#!/bin/bash
set -e
echo "🔐 BIOS Cloud Gateway v1.1 (Linux)"
if [ ! -d "venv" ]; then
    echo "📦 Создаю venv..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
echo "🌐 Откройте: http://127.0.0.1:5000"
python3 api_server.py
