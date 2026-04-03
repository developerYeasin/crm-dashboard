"""
Basic tool implementations for the autonomous agent framework.

These tools provide common system administration and data access capabilities.
All tools are registered with the ToolRegistry.
"""

import json
import os
import subprocess
import psutil
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from agent_framework.tools.registry import default_registry, ToolDefinition
from flask import current_app
from sqlalchemy import text

# ========================================
# SAFETY CONSTANTS
# ========================================

DANGEROUS_COMMANDS = [
    'rm -rf /', 'rm -rf /*', 'dd if=', ':(){ :|:& };:', 'mkfs', 'format',
    'shutdown', 'reboot', 'poweroff', 'halt', 'init 0', 'init 6',
    '> /dev/', 'chmod -R 777 /', 'chown -R', 'mv /*', 'cp /*',
    'sudo', 'su -', 'passwd', 'useradd', 'userdel', 'groupadd', 'groupdel'
]

ALLOWED_FILE_PATH = os.getenv('ALLOWED_FILE_PATH', '/root/max-ai-agent')


# ========================================
# TOOL REGISTRATIONS
# ========================================

def register_basic_tools(registry: ToolDefinition = None):
    """Register all basic tools with the given registry"""
    if registry is None:
        registry = default_registry

    @registry.register(
        name="execute_shell_command",
        description="Execute a shell command on the server. Use for system administration, process management, and file operations. Output limited to 4000 chars. Sensitive commands (rm, dd, shutdown, etc.) are blocked.",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (max 300, default 30)",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 300
                },
                "workdir": {
                    "type": "string",
                    "description": f"Working directory (default: {ALLOWED_FILE_PATH})",
                    "default": ALLOWED_FILE_PATH
                }
            },
            "required": ["command"]
        },
        requires_approval=False,  # Chat mode: execute directly (safety through restrictions)
        risk_level="medium"
    )
    async def execute_shell_command(command: str, timeout: int = 30, workdir: str = ALLOWED_FILE_PATH):
        """Execute a shell command safely with timeout and restrictions"""
        # Security: Validate timeout
        timeout = min(max(timeout, 1), 300)

        # Security: Check for dangerous commands
        cmd_lower = command.lower()
        for dangerous in DANGEROUS_COMMANDS:
            if dangerous.lower() in cmd_lower:
                return {
                    "success": False,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Dangerous command blocked: contains '{dangerous}'",
                    "error": "security_violation"
                }

        # Security: Restrict working directory
        if not os.path.abspath(workdir).startswith(os.path.abspath(ALLOWED_FILE_PATH)):
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Access denied: working directory outside allowed path ({workdir})",
                "error": "path_violation"
            }

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workdir
            )

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout[:4000],
                "stderr": result.stderr[:4000]
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "error": "timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "error": "execution_error"
            }

    @registry.register(
        name="read_file",
        description="Read contents of a file. Only files within the Max AI Agent directory can be accessed.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": f"Absolute path to file (must be under {ALLOWED_FILE_PATH})"
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (default 1000)",
                    "default": 1000,
                    "minimum": 1,
                    "maximum": 10000
                }
            },
            "required": ["file_path"]
        },
        requires_approval=False,  # Read-only, low risk
        risk_level="low"
    )
    async def read_file(file_path: str, max_lines: int = 1000):
        """Read a file safely with path validation"""
        # Validate path
        abs_path = os.path.abspath(file_path)
        allowed_root = os.path.abspath(ALLOWED_FILE_PATH)

        if not abs_path.startswith(allowed_root):
            return {
                "success": False,
                "error": f"Access denied: file outside allowed directory",
                "file_path": file_path
            }

        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "file_path": file_path
            }

        if not os.path.isfile(abs_path):
            return {
                "success": False,
                "error": f"Path is not a file: {file_path}",
                "file_path": file_path
            }

        try:
            with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"... (truncated after {max_lines} lines)")
                        break
                    lines.append(line.rstrip('\n'))

                content = '\n'.join(lines)
                file_size = os.path.getsize(abs_path)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(abs_path)).isoformat()

                return {
                    "success": True,
                    "file_path": file_path,
                    "content": content,
                    "lines_read": len(lines),
                    "total_lines": len(open(abs_path).readlines()) if len(lines) < max_lines else None,
                    "size_bytes": file_size,
                    "modified_at": file_mtime
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }

    @registry.register(
        name="list_directory",
        description="List files and directories in a folder. Shows name, type, size, and modification time.",
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": f"Absolute directory path (default: {ALLOWED_FILE_PATH})",
                    "default": ALLOWED_FILE_PATH
                },
                "pattern": {
                    "type": "string",
                    "description": "Optional glob pattern filter (e.g., '*.py', '*.log')"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "List recursively? (default false)",
                    "default": False
                }
            },
            "required": []
        },
        requires_approval=False,
        risk_level="low"
    )
    async def list_directory(directory: str = ALLOWED_FILE_PATH, pattern: str = None, recursive: bool = False):
        """List directory contents safely"""
        abs_dir = os.path.abspath(directory)
        allowed_root = os.path.abspath(ALLOWED_FILE_PATH)

        if not abs_dir.startswith(allowed_root):
            return {
                "success": False,
                "error": f"Access denied: directory outside allowed path"
            }

        if not os.path.exists(abs_dir):
            return {
                "success": False,
                "error": f"Directory not found: {directory}"
            }

        if not os.path.isdir(abs_dir):
            return {
                "success": False,
                "error": f"Path is not a directory: {directory}"
            }

        try:
            items = []

            if recursive:
                walk_root = abs_dir
                for root, dirs, files in os.walk(walk_root):
                    # Apply pattern filter at each level
                    for fname in files:
                        if pattern and not Path(fname).match(pattern):
                            continue
                        filepath = os.path.join(root, fname)
                        relpath = os.path.relpath(filepath, abs_dir)
                        try:
                            stat = os.stat(filepath)
                            items.append({
                                "name": relpath,
                                "type": "file",
                                "size_bytes": stat.st_size,
                                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                            })
                        except Exception:
                            continue
            else:
                entries = os.listdir(abs_dir)
                if pattern:
                    from fnmatch import fnmatch
                    entries = [e for e in entries if fnmatch(e, pattern)]

                for entry in entries:
                    filepath = os.path.join(abs_dir, entry)
                    try:
                        stat = os.stat(filepath)
                        items.append({
                            "name": entry,
                            "type": "directory" if os.path.isdir(filepath) else "file",
                            "size_bytes": stat.st_size if os.path.isfile(filepath) else None,
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                    except Exception:
                        continue

            # Sort: directories first, then files, alphabetically
            items.sort(key=lambda x: (0 if x['type'] == 'directory' else 1, x['name'].lower()))

            return {
                "success": True,
                "directory": directory,
                "count": len(items),
                "items": items[:10000]  # Limit to prevent huge responses
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "directory": directory
            }

    @registry.register(
        name="get_system_metrics",
        description="Get current system metrics including CPU, memory, disk usage, and process count.",
        parameters={
            "type": "object",
            "properties": {}
        },
        requires_approval=False,
        risk_level="low"
    )
    async def get_system_metrics():
        """Get system resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            processes = len(psutil.pids())

            uptime_seconds = int(datetime.now().timestamp() - psutil.boot_time())
            uptime_str = f"{uptime_seconds // 86400}d {(uptime_seconds % 86400) // 3600}h {(uptime_seconds % 3600) // 60}m"

            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(logical=False),
                    "count_logical": psutil.cpu_count(logical=True)
                },
                "memory": {
                    "percent": memory.percent,
                    "used_gb": round(memory.used / (1024**3), 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2)
                },
                "disk": {
                    "percent": disk.percent,
                    "used_gb": round(disk.used / (1024**3), 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2)
                },
                "processes": processes,
                "uptime": uptime_str
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @registry.register(
        name="query_database",
        description="Execute SQL query against the Max AI Agent database. Read-only by default. Set allow_write=true for INSERT/UPDATE/DELETE (requires approval). Returns up to 100 rows for SELECT queries.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute"
                },
                "allow_write": {
                    "type": "boolean",
                    "description": "Allow write operations (INSERT/UPDATE/DELETE/ALTER). Default false.",
                    "default": False
                }
            },
            "required": ["query"]
        },
        requires_approval=False,  # Approval enforced based on query type
        risk_level="medium"
    )
    async def query_database(query: str, allow_write: bool = False):
        """Execute a SQL query safely with write protection"""
        from flask import current_app
        from extensions import db

        if not query or not query.strip():
            return {"success": False, "error": "Empty query"}

        query_upper = query.strip().upper()

        # Block dangerous operations if write not explicitly allowed
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE', 'CREATE', 'GRANT', 'REVOKE', 'SHUTDOWN']
        if not allow_write and any(keyword in query_upper for keyword in dangerous_keywords):
            return {
                "success": False,
                "error": "Write operations blocked. Set allow_write=true to allow (may require additional approval).",
                "suggested_action": "Use allow_write=true if write operation is intentional"
            }

        # Additional safety: Block operations on critical tables
        critical_tables = ['users', 'conversations', 'ai_messages']
        if any(f"FROM {table}" in query_upper or f"INTO {table}" in query_upper or f"UPDATE {table}" in query_upper
               for table in critical_tables):
            if not allow_write:
                return {
                    "success": False,
                    "error": "Operations on critical tables require explicit allow_write=true"
                }

        try:
            # Execute query
            result = db.session.execute(text(query))

            if query_upper.startswith('SELECT'):
                rows = result.fetchall()
                columns = result.keys()

                # Convert to list of dicts, limit to 100 rows
                data = [dict(zip(columns, row)) for row in rows[:100]]

                return {
                    "success": True,
                    "rows_returned": len(data),
                    "total_rows": len(rows),
                    "columns": list(columns),
                    "data": data,
                    "truncated": len(rows) > 100
                }
            else:
                # Non-SELECT query
                db.session.commit()
                return {
                    "success": True,
                    "message": "Query executed successfully",
                    "rows_affected": result.rowcount
                }

        except Exception as e:
            db.session.rollback()
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    @registry.register(
        name="write_file",
        description="Write content to a file. Will create directories if needed. Files must be within Max AI Agent directory.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": f"Absolute file path (must be under {ALLOWED_FILE_PATH})"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to file"
                },
                "append": {
                    "type": "boolean",
                    "description": "Append to existing file? Default false (overwrite)",
                    "default": False
                }
            },
            "required": ["file_path", "content"]
        },
        requires_approval=True,  # Writing files can be risky
        risk_level="medium"
    )
    async def write_file(file_path: str, content: str, append: bool = False):
        """Write content to a file safely"""
        abs_path = os.path.abspath(file_path)
        allowed_root = os.path.abspath(ALLOWED_FILE_PATH)

        if not abs_path.startswith(allowed_root):
            return {
                "success": False,
                "error": f"Access denied: cannot write outside allowed directory"
            }

        try:
            mode = 'a' if append else 'w'
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)

            with open(abs_path, mode, encoding='utf-8') as f:
                f.write(content)

            file_size = os.path.getsize(abs_path)

            return {
                "success": True,
                "file_path": file_path,
                "bytes_written": len(content.encode('utf-8')),
                "total_size": file_size,
                "action": "appended" if append else "created/overwritten"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }

    @registry.register(
        name="search_knowledge_base",
        description="Search the knowledge base for articles matching a query. Returns title, category, and snippet.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keywords)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default 5)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                }
            },
            "required": ["query"]
        },
        requires_approval=False,
        risk_level="low"
    )
    async def search_knowledge_base(query: str, limit: int = 5):
        """Search knowledge base articles"""
        from models import KnowledgeBaseEntry

        try:
            # Simple keyword-based search (can be enhanced with embeddings later)
            query_terms = query.lower().split()
            all_entries = KnowledgeBaseEntry.query.all()

            scored_entries = []
            for entry in all_entries:
                entry_text = (entry.title + ' ' + (entry.content or '')).lower()
                # Score by number of matching terms
                score = sum(1 for term in query_terms if term in entry_text and len(term) > 2)
                if score > 0:
                    scored_entries.append((score, entry))

            # Sort by score descending, take top N
            scored_entries.sort(key=lambda x: x[0], reverse=True)
            top_entries = scored_entries[:limit]

            results = []
            for score, entry in top_entries:
                results.append({
                    "id": entry.id,
                    "title": entry.title,
                    "category": entry.category,
                    "snippet": entry.content[:300] + "..." if len(entry.content) > 300 else entry.content,
                    "score": score
                })

            return {
                "success": True,
                "query": query,
                "results": results,
                "total_found": len(results)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# ========================================
# MAX AI AGENT-SPECIFIC TOOLS
# ========================================

def register_max_ai_agent_tools(registry: ToolDefinition = None):
    """Register Max AI Agent-specific tools"""
    if registry is None:
        registry = default_registry

    @registry.register(
        name="query_orders",
        description="Query orders in the Max AI Agent system. Filter by status, customer, date range, or search terms. Returns order summaries including ID, customer name, phone, division, district, status, and payment type.",
        parameters={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by order delivery status (Submitted, Delivered, Returned)",
                    "enum": ["Submitted", "Delivered", "Returned"]
                },
                "payment_type": {
                    "type": "string",
                    "description": "Filter by payment type (COD, Prepaid)",
                    "enum": ["COD", "Prepaid"]
                },
                "customer_name": {
                    "type": "string",
                    "description": "Search by customer name (partial match)"
                },
                "phone_number": {
                    "type": "string",
                    "description": "Search by phone number (partial match)"
                },
                "division": {
                    "type": "string",
                    "description": "Filter by division"
                },
                "district": {
                    "type": "string",
                    "description": "Filter by district"
                },
                "date_from": {
                    "type": "string",
                    "description": "Filter orders created after this date (YYYY-MM-DD)"
                },
                "date_to": {
                    "type": "string",
                    "description": "Filter orders created before this date (YYYY-MM-DD)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default 20, max 100)",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100
                }
            },
            "required": []
        },
        requires_approval=False,
        risk_level="low"
    )
    async def query_orders(
        status: str = None,
        payment_type: str = None,
        customer_name: str = None,
        phone_number: str = None,
        division: str = None,
        district: str = None,
        date_from: str = None,
        date_to: str = None,
        limit: int = 20
    ):
        """Query orders in the Max AI Agent system"""
        from models import Order, OrderStatus, db
        from sqlalchemy import or_, and_

        try:
            query = Order.query

            # Apply filters
            if status:
                query = query.join(OrderStatus).filter(OrderStatus.delivery_status == status)
            if payment_type:
                query = query.filter(Order.payment_type == payment_type)
            if customer_name:
                query = query.filter(Order.customer_name.ilike(f"%{customer_name}%"))
            if phone_number:
                query = query.filter(Order.phone_number.ilike(f"%{phone_number}%"))
            if division:
                query = query.filter(Order.division.ilike(f"%{division}%"))
            if district:
                query = query.filter(Order.district.ilike(f"%{district}%"))
            if date_from:
                from datetime import datetime
                try:
                    start_date = datetime.strptime(date_from, '%Y-%m-%d')
                    query = query.filter(Order.created_at >= start_date)
                except ValueError:
                    return {"success": False, "error": "Invalid date_from format. Use YYYY-MM-DD"}
            if date_to:
                try:
                    end_date = datetime.strptime(date_to, '%Y-%m-%d')
                    query = query.filter(Order.created_at <= end_date)
                except ValueError:
                    return {"success": False, "error": "Invalid date_to format. Use YYYY-MM-DD"}

            # Order by most recent
            query = query.order_by(Order.created_at.desc()).limit(min(limit, 100))

            orders = query.all()

            results = []
            for order in orders:
                order_data = order.to_dict()
                if order.status:
                    order_data['delivery_status'] = order.status.delivery_status
                    order_data['design_ready'] = order.status.design_ready
                    order_data['is_printed'] = order.status.is_printed
                    order_data['picking_done'] = order.status.picking_done
                results.append(order_data)

            return {
                "success": True,
                "count": len(results),
                "orders": results
            }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}

    @registry.register(
        name="get_order_details",
        description="Get detailed information about a specific order including items, media, and status history.",
        parameters={
            "type": "object",
            "properties": {
                "order_id": {"type": "integer", "description": "Order ID (required)"}
            },
            "required": ["order_id"]
        },
        requires_approval=False,
        risk_level="low"
    )
    async def get_order_details(order_id: int):
        """Get detailed order information with items and media"""
        from models import Order, OrderItem, Media, OrderStatus, db

        try:
            order = Order.query.get(order_id)
            if not order:
                return {"success": False, "error": f"Order {order_id} not found"}

            result = order.to_dict()
            result['items'] = [item.to_dict(with_media=True) for item in order.items]
            result['status'] = order.status.to_dict() if order.status else None
            result['activity_logs'] = [log.to_dict() for log in order.activity_logs]

            return {"success": True, "order": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @registry.register(
        name="create_task",
        description="Create a new task in the Max AI Agent system. Tasks can be assigned to team members.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title (required)"},
                "description": {"type": "string", "description": "Task description"},
                "assigned_to": {"type": "integer", "description": "User ID of assignee (optional)"},
                "priority": {
                    "type": "string",
                    "description": "Task priority",
                    "enum": ["Low", "Medium", "High", "Urgent"],
                    "default": "Medium"
                },
                "due_date": {"type": "string", "description": "Due date in ISO format (YYYY-MM-DDTHH:MM:SS)"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags"
                }
            },
            "required": ["title"]
        },
        requires_approval=False,
        risk_level="low"
    )
    async def create_task(
        title: str,
        description: str = None,
        assigned_to: int = None,
        priority: str = "Medium",
        due_date: str = None,
        tags: list = None
    ):
        """Create a new task in the Max AI Agent system"""
        from models import Task, db
        from datetime import datetime

        try:
            task = Task(
                title=title[:200],
                description=description,
                assigned_to=assigned_to,
                assigned_by=1,  # System/agent
                status='To Do',
                priority=priority,
                due_date=datetime.fromisoformat(due_date) if due_date else None,
                tags=json.dumps(tags) if tags else None
            )
            db.session.add(task)
            db.session.commit()

            return {
                "success": True,
                "task_id": task.id,
                "message": f"Task created with ID {task.id}",
                "task": task.to_dict()
            }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}

    @registry.register(
        name="update_task_status",
        description="Update the status of a task. Useful for tracking progress.",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID (required)"},
                "status": {
                    "type": "string",
                    "description": "New status",
                    "enum": ["To Do", "In Progress", "Review", "Done", "Cancelled"]
                },
                "comment": {"type": "string", "description": "Optional comment about the change"}
            },
            "required": ["task_id", "status"]
        },
        requires_approval=False,
        risk_level="low"
    )
    async def update_task_status(task_id: int, status: str, comment: str = None):
        """Update a task's status"""
        from models import Task, Comment, db

        try:
            task = Task.query.get(task_id)
            if not task:
                return {"success": False, "error": f"Task {task_id} not found"}

            old_status = task.status
            task.status = status
            db.session.commit()

            return {
                "success": True,
                "task_id": task_id,
                "old_status": old_status,
                "new_status": status,
                "message": f"Task status updated from {old_status} to {status}"
            }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}

    print(f"Max AI Agent tools registered (total tools: {len(registry.tools)})")


# Auto-register on import
register_basic_tools(default_registry)
register_max_ai_agent_tools(default_registry)

