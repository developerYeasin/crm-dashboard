#!/usr/bin/env python3
"""
Test script for the autonomous agent framework.

This script demonstrates:
1. Creating an agent session
2. Running a simple multi-step task
3. Viewing results

Usage:
    python test_agent.py --goal "List files in /root/max-ai-agent and count them"
"""

import argparse
import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from flask import Flask
from config import Config
from extensions import db
from agent_framework import create_agent, get_agent_session, list_agent_sessions


def setup_app():
    """Create Flask app and initialize database"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    # Import agent models to register them with the shared db
    # No need to call init_db_handlers; just importing registers models
    from agent_framework.database.models import AgentSession, AgentStep, ToolCall, ApprovalQueue, AgentLongTermMemory, AgentTemplate  # noqa

    return app


async def run_agent_test(app, goal: str, user_id: int = 1):
    """Run agent with the given goal"""
    from agent_framework.tools.registry import default_registry

    with app.app_context():
        # Create a database session
        from agent_framework.database.models import db as agent_db
        agent_db.session.begin()

        try:
            # Create agent
            session_id = f"test-{int(asyncio.get_event_loop().time() * 1000)}"
            agent = create_agent(
                session_id=session_id,
                user_id=user_id,
                db_session=agent_db.session,
                tool_registry=default_registry,
                max_steps=10,
                stream_callback=None  # No streaming in CLI mode
            )

            print(f"\n{'='*60}")
            print(f"Agent Test: {goal}")
            print(f"Session ID: {session_id}")
            print(f"{'='*60}\n")

            # Run the agent
            result = await agent.run_loop(goal)

            print("\n" + "="*60)
            print("AGENT EXECUTION COMPLETE")
            print("="*60)
            print(f"Status: {result.status}")
            print(f"Steps: {len(result.steps)}")
            print(f"\nSummary:")
            print(result.summary)
            print("\nFinal thought:")
            print(result.final_thought.content)
            print("\nFull session saved to database with ID:", result.session_id)

            # Query from database to verify
            db_session = get_agent_session(agent_db.session, result.session_id)
            if db_session:
                print(f"\nDatabase record: {db_session.to_dict()}")

            agent_db.session.commit()
            return result

        except Exception as e:
            agent_db.session.rollback()
            print(f"\nError: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return None


def main():
    parser = argparse.ArgumentParser(description="Test autonomous agent framework")
    parser.add_argument('--goal', type=str, default="List files in the /root/max-ai-agent/backend directory",
                        help='Goal for the agent to accomplish')
    parser.add_argument('--user-id', type=int, default=1,
                        help='User ID (default: 1)')
    parser.add_argument('--max-steps', type=int, default=10,
                        help='Maximum steps (default: 10)')

    args = parser.parse_args()

    # Setup Flask app
    print("Initializing application...")
    app = setup_app()

    # Run agent
    print(f"Starting agent with goal: {args.goal}")
    result = asyncio.run(run_agent_test(app, args.goal, args.user_id))

    if result:
        print("\n✓ Test completed successfully")
        sys.exit(0)
    else:
        print("\n✗ Test failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
