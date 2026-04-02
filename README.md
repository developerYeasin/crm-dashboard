# CRM Dashboard - AI Assistant

A standalone AI-powered CRM dashboard for system administration, automation, and analytics.

## Features

- **Natural Language Chat** - Interact with Claude AI to perform tasks
- **System Administration** - Execute shell commands, manage files, monitor processes
- **Database Querying** - Run SQL queries with audit logging
- **Cron Job Management** - Create, view, and delete scheduled tasks
- **System Metrics** - Real-time CPU, memory, disk, and network monitoring
- **Complete Audit Trail** - All actions logged for security and compliance

## Tech Stack

**Backend:**
- Python 3.11
- Flask REST API
- MySQL Database (SQLAlchemy ORM)
- Anthropic Claude AI integration

**Frontend:**
- React 18 (SPA)
- React Router for navigation
- Axios for API calls
- Tailwind CSS for styling

## Quick Start

### Prerequisites
- Python 3.11+
- MySQL database (shared with order-tracker)
- Anthropic API key or OpenRouter API key

### 1. Environment Setup

```bash
cd crm-dashboard/backend
cp .env.template .env
```

Edit `.env` and configure:
- Database connection (use same DB as order-tracker)
- AI API credentials:
  - **OpenRouter** (recommended):
    ```
    ANTHROPIC_BASE_URL=https://openrouter.ai/api
    ANTHROPIC_AUTH_TOKEN=sk-or-v1-xxxxx
    ANTHROPIC_MODEL=stepfun/step-3.5-flash:free
    ```
  - **Direct Anthropic**:
    ```
    ANTHROPIC_API_KEY=sk-ant-xxxxx
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

## Production Deployment

### Systemd Service

```bash
sudo cp crm-dashboard.service /etc/systemd/system/
sudo systemctl enable --now crm-dashboard
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name crm.yourdomain.com;

    location / {
        root /var/www/crm-dashboard;
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

### AI Chat
- `POST /api/ai/chat` - Send message to AI
- `GET /api/ai/conversations` - List conversations
- `GET /api/ai/conversations/:id/messages` - Get conversation messages

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

The CRM Dashboard is separate from the Order Tracker application but shares the same database for user authentication. It provides AI-powered system administration capabilities without cluttering the order management interface.

## License

MIT License
