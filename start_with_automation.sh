#!/bin/bash

echo "========================================"
echo "VaultMind with Automation System"
echo "========================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    exit 1
fi

echo "[1/4] Installing automation dependencies..."
pip3 install -q -r requirements-automation.txt
if [ $? -ne 0 ]; then
    echo "WARNING: Some dependencies may have failed to install"
fi

echo
echo "[2/4] Creating logs directory..."
mkdir -p logs

echo
echo "[3/4] Starting automation system in background..."
nohup python3 run_automation_system.py > logs/automation_startup.log 2>&1 &
AUTOMATION_PID=$!
echo "Automation system started (PID: $AUTOMATION_PID)"

echo
echo "Waiting for automation system to initialize..."
sleep 5

echo
echo "[4/4] Starting Streamlit dashboard..."
echo
echo "========================================"
echo "System URLs:"
echo "  Dashboard: http://localhost:8501"
echo "  Metrics:   http://localhost:8000/metrics"
echo "========================================"
echo
echo "Press Ctrl+C to stop the dashboard"
echo "(Automation system will continue running in background)"
echo

streamlit run genai_dashboard_modular.py

echo
echo "Dashboard stopped. Automation system is still running (PID: $AUTOMATION_PID)"
echo "To stop automation: kill $AUTOMATION_PID"
