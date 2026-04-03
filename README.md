# Max AI Agent

AI-powered system administration and automation platform.

## Features

- **Natural Language Chat** - Interact with Max AI to perform tasks using real-time WebSocket
- **Dual-Model AI** - Internal model learns from external AI responses for faster, cost-effective operation
- **Image Upload** - Send images in chat for visual context (supports all file types in Knowledge Base)
- **Knowledge Base Integration** - AI automatically reads and references knowledge base articles
- **System Administration** - Execute shell commands, manage files, monitor processes
- **Database Querying** - Run SQL queries with audit logging
- **Cron Job Management** - Create, view, and delete scheduled tasks
- **System Metrics** - Real-time CPU, memory, disk, and network monitoring
- **Complete Audit Trail** - All actions logged for security and compliance

## Tech Stack

**Backend:**
- Python 3.11+
- Flask REST API with WebSocket (Flask-SocketIO)
- MySQL Database (SQLAlchemy ORM)
- Dual-model AI system (Max-model1)
- Real-time bidirectional communication

**Frontend:**
- React 18 (SPA)
- React Router for navigation
- Socket.IO client for real-time chat
- Axios for API calls
- Tailwind CSS for styling

## Quick Start

### Prerequisites
- Python 3.11+
- MySQL database (shared with order-tracker)
- Anthropic API key or OpenRouter API key

### 1. Environment Setup

```bash
cd max-ai-agent/backend
cp .env.template .env
```

Edit `.env` and configure:
- Database connection (use same DB as order-tracker)
- Max Model 1 Configuration:
  ```
  # Internal model type (embeddings, hybrid, or simple)
  MAX_MODEL1_INTERNAL_TYPE=embeddings

  # External AI API (OpenAI, Anthropic, or OpenRouter)
  MAX_MODEL1_EXTERNAL_API_URL=https://openrouter.ai/api/v1
  MAX_MODEL1_EXTERNAL_API_KEY=sk-or-v1-xxxxx
  MAX_MODEL1_EXTERNAL_MODEL=stepfun/step-3.5-flash:free

  # Confidence threshold for internal model (0.0-1.0)
  MAX_MODEL1_CONFIDENCE_THRESHOLD=0.7
  ```
- WebSocket configuration:
  ```
  SOCKET_CORS_ALLOWED_ORIGINS=http://localhost:3000
  ```
- AI API credentials (for fallback or direct use):
  ```
  ANTHROPIC_BASE_URL=https://openrouter.ai/api
  ANTHROPIC_AUTH_TOKEN=sk-or-v1-xxxxx
  ANTHROPIC_MODEL=stepfun/step-3.5-flash:free
  ```

### 2. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Database Migration

Create the AI Assistant tables in your existing database:

```bash
python migrate_ai_tables.py
```

The migration will also create tables for Max-model1 training data and chat attachments.

### 4. Run Backend

```bash
python app.py
```

Backend will start on http://localhost:8091

### 5. Run Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Frontend will start on http://localhost:3000

### 6. Login

Use the same admin credentials as order-tracker:
- Email: `admin@example.com`
- Password: `admin123`

## Recent Updates (April 2026)

- ✅ **Tool Calling Implementation**: AI can now execute real commands (shell, database queries, file operations)
- ✅ **Markdown Rendering**: Responses display with proper formatting (tables, bold, lists, code)
- ✅ **Improved Streaming**: Responses stream in natural sentence chunks
- ✅ **Fixed UI Issues**: Message disappearing, sidebar toggle, height, scrollbars

## Testing Tool Calling

After starting both servers, test if the AI can execute commands:

1. Open the AI Assistant at `/ai-assistant`
2. Ask: **"What time is it now?"**
3. Expected: AI executes `date` command and shows actual output

Other test queries:
- "Show active processes" → runs `ps aux`
- "How many orders today?" → queries database
- "List files in the project" → runs `ls`
- "Check disk usage" → runs `df -h`

### Debugging

Check backend logs for tool execution:
```bash
# Look for [ToolCall] messages
tail -f logs/app.log  # or wherever your logs are stored
```

Expected log output:
```
[ToolCall] Available tools: ['execute_shell_command', 'query_database', ...]
[ToolCall] Sending request to https://openrouter.ai/api/v1 with X tools
[ToolCall] Received response with keys: [...]
[ToolCall] Initial response: N tool calls
[ToolCall] Executing execute_shell_command with input: {'command': 'date'}
[ToolCall] Result: Mon Apr  3 05:30:45 UTC 2026
```

If AI says "I don't have access", verify:
- API key is valid and model supports tool calling (Claude 3.5 Sonnet+)
- Tools are registered (check logs for "Available tools")
- `execute_shell_command` has `requires_approval=False` in `agent_framework/tools/implementations.py`

## Production Deployment

### Systemd Service

```bash
sudo cp max-ai-agent.service /etc/systemd/system/
sudo systemctl enable --now max-ai-agent
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name max-ai-agent.yourdomain.com;

    location / {
        root /var/www/max-ai-agent;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8091;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## API Endpoints

### Authentication
- `POST /api/login` - Login
- `GET /api/verify` - Verify token
- `POST /api/logout` - Logout

### AI Chat (WebSocket + REST)
- `WS /ws` - WebSocket connection for real-time chat
- `POST /api/ai/chat` - Send message to AI (REST fallback)
- `GET /api/ai/conversations` - List conversations
- `GET /api/ai/conversations/:id/messages` - Get conversation messages
- `POST /api/chat/upload` - Upload attachments (images/files) to chat

### Max Model 1
- `GET /api/ai/models/max-model1/status` - Get model statistics
- `POST /api/ai/models/max-model1/train` - Trigger model retraining
- `GET /api/ai/models/max-model1/stats` - Training data statistics

### System Operations
- `POST /api/ai/execute` - Execute shell command
- `GET /api/ai/system/metrics` - Get system metrics
- `GET /api/ai/processes` - List processes
- `POST /api/ai/processes/:pid/kill` - Kill process

### Database
- `POST /api/ai/db/query` - Execute SQL query

### File System
- `POST /api/ai/files/read` - Read file
- `POST /api/ai/files/write` - Write file

### Cron Jobs
- `GET /api/ai/cron/list` - List cron jobs
- `POST /api/ai/cron/create` - Create cron job
- `DELETE /api/ai/cron/delete/:id` - Delete cron job

### Logs
- `GET /api/ai/logs/system?limit=50` - System command logs
- `GET /api/ai/logs/app` - Application logs

### Knowledge Base
- `GET /api/kb` - Get all KB entries (filter by category)
- `POST /api/kb` - Create KB entry
- `GET /api/kb/search` - Search KB
- `GET /api/kb/categories` - Get all categories

## Security Considerations

⚠️ **WARNING**: The AI Assistant has full system access. Only trusted admin users should have access.

### Built-in Safety Measures
- Authentication required for all endpoints
- Dangerous command blocklist (rm -rf, sudo, dd, mkfs, shutdown, etc.)
- File operations restricted to project directory
- Complete audit logging of all AI actions
- Conversation history stored for accountability

### Production Recommendations
1. Use a dedicated system user with limited sudo privileges
2. Implement command approval workflow
3. Run in Docker container for isolation
4. Set database to read-only by default
5. Network segmentation to block external access
6. Regular review of audit logs
7. Rotate API keys periodically

## Architecture

Max AI Agent is a standalone system administration and automation platform. It shares the same database with the Order Tracker application for user authentication but operates independently. The AI assistant (powered by Claude via Max-model1) has full system access to automate tasks, monitor metrics, and execute commands - all with complete audit trails.

### Max-model1 Architecture

The dual-model system consists of:
1. **Internal Model**: Fast, lightweight retrieval-based model using embeddings and FAISS for similarity search. Stores learned responses locally.
2. **External Model**: Configurable API (Anthropic, OpenAI, etc.) for high-quality responses.
3. **Learning Loop**: External model responses are stored in training data. Periodic retraining improves the internal model.

### WebSocket Real-Time Communication

Bidirectional WebSocket connection enables:
- Instant message delivery
- Streaming AI responses (token by token)
- Typing indicators
- Multi-user collaboration

### Knowledge Base Integration

All AI responses automatically incorporate relevant knowledge base articles via semantic search, providing accurate, domain-specific answers.

## Troubleshooting

### AI says "I don't have access" or gives generic responses

**Cause**: Tool calling not properly configured or model doesn't support tools.

**Solutions**:
1. Verify `MAX_MODEL1_EXTERNAL_MODEL` is Claude 3.5 Sonnet or newer (tool-capable)
2. Check backend logs for `[ToolCall] Available tools:` message — if empty, tools not registered
3. Ensure `agent_framework/tools/implementations.py` is imported at startup (it is via `agent_framework/__init__.py`)
4. Confirm API key has access to the specified model

### WebSocket disconnects frequently

**Cause**: Ping timeout, network issue, or server restarted.

**Solutions**:
1. Increase WebSocket ping timeout in Flask-SocketIO configuration
2. Check server resource usage (high CPU/memory may cause restarts)
3. Verify `SOCKET_CORS_ALLOWED_ORIGINS` includes your frontend URL

### No messages appear in chat

**Cause**: Backend not running, CORS issue, or auth failure.

**Solutions**:
1. Confirm backend is running on port 8091 (or configured `PORT`)
2. Check browser console for errors
3. Verify `.env` has correct database credentials and API keys
4. Re-login to refresh authentication token

### Frontend not updating after code changes

**Solutions**:
1. Hard refresh browser: `Ctrl + Shift + R` (or `Cmd + Shift + R` on Mac)
2. Clear browser cache
3. Restart Vite dev server

### Deployment issues

**Common problems**:
- Missing environment variables → check `.env` file
- Database connection failed → verify MySQL credentials and that DB exists
- Port already in use → change `PORT` in `.env`
- Permission errors → ensure user has read/write access to project directory

**Enable debug logging**:
In `.env`, set `DEBUG=true` and check logs:
```bash
tail -f logs/app.log
```

## License

MIT License
