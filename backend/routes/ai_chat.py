import os
import json
import subprocess
import psutil
import re
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, g
from extensions import db
from models import AIConversation, AIMessage, AIAction, SystemCronJob, SystemCommandLog, SystemMetric, User
from dotenv import load_dotenv
from anthropic import Anthropic
from auth import login_required, get_current_user
from cache import (
    Cache, generate_conversation_context_key, generate_ai_response_key,
    generate_ai_stateless_key, generate_system_metrics_key, generate_file_content_key,
    MemoryCache
)
from sqlalchemy.exc import OperationalError

load_dotenv()

ai_bp = Blueprint('ai', __name__)

# Deadlock retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # seconds

def retry_on_deadlock(func):
    """Decorator to retry database operations on deadlock/lock timeout"""
    from functools import wraps
    from sqlalchemy.exc import OperationalError

    @wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                # MySQL deadlock (1213) or lock wait timeout (1205)
                if hasattr(e.orig, 'args') and len(e.orig.args) > 0:
                    errcode = e.orig.args[0]
                    if errcode in (1205, 1213):  # Lock wait timeout or deadlock
                        if attempt < MAX_RETRIES - 1:
                            current_app.logger.warning(f"Database lock detected, retrying ({attempt + 1}/{MAX_RETRIES})...")
                            time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                            continue
                        else:
                            current_app.logger.error(f"Database lock timeout after {MAX_RETRIES} retries")
                raise
        return None
    return wrapper

# In-memory LRU cache for conversation context (fast, per-process)
# Will be initialized after app context with proper maxsize from config
_context_cache = None

def _get_context_cache():
    """Get context cache, initializing if needed"""
    global _context_cache
    if _context_cache is None:
        # Get maxsize from app config if available, else default 256
        try:
            from flask import current_app
            maxsize = current_app.config.get('CACHE_CONTEXT_MAXSIZE', 256) if current_app else 256
        except Exception:
            maxsize = 256
        _context_cache = MemoryCache(maxsize=maxsize)
    return _context_cache

# Configure AI client - support both Anthropic direct and OpenRouter
BASE_URL = os.getenv('ANTHROPIC_BASE_URL')
API_KEY = os.getenv('ANTHROPIC_AUTH_TOKEN') or os.getenv('ANTHROPIC_API_KEY')
MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')

if BASE_URL:
    # Using OpenRouter or custom endpoint
    anthropic_client = Anthropic(
        api_key=API_KEY,
        base_url=BASE_URL,
        default_headers={
            'HTTP-Referer': 'https://crm-dashboard.local',
            'X-Title': 'CRM Dashboard'
        } if 'openrouter' in BASE_URL else {}
    )
else:
    # Using direct Anthropic API
    anthropic_client = Anthropic(api_key=API_KEY)

# System prompt - keep it simple
SYSTEM_PROMPT = """You are a helpful AI assistant for a CRM dashboard.

Respond naturally and concisely. When you need to perform actions, use the provided tools.

RULES:
- Be helpful and professional
- Use tools when you need to get information or perform actions
- Don't mention tool usage to the user
- Present results clearly
- Keep responses conversational
"""

# Dangerous commands blocklist
DANGEROUS_COMMANDS = [
    'rm -rf /', 'rm -rf /*', 'dd if=', ':(){ :|:& };:', 'mkfs', 'format',
    'shutdown', 'reboot', 'poweroff', 'halt', 'init 0', 'init 6',
    '> /dev/', 'chmod -R 777 /', 'chown -R', 'mv /*', 'cp /*',
    'sudo', 'su -', 'passwd', 'useradd', 'userdel', 'groupadd', 'groupdel'
]

def is_safe_command(command):
    """Check if command is safe to execute"""
    cmd_lower = command.lower()
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous.lower() in cmd_lower:
            return False, f"Potentially dangerous command blocked: contains '{dangerous}'"
    return True, "OK"

def execute_shell_command(command, timeout=30):
    """Execute a shell command and return output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'success': True,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'exit_code': -1,
            'stdout': '',
            'stderr': f'Command timed out after {timeout} seconds'
        }
    except Exception as e:
        return {
            'success': False,
            'exit_code': -1,
            'stdout': '',
            'stderr': str(e)
        }

def get_conversation_context(conversation_id, limit=15):
    """Get recent messages for context with caching"""
    cache_key = generate_conversation_context_key(conversation_id, limit)
    context_cache = _get_context_cache()

    # Try memory cache first (fast, per-process LRU)
    cached = context_cache.get(cache_key)
    if cached is not None:
        current_app.logger.debug(f"Context cache HIT (memory): conv {conversation_id}")
        return cached

    # Try database cache if available (slower but shared across processes)
    if hasattr(current_app, 'cache') and current_app.cache._enabled:
        cached = current_app.cache.get(cache_key)
        if cached is not None:
            current_app.logger.debug(f"Context cache HIT (db): conv {conversation_id}")
            # Populate memory cache for faster future access
            context_cache.set(cache_key, cached, ttl_seconds=current_app.config.get('CACHE_TTL_CONTEXT', 30))
            return cached

    # Cache miss - query database
    current_app.logger.debug(f"Context cache MISS: conv {conversation_id}")
    messages = AIMessage.query.filter_by(
        conversation_id=conversation_id
    ).order_by(AIMessage.timestamp.desc()).limit(limit).all()

    context = []
    for msg in reversed(messages):
        context.append({
            'role': msg.role,
            'content': msg.content
        })

    # Store in caches
    ttl = current_app.config.get('CACHE_TTL_CONTEXT', 30) if hasattr(current_app, 'cache') else 30
    context_cache.set(cache_key, context, ttl_seconds=ttl)
    if hasattr(current_app, 'cache') and current_app.cache._enabled:
        current_app.cache.set(cache_key, context, ttl_seconds=ttl)

    return context

def execute_tool(tool_name, tool_input, conversation_id, user_email):
    """Execute a tool requested by the AI"""
    try:
        if tool_name == 'execute_command':
            command = tool_input.get('command')
            timeout = tool_input.get('timeout', 30)
            if not command:
                return "Error: No command provided"

            # Safety check
            is_safe, reason = is_safe_command(command)
            if not is_safe:
                return f"Error: Command blocked - {reason}"

            # Execute
            result = execute_shell_command(command, timeout)

            # Log
            action = AIAction(
                conversation_id=conversation_id,
                action_type='tool_shell_command',
                description=f"AI executed: {command}",
                command=command,
                result=f"Exit code: {result.get('exit_code')}",
                status='completed' if result.get('success') else 'failed',
                executed_by=user_email
            )
            db.session.add(action)

            cmd_log = SystemCommandLog(
                command=command,
                executed_by=user_email,
                conversation_id=conversation_id,
                output=result.get('stdout', '') + result.get('stderr', ''),
                exit_code=result.get('exit_code', -1),
                execution_time=0,
                status='success' if result.get('success') else 'failed'
            )
            db.session.add(cmd_log)
            db.session.commit()

            output = result.get('stdout', '') or result.get('stderr', '')
            return f"Exit code: {result.get('exit_code')}\n\n{output[:4000]}"

        elif tool_name == 'query_database':
            query = tool_input.get('query')
            allow_write = tool_input.get('allow_write', False)

            if not query:
                return "Error: No query provided"

            # Block writes unless explicitly allowed
            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE', 'CREATE']
            query_upper = query.upper()

            if not allow_write and any(keyword in query_upper for keyword in dangerous_keywords):
                return "Error: Write operations blocked. Set allow_write=true for writes."

            # Log
            action = AIAction(
                conversation_id=conversation_id,
                action_type='db_query',
                description=f"AI query: {query[:100]}...",
                command=query,
                status='approved',
                executed_by=user_email
            )
            db.session.add(action)
            db.session.commit()

            try:
                result = db.session.execute(db.text(query))
                db.session.commit()

                if query_upper.startswith('SELECT'):
                    rows = result.fetchall()
                    columns = result.keys()
                    data = [dict(zip(columns, row)) for row in rows[:100]]

                    return f"Query returned {len(data)} rows\nColumns: {', '.join(columns)}\n\nFirst row: {data[0] if data else 'No data'}"
                else:
                    return f"Query executed successfully. Rows affected: {result.rowcount}"
            except Exception as e:
                action.status = 'failed'
                action.result = str(e)
                db.session.commit()
                return f"Query error: {str(e)}"

        elif tool_name == 'create_cron_job':
            name = tool_input.get('name')
            command = tool_input.get('command')
            schedule = tool_input.get('schedule')
            description = tool_input.get('description', '')

            if not all([name, command, schedule]):
                return "Error: Missing required fields (name, command, schedule)"

            # Validate cron expression
            cron_parts = schedule.split()
            if len(cron_parts) != 5:
                return "Error: Invalid cron expression. Use format: 'minute hour day month weekday'"

            # Safety check command
            is_safe, reason = is_safe_command(command)
            if not is_safe:
                return f"Error: Command blocked - {reason}"

            # Create job
            job = SystemCronJob(
                name=name,
                command=command,
                schedule=schedule,
                enabled=True,
                created_by=user_email,
                description=description
            )
            db.session.add(job)

            action = AIAction(
                conversation_id=conversation_id,
                action_type='cron_create',
                description=f"AI created cron: {name}",
                command=f"{schedule} {command}",
                status='completed',
                executed_by=user_email
            )
            db.session.add(action)
            db.session.commit()

            return f"✅ Cron job created successfully\nName: {name}\nSchedule: {schedule}\nCommand: {command}"

        elif tool_name == 'get_system_metrics':
            # Check cache first
            cache_hit = False
            metrics = None
            metrics_cache_key = generate_system_metrics_key()

            if hasattr(current_app, 'cache') and current_app.cache._enabled:
                cached_metrics = current_app.cache.get(metrics_cache_key)
                if cached_metrics is not None:
                    metrics = cached_metrics
                    cache_hit = True
                    current_app.logger.debug("System metrics cache HIT")

            if not cache_hit:
                # Collect metrics (expensive operation)
                metrics = {
                    'cpu': {
                        'percent': psutil.cpu_percent(interval=1),
                        'count': psutil.cpu_count(),
                    },
                    'memory': {
                        'percent': psutil.virtual_memory().percent,
                        'used_gb': psutil.virtual_memory().used / (1024**3),
                        'total_gb': psutil.virtual_memory().total / (1024**3),
                    },
                    'disk': {
                        'percent': psutil.disk_usage('/').percent,
                        'used_gb': psutil.disk_usage('/').used / (1024**3),
                        'total_gb': psutil.disk_usage('/').total / (1024**3),
                        'free_gb': psutil.disk_usage('/').free / (1024**3),
                    },
                    'processes': len(psutil.pids())
                }

                # Cache metrics for future use (15 seconds)
                if hasattr(current_app, 'cache') and current_app.cache._enabled:
                    try:
                        current_app.cache.set(metrics_cache_key, metrics, ttl_seconds=current_app.config.get('CACHE_TTL_METRICS', 15))
                        current_app.logger.debug("System metrics cached")
                    except Exception as e:
                        current_app.logger.error(f"Failed to cache system metrics: {str(e)}")

            # Store metrics in database for audit (always do this, even from cache)
            for metric_type, data in metrics.items():
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, (int, float)):
                            metric = SystemMetric(
                                metric_type=metric_type,
                                metric_name=key,
                                value=float(value),
                                unit='%' if 'percent' in key else 'GB' if 'gb' in key else 'count'
                            )
                            db.session.add(metric)
            db.session.commit()

            import json
            return f"System Metrics:\n```json\n{json.dumps(metrics, indent=2)}\n```"

        elif tool_name == 'read_file':
            path = tool_input.get('path')
            if not path:
                return "Error: No file path provided"

            # Safety: restrict to allowed directories
            allowed_base = os.getenv('ALLOWED_FILE_PATH', '/root/crm-dashboard')
            if not path.startswith(allowed_base):
                return f"Error: Access denied. Can only read files in {allowed_base}"

            # Check cache first
            cache_hit = False
            content = None
            file_cache_key = None

            if hasattr(current_app, 'cache') and current_app.cache._enabled:
                try:
                    # Get file modification time for cache key validation
                    import os
                    mtime = str(os.path.getmtime(path)) if os.path.exists(path) else None
                    file_cache_key = generate_file_content_key(path, mtime)
                    cached_content = current_app.cache.get(file_cache_key)
                    if cached_content is not None:
                        content = cached_content
                        cache_hit = True
                        current_app.logger.debug(f"File cache HIT: {path}")
                except Exception as e:
                    current_app.logger.warning(f"File cache check failed: {str(e)}")

            if not cache_hit:
                try:
                    with open(path, 'r') as f:
                        content = f.read()

                    # Cache file content for 5 minutes
                    if hasattr(current_app, 'cache') and current_app.cache._enabled and file_cache_key:
                        try:
                            current_app.cache.set(file_cache_key, content, ttl_seconds=current_app.config.get('CACHE_TTL_FILE', 300))
                            current_app.logger.debug(f"File cached: {path}")
                        except Exception as e:
                            current_app.logger.error(f"Failed to cache file {path}: {str(e)}")
                except Exception as e:
                    return f"Error reading file: {str(e)}"

            return f"File: {path}\n\n```\n{content[:4000]}\n```"

        else:
            return f"Error: Unknown tool '{tool_name}'"

    except Exception as e:
        return f"Tool execution error: {str(e)}"


@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """Main AI chat endpoint with tool calling"""
    current_user = g.current_user
    data = request.json

    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400

    user_message = data['message']
    conversation_id = data.get('conversation_id')

    # Get or create conversation
    if conversation_id:
        conversation = AIConversation.query.get(conversation_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
    else:
        conversation = AIConversation(
            user_id=g.current_user.id,
            title=user_message[:100] + ('...' if len(user_message) > 100 else '')
        )
        db.session.add(conversation)
        db.session.commit()

    # Save user message
    user_msg = AIMessage(
        conversation_id=conversation.id,
        role='user',
        content=user_message
    )
    db.session.add(user_msg)

    # Build conversation history for context
    history = get_conversation_context(conversation.id, limit=15)

    # Build system prompt with current time
    system_prompt = SYSTEM_PROMPT + "\n\nCurrent time: " + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    # Generate cache keys for response caching
    cache_enabled = current_app.config.get('CACHE_ENABLED', True) if hasattr(current_app, 'cache') else False
    ai_response_cache_key = None
    ai_stateless_cache_key = None

    if cache_enabled:
        # Create a hash of the conversation context to capture conversation state
        import hashlib
        context_str = json.dumps([{'role': h['role'], 'content': h['content'][:200]} for h in history], sort_keys=True)
        context_hash = hashlib.sha256(context_str.encode()).hexdigest()[:16]
        ai_response_cache_key = generate_ai_response_key(
            user_message,
            context_hash,
            MODEL
        )
        # Also generate a stateless cache key for common questions (no conversation context)
        ai_stateless_cache_key = generate_ai_stateless_key(user_message)

    # Check cache FIRST before making API call
    cached_response = None
    if cache_enabled and ai_response_cache_key:
        cached_response = current_app.cache.get(ai_response_cache_key)
        if cached_response:
            current_app.logger.info(f"Cache HIT for AI response: {ai_response_cache_key[:32]}...")
            # Still record assistant message in DB to maintain history
            assistant_message = cached_response
            # Skip API call entirely
        elif ai_stateless_cache_key:
            cached_stateless = current_app.cache.get(ai_stateless_cache_key)
            if cached_stateless:
                current_app.logger.info(f"Cache HIT (stateless) for AI response: {ai_stateless_cache_key[:32]}...")
                assistant_message = cached_stateless
                # We'll still continue to store in DB and return, but not cache to conversation-specific key

    try:
        if not cached_response:
            # Define tools
            tools = [
                {
                    "name": "execute_command",
                    "description": "Execute a shell command on the server",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "The shell command to execute"},
                            "timeout": {"type": "number", "description": "Timeout in seconds (default 30)"}
                        },
                        "required": ["command"]
                    }
                },
                {
                    "name": "query_database",
                    "description": "Execute a SQL query on the database",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "SQL query to execute"},
                            "allow_write": {"type": "boolean", "description": "Allow write operations (INSERT, UPDATE, DELETE)"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "create_cron_job",
                    "description": "Create a scheduled cron job",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Job name"},
                            "command": {"type": "string", "description": "Command to run"},
                            "schedule": {"type": "string", "description": "Cron expression (e.g., '0 2 * * *')"},
                            "description": {"type": "string", "description": "Description"}
                        },
                        "required": ["name", "command", "schedule"]
                    }
                },
                {
                    "name": "get_system_metrics",
                    "description": "Get current system metrics (CPU, memory, disk, network, processes)",
                    "input_schema": {"type": "object", "properties": {}}
                },
                {
                    "name": "read_file",
                    "description": "Read a file from the filesystem (project directory only)",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path to read"}
                        },
                        "required": ["path"]
                    }
                }
            ]

        # Call AI API with tools
        response = anthropic_client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=system_prompt,
            messages=history,
            tools=tools
        )

        # Process response - handle tool use blocks
        assistant_message = ""
        tool_uses = []

        for block in response.content:
            if hasattr(block, 'text') and block.text:
                assistant_message += block.text
            elif hasattr(block, 'type') and block.type == 'tool_use':
                tool_uses.append({
                    'id': block.id,
                    'name': block.name,
                    'input': block.input
                })

        # If AI wants to use tools, execute them and get final response
        if tool_uses:
            print(f"[AI] Requested {len(tool_uses)} tool(s): {[t['name'] for t in tool_uses]}")

            # Execute each tool
            tool_results = []
            for tool_use in tool_uses:
                tool_name = tool_use['name']
                tool_input = tool_use['input']
                result = execute_tool(tool_name, tool_input, conversation.id, g.current_user.email)
                tool_results.append({
                    'type': 'tool_result',
                    'tool_use_id': tool_use['id'],
                    'content': result
                })

            # Send tool results back to Claude to get final response
            messages_with_results = history + [
                {"role": "assistant", "content": [{"type": "tool_use", **t} for t in tool_uses]},
                {"role": "user", "content": tool_results}
            ]

            try:
                final_response = anthropic_client.messages.create(
                    model=MODEL,
                    max_tokens=4000,
                    system=system_prompt,
                    messages=messages_with_results
                )

                # Extract final message
                assistant_message = ""
                for block in final_response.content:
                    if hasattr(block, 'text') and block.text:
                        assistant_message += block.text
            except Exception as e:
                assistant_message = f"I encountered an error while processing the results: {str(e)}"

        if not assistant_message.strip():
            assistant_message = "I apologize, but I couldn't generate a response. Please try again."

        # Cache the AI response if we just computed it (not from cache)
        # and if caching is enabled
        if cache_enabled and not cached_response and assistant_message:
            # Cache in conversation-specific cache (long TTL)
            if ai_response_cache_key:
                try:
                    current_app.cache.set(ai_response_cache_key, assistant_message, ttl_seconds=current_app.config.get('CACHE_TTL_AI_RESPONSE', 86400))
                    current_app.logger.info(f"Cached AI response with key: {ai_response_cache_key[:32]}...")
                except Exception as e:
                    current_app.logger.error(f"Failed to cache AI response: {str(e)}")

            # Also cache in stateless cache for common questions (shorter TTL)
            if ai_stateless_cache_key and current_app.config.get('CACHE_TTL_AI_STATELESS', 3600) > 0:
                try:
                    current_app.cache.set(ai_stateless_cache_key, assistant_message, ttl_seconds=current_app.config.get('CACHE_TTL_AI_STATELESS', 3600))
                    current_app.logger.debug(f"Cached AI response (stateless) with key: {ai_stateless_cache_key[:32]}...")
                except Exception as e:
                    current_app.logger.error(f"Failed to cache stateless AI response: {str(e)}")

        # Save assistant message and update conversation in a single transaction
        # with retry on deadlock
        assistant_msg = AIMessage(
            conversation_id=conversation.id,
            role='assistant',
            content=assistant_message
        )
        db.session.add(assistant_msg)
        conversation.updated_at = datetime.utcnow()

        # Retry commit on deadlock/lock timeout
        for attempt in range(MAX_RETRIES):
            try:
                db.session.commit()
                break
            except OperationalError as e:
                # Check if it's a deadlock or lock wait timeout
                if hasattr(e.orig, 'args') and len(e.orig.args) > 0:
                    errcode = e.orig.args[0]
                    if errcode in (1205, 1213):
                        db.session.rollback()
                        if attempt < MAX_RETRIES - 1:
                            current_app.logger.warning(f"Commit deadlocked, retrying ({attempt + 1}/{MAX_RETRIES})...")
                            time.sleep(RETRY_DELAY * (attempt + 1))
                            continue
                        else:
                            current_app.logger.error(f"Commit failed after {MAX_RETRIES} retries due to deadlock")
                            raise
                raise

        # Invalidate conversation context cache to ensure next request gets fresh history
        try:
            if cache_enabled and hasattr(current_app, 'cache') and current_app.cache._enabled:
                current_app.cache.invalidate_pattern(f"conv:{conversation.id}:")
                current_app.logger.debug(f"Invalidated context cache for conversation {conversation.id}")
        except Exception as e:
            current_app.logger.error(f"Cache invalidation failed: {str(e)}")

        return jsonify({
            'response': assistant_message,
            'conversation_id': conversation.id,
            'message_id': assistant_msg.id
        })

    except Exception as e:
        current_app.logger.error(f'AI Chat Error: {str(e)}')
        return jsonify({'error': f'AI service error: {str(e)}'}), 500

@ai_bp.route('/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get all conversations for the current user."""
    # This uses the old AIAssistant models (AIConversation, AIMessage)
    conversations = AIConversation.query.filter_by(user_id=g.current_user.id).order_by(AIConversation.updated_at.desc()).all()
    result = []
    for conv in conversations:
        result.append({
            'id': conv.id,
            'title': conv.title,
            'created_at': conv.created_at.isoformat() if conv.created_at else None,
            'updated_at': conv.updated_at.isoformat() if conv.updated_at else None,
            'message_count': len(conv.messages) if hasattr(conv, 'messages') else 0
        })
    return jsonify(result), 200

@ai_bp.route('/conversations/<int:conv_id>/messages', methods=['GET'])
@login_required
def get_conversation_messages(conv_id):
    """Get messages for a conversation."""
    conversation = AIConversation.query.filter_by(id=conv_id, user_id=g.current_user.id).first()
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    messages = AIMessage.query.filter_by(conversation_id=conv_id).order_by(AIMessage.timestamp.asc()).all()
    result = []
    for msg in messages:
        result.append({
            'id': msg.id,
            'conversation_id': msg.conversation_id,
            'role': msg.role,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
            'action_taken': msg.action_taken,
            'command_executed': msg.command_executed,
            'command_output': msg.command_output
        })
    return jsonify(result), 200

@ai_bp.route('/execute', methods=['POST'])
@login_required
def execute_command():
    """Execute a shell command directly (not via AI)."""
    data = request.json
    if not data or 'command' not in data:
        return jsonify({'error': 'Command is required'}), 400
    command = data['command']
    timeout = data.get('timeout', 30)
    # Safety check
    is_safe, reason = is_safe_command(command)
    if not is_safe:
        return jsonify({'error': f'Command blocked: {reason}'}), 400
    # Execute
    result = execute_shell_command(command, timeout)
    # Log
    cmd_log = SystemCommandLog(
        command=command,
        executed_by=g.current_user.email,
        output=result.get('stdout', '') + result.get('stderr', ''),
        exit_code=result.get('exit_code', -1),
        execution_time=0,
        status='success' if result.get('success') else 'failed'
    )
    db.session.add(cmd_log)
    db.session.commit()
    return jsonify({
        'exit_code': result.get('exit_code'),
        'stdout': result.get('stdout', ''),
        'stderr': result.get('stderr', '')
    }), 200

@ai_bp.route('/system/metrics', methods=['GET'])
@login_required
def get_system_metrics():
    """Get current system metrics."""
    # Use cache if available
    try:
        metrics = {}
        cache_hit = False
        metrics_cache_key = f"system_metrics:{int(datetime.now().timestamp() // 15)}"  # 15-second buckets
        
        if hasattr(current_app, 'cache') and current_app.cache._enabled:
            cached_metrics = current_app.cache.get(metrics_cache_key)
            if cached_metrics is not None:
                metrics = cached_metrics
                cache_hit = True
                current_app.logger.debug("System metrics cache HIT")
        
        if not cache_hit:
            # Get top memory processes
            processes = []
            try:
                import psutil
                all_procs = []
                for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                    try:
                        pinfo = proc.info
                        if pinfo['memory_info']:
                            all_procs.append({
                                'pid': pinfo['pid'],
                                'name': pinfo['name'],
                                'memory_mb': pinfo['memory_info'].rss / (1024 * 1024)  # Convert to MB
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                # Sort by memory and get top 5
                all_procs.sort(key=lambda x: x['memory_mb'], reverse=True)
                processes = all_procs[:5]
            except Exception as e:
                current_app.logger.warning(f"Failed to get process info: {e}")

            metrics = {
                'cpu': {
                    'percent': psutil.cpu_percent(interval=1),
                    'count': psutil.cpu_count(),
                },
                'memory': {
                    'percent': psutil.virtual_memory().percent,
                    'used_gb': psutil.virtual_memory().used / (1024**3),
                    'total_gb': psutil.virtual_memory().total / (1024**3),
                    'available_gb': psutil.virtual_memory().available / (1024**3),
                },
                'disk': {
                    'percent': psutil.disk_usage('/').percent,
                    'used_gb': psutil.disk_usage('/').used / (1024**3),
                    'total_gb': psutil.disk_usage('/').total / (1024**3),
                    'free_gb': psutil.disk_usage('/').free / (1024**3),
                },
                'processes': {
                    'count': len(psutil.pids()),
                    'top_memory': processes
                },
                'network': {
                    'io_counters': psutil.net_io_counters()._asdict()
                }
            }
            if hasattr(current_app, 'cache') and current_app.cache._enabled:
                try:
                    current_app.cache.set(metrics_cache_key, metrics, ttl_seconds=15)
                    current_app.logger.debug("System metrics cached")
                except Exception as e:
                    current_app.logger.error(f"Failed to cache metrics: {e}")
        return jsonify(metrics), 200
    except Exception as e:
        current_app.logger.error(f'Metrics Error: {str(e)}')
        return jsonify({'error': str(e)}), 500

@ai_bp.route('/cron/list', methods=['GET'])
@login_required
def list_cron_jobs():
    """List all cron jobs."""
    jobs = SystemCronJob.query.order_by(SystemCronJob.created_at.desc()).all()
    result = []
    for job in jobs:
        result.append({
            'id': job.id,
            'name': job.name,
            'command': job.command,
            'schedule': job.schedule,
            'enabled': job.enabled,
            'created_by': job.created_by,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'last_run': job.last_run.isoformat() if job.last_run else None,
            'last_output': job.last_output,
            'description': job.description
        })
    return jsonify(result), 200

@ai_bp.route('/cron/create', methods=['POST'])
@login_required
def create_cron_job():
    """Create a new cron job."""
    data = request.json
    if not data or not data.get('name') or not data.get('command') or not data.get('schedule'):
        return jsonify({'error': 'Name, command, and schedule are required'}), 400
    # Validate cron expression (simple 5-part check)
    schedule_parts = data['schedule'].split()
    if len(schedule_parts) != 5:
        return jsonify({'error': 'Invalid cron expression. Use format: minute hour day month weekday'}), 400
    # Safety check command
    is_safe, reason = is_safe_command(data['command'])
    if not is_safe:
        return jsonify({'error': f'Command blocked: {reason}'}), 400
    job = SystemCronJob(
        name=data['name'],
        command=data['command'],
        schedule=data['schedule'],
        enabled=data.get('enabled', True),
        created_by=g.current_user.email,
        description=data.get('description', '')
    )
    db.session.add(job)
    db.session.commit()
    return jsonify({
        'id': job.id,
        'name': job.name,
        'command': job.command,
        'schedule': job.schedule,
        'enabled': job.enabled,
        'created_by': job.created_by,
        'description': job.description
    }), 201

@ai_bp.route('/cron/delete/<int:job_id>', methods=['DELETE'])
@login_required
def delete_cron_job(job_id):
    """Delete a cron job."""
    job = SystemCronJob.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    return jsonify({'message': 'Cron job deleted'}), 200

@ai_bp.route('/logs/system', methods=['GET'])
@login_required
def get_system_logs():
    """Get system command logs."""
    limit = request.args.get('limit', 50, type=int)
    logs = SystemCommandLog.query.order_by(SystemCommandLog.executed_at.desc()).limit(limit).all()
    result = []
    for log in logs:
        result.append({
            'id': log.id,
            'command': log.command,
            'executed_by': log.executed_by,
            'conversation_id': log.conversation_id,
            'output': log.output,
            'exit_code': log.exit_code,
            'execution_time': log.execution_time,
            'executed_at': log.executed_at.isoformat() if log.executed_at else None,
            'status': log.status
        })
    return jsonify(result), 200

@ai_bp.route('/logs/app', methods=['GET'])
@login_required
def get_app_logs():
    """Get application logs (placeholder - would read from log files)."""
    # For now, return recent activity logs
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(50).all()
    result = []
    for log in logs:
        result.append({
            'id': log.id,
            'action': log.action,
            'details': log.details,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None
        })
    return jsonify(result), 200
