"""
Agent management API endpoints.
Allows triggering agents, checking status, and viewing agent logs.
"""
from flask import Blueprint, request, jsonify
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from models import db, ActivityLog

agents_bp = Blueprint('agents', __name__)

# In-memory store for agent run status (could be Redis in production)
agent_status = {
    'qa': {'last_run': None, 'is_running': False, 'last_result': None},
    'backend': {'last_run': None, 'is_running': False, 'last_result': None},
    'frontend': {'last_run': None, 'is_running': False, 'last_result': None}
}

def trigger_agent_sync(agent_type: str) -> bool:
    """Trigger an agent synchronously (blocking). Returns True if successful."""
    try:
        # Update status
        agent_status[agent_type]['is_running'] = True
        agent_status[agent_type]['last_run'] = datetime.now().isoformat()

        # Run the agent
        result = subprocess.run(
            ['python', '-m', 'agents.run_agent', '--type', agent_type],
            cwd=Path(__file__).parent.parent.absolute(),
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes
        )

        # Capture logs
        output = result.stdout
        errors = result.stderr

        # Log to ActivityLog
        action = f"{agent_type.capitalize()} Agent Run"
        details = f"Exit code: {result.returncode}\nOutput: {output[:2000]}\nErrors: {errors[:1000]}"
        log = ActivityLog(
            action=action,
            details=details
        )
        db.session.add(log)
        db.session.commit()

        # Update status
        success = result.returncode == 0
        agent_status[agent_type]['is_running'] = False
        agent_status[agent_type]['last_result'] = {
            'success': success,
            'exit_code': result.returncode,
            'timestamp': datetime.now().isoformat()
        }

        return success

    except subprocess.TimeoutExpired:
        agent_status[agent_type]['is_running'] = False
        agent_status[agent_type]['last_result'] = {
            'success': False,
            'error': 'timeout',
            'timestamp': datetime.now().isoformat()
        }
        return False
    except Exception as e:
        agent_status[agent_type]['is_running'] = False
        agent_status[agent_type]['last_result'] = {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        return False

def trigger_agent_async(agent_type: str):
    """Trigger an agent in a background thread."""
    def run():
        try:
            trigger_agent_sync(agent_type)
        except Exception as e:
            print(f"Agent {agent_type} failed: {e}")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

@agents_bp.route('/agents/trigger/<agent_type>', methods=['POST'])
def trigger_agent(agent_type):
    """Trigger an agent to run immediately."""
    if agent_type not in ['qa', 'backend', 'frontend']:
        return jsonify({'error': 'Invalid agent type'}), 400

    # Check if already running
    if agent_status[agent_type]['is_running']:
        return jsonify({
            'message': f'Agent {agent_type} is already running',
            'status': 'running'
        }), 409

    # Trigger in background
    trigger_agent_async(agent_type)

    return jsonify({
        'message': f'Agent {agent_type} started',
        'status': 'started'
    }), 202

@agents_bp.route('/agents/status', methods=['GET'])
def get_agent_status():
    """Get status of all agents, combining in-memory state with database logs."""
    # Start with a copy of in-memory status
    status = {}
    for agent_type in ['qa', 'backend', 'frontend']:
        status[agent_type] = agent_status.get(agent_type, {
            'is_running': False,
            'last_run': None,
            'last_result': None
        }).copy()

    # Enhance with database logs for latest run
    for agent_type in ['qa', 'backend', 'frontend']:
        action_prefix = f"{agent_type.capitalize()} Agent"
        # Look for the most recent Agent log (Started, Completed, Failed)
        log = ActivityLog.query.filter(
            ActivityLog.action.like(f"{action_prefix}%")
        ).order_by(ActivityLog.timestamp.desc()).first()

        if log:
            # Parse success from action or details
            success = 'completed' in log.action.lower() and 'failed' not in log.action.lower()
            exit_code = None
            if log.details:
                import re
                m = re.search(r'Exit code: (\d+)', log.details)
                if m:
                    exit_code = int(m.group(1))
                    success = exit_code == 0
                else:
                    # If no explicit exit code, infer from action
                    success = 'failed' not in log.action.lower()

            status[agent_type]['last_run'] = log.timestamp.isoformat() if log.timestamp else None
            status[agent_type]['last_result'] = {
                'success': success,
                'exit_code': exit_code,
                'action': log.action,
                'timestamp': log.timestamp.isoformat() if log.timestamp else None
            }

    return jsonify(status), 200

@agents_bp.route('/agents/logs', methods=['GET'])
def get_agent_logs():
    """Get recent agent activity logs."""
    limit = request.args.get('limit', 50, type=int)
    agent_type = request.args.get('agent')  # Optional filter

    query = ActivityLog.query

    if agent_type:
        query = query.filter(ActivityLog.action.like(f'%{agent_type.capitalize()} Agent%'))

    logs = query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()

    result = []
    for log in logs:
        result.append({
            'id': log.id,
            'action': log.action,
            'details': log.details,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None
        })

    return jsonify(result), 200

@agents_bp.route('/agents/latest/<agent_type>', methods=['GET'])
def get_latest_run(agent_type):
    """Get the most recent run result for an agent."""
    if agent_type not in ['qa', 'backend', 'frontend']:
        return jsonify({'error': 'Invalid agent type'}), 400

    # Fetch latest log from DB
    action_prefix = f"{agent_type.capitalize()} Agent"
    log = ActivityLog.query.filter(
        ActivityLog.action.like(f"{action_prefix}%")
    ).order_by(ActivityLog.timestamp.desc()).first()

    if not log:
        return jsonify({'message': 'No runs found'}), 404

    # Parse success
    success = 'completed' in log.action.lower() and 'failed' not in log.action.lower()
    exit_code = None
    if log.details:
        import re
        m = re.search(r'Exit code: (\d+)', log.details)
        if m:
            exit_code = int(m.group(1))
            success = exit_code == 0

    result = {
        'action': log.action,
        'details': log.details,
        'timestamp': log.timestamp.isoformat() if log.timestamp else None,
        'success': success,
        'exit_code': exit_code
    }

    return jsonify(result), 200
