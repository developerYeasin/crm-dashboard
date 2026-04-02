#!/bin/bash
set -e

echo "=== Installing CRM Dashboard ==="

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Installation complete! ==="
echo ""
echo "Next steps:"
echo "1. Copy .env.template to .env and configure it"
echo "2. Run: python migrate_ai_tables.py"
echo "3. Start the server: python app.py"
echo ""
echo "Or use systemd:"
echo "  sudo cp ../crm-dashboard.service /etc/systemd/system/"
echo "  sudo systemctl enable --now crm-dashboard"
echo ""
