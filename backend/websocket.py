"""
WebSocket handlers for real-time AI chat communication.
"""

import os
import json
import time
import asyncio
from datetime import datetime
from flask import request, current_app
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from extensions import db
from models import AIMessage, AIConversation, User, ChatAttachment, KnowledgeBaseEntry
from auth import verify_token

# Agent framework imports
from agent_framework import create_agent
from agent_framework.database.handler import get_agent_session as get_db_session, get_agent_steps
from agent_framework.tools.registry import default_registry

# SocketIO instance will be initialized in app.py
socketio = None

# Global dictionary to store authenticated users by socket session ID
socket_users = {}

# Active agent sessions: {session_id: {task, agent, db_session, user_id}}
active_agent_sessions = {}


def init_socketio(app):
    """Initialize SocketIO with the Flask app."""
    global socketio
    cors_origins = app.config.get('SOCKET_CORS_ALLOWED_ORIGINS', '*')

    socketio = SocketIO(
        app,
        cors_allowed_origins=cors_origins,
        async_mode='eventlet',
        logger=True,
        engineio_logger=True,
        ping_timeout=120,  # Increase ping timeout to 120 seconds (default is 60)
        ping_interval=25,  # Keep ping interval reasonable
        max_http_buffer_size=1e8  # Allow larger messages
    )

    # Register event handlers
    socketio.on_event('connect', handle_connect)
    socketio.on_event('disconnect', handle_disconnect)
    socketio.on_event('authenticate', handle_authenticate)
    socketio.on_event('join_conversation', handle_join_conversation)
    socketio.on_event('leave_conversation', handle_leave_conversation)
    socketio.on_event('send_message', handle_send_message)
    socketio.on_event('typing_start', handle_typing_start)
    socketio.on_event('typing_stop', handle_typing_stop)

    # Agent-specific events
    socketio.on_event('start_agent', handle_start_agent)
    socketio.on_event('approve_action', handle_approve_action)
    socketio.on_event('cancel_agent', handle_cancel_agent)

    return socketio

def handle_connect():
    """Handle new WebSocket connection."""
    socket_users[request.sid] = None
    current_app.logger.info(f"WebSocket connected: {request.sid}")
    emit('connected', {'status': 'connected', 'sid': request.sid})

def handle_disconnect():
    """Handle WebSocket disconnection."""
    user = socket_users.get(request.sid)
    if user:
        current_app.logger.info(f"WebSocket disconnected: user {user.id}, sid {request.sid}")
    else:
        current_app.logger.info(f"WebSocket disconnected: sid {request.sid}")
    socket_users.pop(request.sid, None)

def handle_authenticate(data):
    """Authenticate the WebSocket connection."""
    token = data.get('token')
    current_app.logger.info(f"[DEBUG auth] Received auth token: {token[:20] if token else None}..., sid: {request.sid}")
    if not token:
        current_app.logger.warning(f"[DEBUG auth] No token provided, rejecting")
        emit('error', {'message': 'Authentication required'})
        disconnect()
        return

    user = verify_token(token)
    current_app.logger.info(f"[DEBUG auth] Token verification result: {'SUCCESS' if user else 'FAILED'}, user: {user.email if user else None}")
    if not user:
        emit('error', {'message': 'Invalid token'})
        disconnect()
        return

    socket_users[request.sid] = user
    current_app.logger.info(f"WebSocket authenticated: user {user.email}, sid {request.sid}")
    emit('authenticated', {'status': 'authenticated', 'user': user.to_dict()})

def handle_join_conversation(data):
    """Join a conversation room."""
    user = socket_users.get(request.sid)
    current_app.logger.info(f"[DEBUG join] Auth check for sid {request.sid}: {'authenticated' if user else 'NOT AUTHENTICATED'}")
    if not user:
        current_app.logger.warning(f"[DEBUG join] Rejecting: not authenticated")
        emit('error', {'message': 'Not authenticated'})
        return

    conversation_id = data.get('conversation_id')
    if not conversation_id:
        emit('error', {'message': 'Conversation ID required'})
        return

    # Verify conversation belongs to user
    conversation = AIConversation.query.filter_by(
        id=conversation_id,
        user_id=user.id
    ).first()

    if not conversation:
        emit('error', {'message': 'Conversation not found'})
        return

    room = f"conv_{conversation_id}"
    join_room(room)
    current_app.logger.info(f"User {user.email} joined conversation {conversation_id}")

    # Send recent messages
    messages = AIMessage.query.filter_by(
        conversation_id=conversation_id
    ).order_by(AIMessage.timestamp.asc()).limit(50).all()

    message_data = []
    for msg in messages:
        # Build attachments list if any
        attachments = []
        if hasattr(msg, 'attachments') and msg.attachments:
            for att in msg.attachments:
                attachments.append({
                    'id': att.id,
                    'file_url': att.file_url,
                    'file_type': att.file_type,
                    'original_name': att.original_name
                })
        message_data.append({
            'id': msg.id,
            'conversation_id': msg.conversation_id,
            'role': msg.role,
            'content': msg.content,
            'created_at': msg.timestamp.isoformat() if msg.timestamp else None,
            'action_taken': msg.action_taken,
            'command_executed': msg.command_executed,
            'command_output': msg.command_output,
            'attachments': attachments if attachments else None
        })

    emit('conversation_joined', {
        'conversation_id': conversation_id,
        'messages': message_data,
        'title': conversation.title
    })

def handle_leave_conversation(data):
    """Leave a conversation room."""
    conversation_id = data.get('conversation_id')
    if conversation_id:
        room = f"conv_{conversation_id}"
        leave_room(room)
        current_app.logger.info(f"User left conversation {conversation_id}")

def handle_send_message(data):
    """Handle incoming chat message."""
    user = socket_users.get(request.sid)
    if not user:
        emit('error', {'message': 'Not authenticated'})
        return

    conversation_id = data.get('conversation_id')
    message_content = data.get('message', '').strip()

    if not message_content:
        emit('error', {'message': 'Message cannot be empty'})
        return

    # Get or create conversation
    if conversation_id:
        conversation = AIConversation.query.filter_by(
            id=conversation_id,
            user_id=user.id
        ).first()
        if not conversation:
            emit('error', {'message': 'Conversation not found'})
            return
    else:
        # Create new conversation with first message as title
        title = message_content[:100] + ('...' if len(message_content) > 100 else '')
        conversation = AIConversation(
            user_id=user.id,
            title=title
        )
        db.session.add(conversation)
        db.session.commit()
        conversation_id = conversation.id

    # Save user message
    user_msg = AIMessage(
        conversation_id=conversation_id,
        role='user',
        content=message_content
    )
    db.session.add(user_msg)
    db.session.commit()

    # Handle image attachments if any
    images = data.get('images', [])
    attachments_data = []
    if images:
        for img in images:
            try:
                attachment = ChatAttachment(
                    message_id=user_msg.id,
                    file_path=img.get('file_path'),
                    file_url=img.get('file_url'),
                    file_type=img.get('file_type', 'file'),
                    original_name=img.get('original_name', img.get('name', 'upload')),
                    file_size=img.get('size')
                )
                db.session.add(attachment)
                attachments_data.append({
                    'id': attachment.id,
                    'file_url': attachment.file_url,
                    'file_type': attachment.file_type,
                    'original_name': attachment.original_name
                })
            except Exception as e:
                current_app.logger.error(f"Failed to save attachment: {e}")
        db.session.commit()

    # Broadcast user message to room (including attachments)
    room = f"conv_{conversation_id}"
    emit('new_message', {
        'id': user_msg.id,
        'conversation_id': conversation_id,
        'role': 'user',
        'content': message_content,
        'created_at': user_msg.timestamp.isoformat() if user_msg.timestamp else None,
        'attachments': attachments_data if attachments_data else None
    }, to=room, include_self=True)

    # Start background task using greenlet (non-blocking with eventlet)
    current_app.logger.info(f"[BG] Starting background greenlet for conv={conversation_id}, sid={request.sid}")
    socketio.start_background_task(
        _generate_ai_response_background,
        conversation_id, room, message_content, user.id, current_app._get_current_object(), request.sid
    )
    current_app.logger.info(f"[BG] Background greenlet started for conv={conversation_id}")

    # Don't emit anything else here - background thread handles everything

def handle_typing_start(data):
    """Broadcast that user started typing."""
    user = socket_users.get(request.sid)
    conversation_id = data.get('conversation_id')
    if conversation_id and user:
        room = f"conv_{conversation_id}"
        emit('user_typing', {
            'user_id': user.id
        }, to=room, include_self=False)

def handle_typing_stop(data):
    """Broadcast that user stopped typing."""
    user = socket_users.get(request.sid)
    conversation_id = data.get('conversation_id')
    if conversation_id and user:
        room = f"conv_{conversation_id}"
        emit('user_stopped_typing', {
            'user_id': user.id
        }, to=room, include_self=False)


# ========================================
# AGENT WEBSOCKET HANDLERS
# ========================================

def handle_start_agent(data):
    """
    Start an autonomous agent session.

    Expected data:
    {
        "session_id": int (optional, creates new if not provided),
        "goal": "string - task for agent",
        "template_id": int (optional)
    }
    """
    user = socket_users.get(request.sid)
    if not user:
        emit('error', {'message': 'Not authenticated'})
        return

    goal = data.get('goal')
    if not goal or not goal.strip():
        emit('error', {'message': 'Goal is required'})
        return

    session_id = data.get('session_id')
    template_id = data.get('template_id')

    current_app.logger.info(f"User {user.id} starting agent with goal: {goal[:100]}")

    # Create or get session
    db_session = db.session
    try:
        if session_id:
            # Use existing session
            agent_db_session = get_db_session(db_session, session_id=session_id, user_id=user.id)
            if not agent_db_session:
                emit('error', {'message': 'Invalid session ID'})
                return
        else:
            # Create new session
            from agent_framework.database.handler import create_agent_session
            agent_db_session = create_agent_session(
                db_session=db_session,
                user_id=user.id,
                title=goal[:255],
                template_id=template_id
            )
            db_session.commit()
            session_id = agent_db_session.id

        # Send initial connection confirmation
        emit('agent_started', {
            'session_id': session_id,
            'status': 'running',
            'goal': goal
        })

        # Capture the client SID for this WebSocket connection
        client_sid = request.sid

        # Define stream callback that emits to the WebSocket
        async def stream_callback(session_id, event, data):
            """Emit streaming events to frontend"""
            try:
                socketio.emit(f'agent_{event}', data, to=client_sid)
            except Exception as e:
                current_app.logger.error(f"Failed to emit event {event}: {e}")

        # Create agent
        agent = create_agent(
            session_id=str(session_id),
            user_id=user.id,
            db_session=db_session,
            tool_registry=default_registry,
            max_steps=30,
            stream_callback=stream_callback
        )

        # Store active session
        active_agent_sessions[session_id] = {
            'task': None,
            'agent': agent,
            'db_session': db_session,
            'user_id': user.id,
            'sid': request.sid
        }

        # Run agent as a background greenlet (non-blocking with eventlet)
        def run_agent(app):
            with app.app_context():
                try:
                    # Since agent.run_loop is async, we need to run it in a new event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(agent.run_loop(goal))
                    loop.close()

                    # Cleanup
                    if session_id in active_agent_sessions:
                        del active_agent_sessions[session_id]
                    current_app.logger.info(f"Agent session {session_id} completed")
                except Exception as e:
                    current_app.logger.error(f"Agent task failed: {e}", exc_info=True)
                    socketio.emit('agent_failed', {
                        'session_id': session_id,
                        'error': str(e)
                    }, to=client_sid)
                    if session_id in active_agent_sessions:
                        del active_agent_sessions[session_id]

        socketio.start_background_task(run_agent, current_app._get_current_object())

    except Exception as e:
        current_app.logger.error(f"Failed to start agent: {e}", exc_info=True)
        emit('agent_error', {'message': str(e)})
        db_session.rollback()


def handle_approve_action(data):
    """
    Handle approval for a pending agent action.

    Expected data:
    {
        "session_id": int,
        "step_id": int,
        "approved": boolean
    }
    """
    user = socket_users.get(request.sid)
    if not user:
        emit('error', {'message': 'Not authenticated'})
        return

    session_id = data.get('session_id')
    step_id = data.get('step_id')
    approved = data.get('approved')

    if session_id is None or step_id is None or approved is None:
        emit('error', {'message': 'session_id, step_id, and approved are required'})
        return

    current_app.logger.info(f"User {user.id} {'approved' if approved else 'denied'} action for session {session_id}, step {step_id}")

    try:
        db_session = db.session

        # Update approval in database
        from agent_framework.database.handler import respond_to_approval
        approval = respond_to_approval(
            db_session=db_session,
            approval_id=step_id,  # Using step_id as approval_id for now (needs refinement)
            approved=approved,
            responded_by=user.id
        )

        if approval:
            db_session.commit()
            emit('approval_response', {
                'session_id': session_id,
                'step_id': step_id,
                'approved': approved,
                'responded_by': user.id
            })

            # If agent is waiting for this approval, the polling in _wait_for_approval will detect it
        else:
            emit('error', {'message': 'Approval not found or already processed'})

    except Exception as e:
        current_app.logger.error(f"Failed to process approval: {e}")
        db.session.rollback()
        emit('error', {'message': 'Failed to process approval'})


def handle_cancel_agent(data):
    """
    Cancel a running agent session.

    Expected data:
    {
        "session_id": int
    }
    """
    user = socket_users.get(request.sid)
    if not user:
        emit('error', {'message': 'Not authenticated'})
        return

    session_id = data.get('session_id')
    if session_id is None:
        emit('error', {'message': 'session_id is required'})
        return

    # Check if session exists and belongs to user
    db_session = db.session
    session = get_db_session(db_session, session_id=session_id, user_id=user.id)
    if not session:
        emit('error', {'message': 'Session not found'})
        return

    # Mark as cancelled
    from agent_framework.database.handler import fail_agent_session
    fail_agent_session(
        db_session=db_session,
        session_id=session_id,
        error='Cancelled by user'
    )
    db_session.commit()

    # Remove from active sessions if running
    if session_id in active_agent_sessions:
        del active_agent_sessions[session_id]

    emit('agent_cancelled', {
        'session_id': session_id,
        'status': 'cancelled'
    })

    current_app.logger.info(f"Agent session {session_id} cancelled by user {user.id}")


def _generate_ai_response_background(conversation_id, room, message_content, user_id, app, client_sid):
    """
    Background task to generate AI response without blocking WebSocket.
    This runs in a separate thread and emits responses as they become available.
    """
    from flask import current_app
    from models import AIMessage, KnowledgeBaseEntry, AIConversation

    with app.app_context():
        try:
            current_app.logger.info(f"[BG] START: conv={conversation_id}, room={room}, user={user_id}, client_sid={client_sid}, msg='{message_content[:50]}...'")
            # Log that we've entered the background task
            current_app.logger.info("[BG] Background task is running")
            # Add immediate test emission to verify socket works
            current_app.logger.info(f"[BG] Will emit test event to client_sid={client_sid} and room={room}")
            try:
                # Emit to both the specific client and the room for redundancy
                socketio.emit('ai_response_chunk', {
                    'conversation_id': conversation_id,
                    'content': 'Thinking...',
                    'is_final': False
                }, to=client_sid)
                socketio.emit('ai_response_chunk', {
                    'conversation_id': conversation_id,
                    'content': 'Thinking...',
                    'is_final': False
                }, to=room)
                current_app.logger.info("[BG] Test event emitted successfully")
            except Exception as e:
                current_app.logger.error(f"[BG] Failed to emit test event: {e}", exc_info=True)
                raise

            current_app.logger.info("[BG] Querying conversation context from database...")
            # Get conversation context
            context_messages = AIMessage.query.filter_by(
                conversation_id=conversation_id
            ).order_by(AIMessage.timestamp.desc()).limit(15).all()
            current_app.logger.info(f"[BG] Retrieved {len(context_messages)} context messages")

            context = []
            for msg in reversed(context_messages):
                context.append({
                    'role': msg.role,
                    'content': msg.content
                })

            # Get Knowledge Base entries
            kb_entries = []
            try:
                query_terms = message_content.lower().split()
                current_app.logger.info("[BG] Querying knowledge base...")
                all_kb = KnowledgeBaseEntry.query.all()
                current_app.logger.info(f"[BG] Retrieved {len(all_kb)} KB entries")
                for entry in all_kb:
                    entry_text = (entry.title + ' ' + (entry.content or '')).lower()
                    if any(term in entry_text and len(term) > 3 for term in query_terms):
                        kb_entries.append(entry)
                        if len(kb_entries) >= 3:  # Top 3
                            break
            except Exception as e:
                current_app.logger.warning(f"[BG] KB lookup failed: {e}")

            # Use Anthropic API directly for better responses (bypass Max Model 1)
            try:
                from anthropic import Anthropic
                import os
                api_key = os.getenv('ANTHROPIC_AUTH_TOKEN') or os.getenv('ANTHROPIC_API_KEY')
                base_url = os.getenv('ANTHROPIC_BASE_URL')
                model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')

                if base_url:
                    client = Anthropic(api_key=api_key, base_url=base_url)
                else:
                    client = Anthropic(api_key=api_key)

                # Build messages for Anthropic
                messages = []
                # Add context from conversation history (last 10 messages)
                for msg in context[-10:] if len(context) > 10 else context:
                    messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
                messages.append({'role': 'user', 'content': message_content})

                # Make API call with timeout
                current_app.logger.info(f"Calling Anthropic API, model={model}")
                try:
                    # Set timeout using requests-based timeout if available
                    import socket
                    socket.setdefaulttimeout(30)  # 30 second timeout for the connection
                    response = client.messages.create(
                        model=model,
                        max_tokens=4000,
                        system="You are a helpful AI assistant for a CRM dashboard. Respond naturally and concisely. Current time: " + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                        messages=messages,
                        timeout=30.0  # explicit timeout in seconds
                    )
                except TypeError:
                    # If timeout parameter not supported by this client version
                    response = client.messages.create(
                        model=model,
                        max_tokens=4000,
                        system="You are a helpful AI assistant for a CRM dashboard. Respond naturally and concisely. Current time: " + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                        messages=messages
                    )

                # Extract text from content blocks (handle ThinkingBlock, TextBlock, etc.)
                # Filter for text blocks only - skip thinking blocks and other non-text types
                text_blocks = [block for block in response.content if getattr(block, 'type', None) == 'text']
                if text_blocks:
                    response_text = text_blocks[0].text
                else:
                    # No text blocks found - use fallback
                    raise ValueError("No text content in AI response")
                full_response = response_text
                current_app.logger.info(f"Anthropic API response received (length={len(response_text)})")
                current_app.logger.info(f"[BG] Response text preview: {response_text[:200]}...")

                # Log that we're about to split into chunks
                current_app.logger.info("[BG] Starting chunk splitting")
            except Exception as e:
                current_app.logger.error(f"Anthropic API call failed: {e}", exc_info=True)
                response_text = "I apologize, but I encountered an error connecting to the AI service. Please try again."
                full_response = response_text

            # Stream response in natural chunks (by sentences or clauses) for better UX
            # Split on sentence boundaries, but also ensure chunks aren't too large
            import re
            import time
            import random

            # For now, just send the full response as a single chunk (no streaming delays)
            # to ensure reliability. Streaming can be re-enabled after we confirm basic flow works.
            chunks = [full_response] if full_response else []
            current_app.logger.info(f"[BG] Prepared {len(chunks)} chunk(s) for emission")

            # Emit all chunks
            current_app.logger.info(f"[BG] Will emit {len(chunks)} chunk(s)")
            for i, chunk in enumerate(chunks):
                try:
                    current_app.logger.info(f"[BG] Emitting chunk {i+1}/{len(chunks)} (len={len(chunk)})")
                    socketio.emit('ai_response_chunk', {
                        'conversation_id': conversation_id,
                        'content': chunk,
                        'is_final': i == len(chunks) - 1
                    }, to=room)  # Use room for reliability
                    current_app.logger.info(f"[BG] Chunk {i+1} emitted")
                except Exception as e:
                    current_app.logger.error(f"[BG] Failed to emit chunk: {e}")
                    break  # Stop streaming if emit fails

            # Save assistant message
            current_app.logger.info("[BG] Saving assistant message to database")
            assistant_msg = AIMessage(
                conversation_id=conversation_id,
                role='assistant',
                content=full_response
            )
            db.session.add(assistant_msg)
            conversation = AIConversation.query.get(conversation_id)
            if conversation:
                conversation.updated_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.info(f"[BG] Assistant message saved with id={assistant_msg.id}")

            # Broadcast final message to the room
            current_app.logger.info("[BG] Emitting final new_message event to room")
            socketio.emit('new_message', {
                'id': assistant_msg.id,
                'conversation_id': conversation_id,
                'role': 'assistant',
                'content': full_response,
                'created_at': assistant_msg.timestamp.isoformat() if assistant_msg.timestamp else None
            }, to=room)
            current_app.logger.info("[BG] new_message emitted")

            socketio.emit('ai_response_complete', {
                'conversation_id': conversation_id,
                'message_id': assistant_msg.id
            }, to=room)
            current_app.logger.info("[BG] ai_response_complete emitted")

            # Notify other tabs/windows about new message (via user room)
            socketio.emit('conversation_updated', {
                'conversation_id': conversation_id,
                'last_message': full_response[:100] + ('...' if len(full_response) > 100 else ''),
                'updated_at': datetime.utcnow().isoformat()
            }, room=f"user_{user_id}")
            current_app.logger.info("[BG] conversation_updated emitted")

            current_app.logger.info(f"[BG] AI response completed for conversation {conversation_id}")

        except Exception as e:
            current_app.logger.error(f"[BG] AI response error: {str(e)}", exc_info=True)
            error_msg = f"I apologize, but I encountered an error: {str(e)}"

            # Save error message
            try:
                with app.app_context():
                    current_app.logger.info("[BG] Saving error message to database")
                    assistant_msg = AIMessage(
                        conversation_id=conversation_id,
                        role='assistant',
                        content=error_msg
                    )
                    db.session.add(assistant_msg)
                    db.session.commit()
                    current_app.logger.info(f"[BG] Error message saved with id={assistant_msg.id}")

                    current_app.logger.info("[BG] Emitting error new_message")
                    socketio.emit('new_message', {
                        'id': assistant_msg.id,
                        'conversation_id': conversation_id,
                        'role': 'assistant',
                        'content': error_msg,
                        'created_at': assistant_msg.timestamp.isoformat() if assistant_msg.timestamp else None,
                        'error': True
                    }, to=room)
                    current_app.logger.info("[BG] Error new_message emitted")

                    current_app.logger.info("[BG] Emitting error ai_response_complete")
                    socketio.emit('ai_response_complete', {
                        'conversation_id': conversation_id,
                        'message_id': assistant_msg.id,
                        'error': True
                    }, to=room)
                    current_app.logger.info("[BG] Error ai_response_complete emitted")

                    # Notify conversation update (with error message) to user room for other tabs
                    current_app.logger.info("[BG] Emitting error conversation_updated")
                    socketio.emit('conversation_updated', {
                        'conversation_id': conversation_id,
                        'last_message': error_msg[:100] + ('...' if len(error_msg) > 100 else ''),
                        'updated_at': datetime.utcnow().isoformat()
                    }, room=f"user_{user_id}")
                    current_app.logger.info("[BG] Error conversation_updated emitted")
            except Exception as e2:
                current_app.logger.error(f"[BG] Failed to save error message: {e2}")
        finally:
            # Ensure database session is cleaned up
            try:
                db.session.remove()
            except Exception as e:
                current_app.logger.warning(f"[BG] Failed to remove session: {e}")
