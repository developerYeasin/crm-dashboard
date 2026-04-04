"""
FastAPI Service for Autonomous Agent Streaming

Standalone FastAPI application providing WebSocket and REST endpoints
for real-time agent execution streaming.

Run with: uvicorn agent_framework.api_stream:app --host 0.0.0.0 --port 8092 --reload
"""

import os
import json
import asyncio
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================
# FastAPI App Setup
# ========================================

app = FastAPI(
    title="Autonomous Agent API",
    description="Real-time streaming API for autonomous agent framework",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8092"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

# ========================================
# Database Setup
# ========================================

# Get database URI from environment or config
DATABASE_URI = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://user:password@localhost/order_tracker'
)

engine = create_engine(DATABASE_URI)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict]:
    """Verify JWT token and return user info"""
    if not credentials:
        return None

    from auth import verify_token as verify_jwt
    user = verify_jwt(credentials.credentials)
    return user

# ========================================
# Connection Manager
# ========================================

class ConnectionManager:
    """Manages WebSocket connections per session"""

    def __init__(self):
        self.active_connections: Dict[int, Dict] = {}  # session_id -> {ws, user_id, agent_task}

    async def connect(self, session_id: int, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[session_id] = {
            'ws': websocket,
            'user_id': user_id,
            'agent_task': None
        }
        logger.info(f"WebSocket connected for session {session_id} by user {user_id}")

        # Send connected event
        await websocket.send_json({
            'event': 'connected',
            'session_id': session_id,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })

    def disconnect(self, session_id: int):
        if session_id in self.active_connections:
            conn = self.active_connections.pop(session_id)
            logger.info(f"WebSocket disconnected for session {session_id}")

    async def send(self, session_id: int, event: str, data: Dict[str, Any]):
        """Send event to specific session"""
        conn = self.active_connections.get(session_id)
        if conn:
            try:
                await conn['ws'].send_json({
                    'event': event,
                    'session_id': session_id,
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Failed to send event {event} to session {session_id}: {e}")

    def get_connection(self, session_id: int) -> Optional[Dict]:
        return self.active_connections.get(session_id)

manager = ConnectionManager()

# ========================================
# WebSocket Events
# ========================================

@app.websocket("/ws/agent/{session_id}")
async def agent_websocket(
    session_id: int,
    websocket: WebSocket,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time agent streaming.

    Client must send:
    1. "start_agent" with goal to begin
    2. "approve_action" to approve pending actions
    3. "cancel_agent" to stop the agent

    Server streams:
    - "agent_thinking": Agent's current thought
    - "agent_action": Action being executed
    - "agent_observation": Result of action
    - "awaiting_approval": Waiting for user approval
    - "agent_completed": Session completed successfully
    - "agent_failed": Session failed
    """
    # Authenticate token if provided
    user = None
    if token:
        from auth import verify_token
        user = verify_token(token)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return
    else:
        # Allow anonymous for testing (not recommended for production)
        logger.warning(f"WebSocket connection without token for session {session_id}")

    # Connect
    user_id = user.id if user else 0
    await manager.connect(session_id, websocket, user_id)

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'start_agent':
                await handle_start_agent(session_id, data, user_id)

            elif msg_type == 'approve_action':
                await handle_approve_action(session_id, data, user_id)

            elif msg_type == 'cancel_agent':
                await handle_cancel_agent(session_id, data, user_id)

            else:
                await websocket.send_json({
                    'event': 'error',
                    'data': {'message': f'Unknown message type: {msg_type}'}
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected: session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(session_id)


async def handle_start_agent(session_id: int, data: Dict, user_id: int):
    """Start an agent session"""
    goal = data.get('goal')
    if not goal:
        await manager.send(session_id, 'agent_error', {'message': 'Goal is required'})
        return

    db = SessionLocal()
    try:
        # Import agent framework
        from agent_framework import create_agent
        from agent_framework.tools.registry import default_registry
        from agent_framework.database.handler import get_agent_session as get_db_session

        # Get or create session
        template_id = data.get('template_id')
        session = get_db_session(db, session_id=session_id, user_id=user_id)
        if not session:
            # Should exist already from REST creation, but create if needed
            from agent_framework.database.handler import create_agent_session
            session = create_agent_session(
                db_session=db,
                user_id=user_id,
                title=goal[:255],
                template_id=template_id
            )
            db.commit()

        # Stream callback
        async def stream_callback(session_id, event, event_data):
            await manager.send(session_id, event, event_data)

        # Create agent
        agent = create_agent(
            session_id=str(session_id),
            user_id=user_id,
            db_session=db,
            tool_registry=default_registry,
            max_steps=30,
            stream_callback=stream_callback
        )

        # Store in connection manager
        conn = manager.get_connection(session_id)
        if conn:
            conn['agent'] = agent
            conn['db'] = db

        # Run in background
        def run_agent():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(agent.run_loop(goal))
                logger.info(f"Agent completed for session {session_id}: {result.status}")
            except Exception as e:
                logger.error(f"Agent failed for session {session_id}: {e}", exc_info=True)
                asyncio.run_coroutine_threadsafe(
                    manager.send(session_id, 'agent_failed', {'error': str(e)}),
                    loop
                )
            finally:
                loop.close()
                # Cleanup
                manager.disconnect(session_id)

        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

    except Exception as e:
        logger.error(f"Failed to start agent: {e}")
        await manager.send(session_id, 'agent_error', {'message': str(e)})


async def handle_approve_action(session_id: int, data: Dict, user_id: int):
    """Handle approval for pending action"""
    step_id = data.get('step_id')
    approved = data.get('approved')

    if step_id is None or approved is None:
        await manager.send(session_id, 'error', {'message': 'step_id and approved are required'})
        return

    db = SessionLocal()
    try:
        from agent_framework.database.handler import respond_to_approval
        approval = respond_to_approval(
            db_session=db,
            approval_id=step_id,
            approved=approved,
            responded_by=user_id,
            comment=data.get('comment')
        )
        db.commit()

        if approval:
            await manager.send(session_id, 'approval_response', {
                'step_id': step_id,
                'approved': approved,
                'responded_by': user_id
            })
        else:
            await manager.send(session_id, 'error', {'message': 'Approval not found'})
    except Exception as e:
        logger.error(f"Approval error: {e}")
        await manager.send(session_id, 'error', {'message': str(e)})
    finally:
        db.close()


async def handle_cancel_agent(session_id: int, data: Dict, user_id: int):
    """Cancel running agent"""
    db = SessionLocal()
    try:
        from agent_framework.database.handler import fail_agent_session
        fail_agent_session(
            db_session=db,
            session_id=session_id,
            error='Cancelled by user'
        )
        db.commit()

        await manager.send(session_id, 'agent_cancelled', {'status': 'cancelled'})

        # Cancel agent task if running
        conn = manager.get_connection(session_id)
        if conn and 'agent' in conn:
            # Agent will detect session status change on next poll
            pass

    except Exception as e:
        logger.error(f"Cancel error: {e}")
        await manager.send(session_id, 'error', {'message': str(e)})
    finally:
        db.close()


# ========================================
# REST Endpoints (duplicate of Flask routes but in FastAPI)
# ========================================

@app.post("/api/agent/sessions")
async def api_create_session(
    goal: str,
    template_id: Optional[int] = None,
    user: Dict = Depends(verify_token)
):
    """Create a new agent session"""
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")

    db = SessionLocal()
    try:
        from agent_framework.database.handler import create_agent_session
        session = create_agent_session(
            db_session=db,
            user_id=user['id'],
            title=goal[:255],
            template_id=template_id
        )
        db.commit()

        return {
            'session_id': session.id,
            'status': 'running',
            'title': session.title,
            'websocket_url': f"/ws/agent/{session.id}",
            'created_at': session.created_at.isoformat() if session.created_at else None
        }
    except Exception as e:
        logger.error(f"Create session error: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
    finally:
        db.close()


@app.get("/api/agent/sessions")
async def api_list_sessions(
    status: Optional[str] = None,
    limit: int = 50,
    user: Dict = Depends(verify_token)
):
    """List agent sessions"""
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")

    db = SessionLocal()
    try:
        from agent_framework.database.handler import list_agent_sessions
        sessions = list_agent_sessions(
            db_session=db,
            user_id=user['id'],
            status=status,
            limit=min(limit, 100)
        )
        return {'sessions': [s.to_dict() for s in sessions]}
    finally:
        db.close()


@app.get("/api/agent/sessions/{session_id}")
async def api_get_session(
    session_id: int,
    user: Dict = Depends(verify_token)
):
    """Get session with steps"""
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")

    db = SessionLocal()
    try:
        from agent_framework.database.handler import get_agent_session, get_agent_steps, get_pending_approvals
        session = get_agent_session(db, session_id=session_id, user_id=user['id'])
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

        steps = get_agent_steps(db, session_id=session_id)
        pending = get_pending_approvals(db, session_id=session_id)

        return {
            'session': session.to_dict(),
            'steps': [s.to_dict() for s in steps],
            'pending_approvals': [p.to_dict() for p in pending]
        }
    finally:
        db.close()


@app.post("/api/agent/sessions/{session_id}/approve")
async def api_approve_action(
    session_id: int,
    approved: bool,
    comment: Optional[str] = None,
    user: Dict = Depends(verify_token)
):
    """Approve or deny a pending action"""
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")

    db = SessionLocal()
    try:
        from agent_framework.database.handler import get_pending_approvals, respond_to_approval

        pending = get_pending_approvals(db, session_id=session_id, limit=1)
        if not pending:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No pending approval")

        approval = respond_to_approval(
            db_session=db,
            approval_id=pending[0].id,
            approved=approved,
            responded_by=user['id'],
            comment=comment
        )
        db.commit()

        return {'status': 'ok', 'approval_id': approval.id}
    finally:
        db.close()


@app.post("/api/agent/sessions/{session_id}/cancel")
async def api_cancel_session(
    session_id: int,
    user: Dict = Depends(verify_token)
):
    """Cancel a running session"""
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")

    db = SessionLocal()
    try:
        from agent_framework.database.handler import fail_agent_session, get_agent_session
        session = get_agent_session(db, session_id=session_id, user_id=user['id'])
        if not session:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

        fail_agent_session(db, session_id=session_id, error='Cancelled by user')
        db.commit()

        return {'status': 'cancelled'}
    finally:
        db.close()


# ========================================
# Health Check
# ========================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agent-api", "timestamp": datetime.utcnow().isoformat()}


# ========================================
# Main Entry Point
# ========================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('AGENT_API_PORT', 8092))
    uvicorn.run(app, host="0.0.0.0", port=port)
