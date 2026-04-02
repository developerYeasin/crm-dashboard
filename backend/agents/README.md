# CRM Dashboard AI Agents

This directory contains three autonomous AI agents for the CRM Dashboard system.

## Agents

| Agent | Module | Description |
|-------|--------|-------------|
| QA Agent | `qa_agent.py` | Tests frontend (lint/build) and CRM APIs (tasks, stats, activity) |
| Backend Dev | `backend_dev_agent.py` | Reviews Python code, security scanning, performance suggestions |
| Frontend Dev | `frontend_dev_agent.py` | Reviews React components, accessibility checks, performance |

## Running Agents

### Manually

```bash
cd /root/crm-dashboard/backend
source venv/bin/activate
python -m agents.run_agent --type qa      # QA
python -m agents.run_agent --type backend # Backend Dev
python -m agents.run_agent --type frontend # Frontend Dev
```

### Via API

```bash
# Get token first
TOKEN=$(curl -s -X POST http://localhost:8087/api/login \
  -H "Content-Type: application/json" \
  -d '{"password":"YOUR_ADMIN_PASSWORD"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

# Trigger agent
curl -X POST http://localhost:8087/api/agents/trigger/qa \
  -H "Authorization: Bearer $TOKEN"
```

### Via Systemd Timer

Use the provided timer units:
```bash
sudo systemctl enable --now order-tracker-agent@qa.timer
# etc.
```

## Logging

All agent activities are logged to the CRM `activity_log` table (no task association).

## Development

To add a new agent:

1. Create a new file `agents/your_agent.py`
2. Inherit from `BaseAgent` in `base_agent.py`
3. Implement the `run()` method
4. Add to `run_agent.py` (already done) and optionally Flask API routes

## See Also

- **CRM_AGENTS_MIGRATION.md** - Full setup and usage guide (project root)
- **Telegram Bot** - `/root/telegram_bot.py`

