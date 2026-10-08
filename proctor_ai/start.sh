#!/usr/bin/env bash
set -e

echo ""
echo "============================================================"
echo "   IntegrityShield - AI Exam Proctoring System"
echo "============================================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "[ERROR] python3 not found. Install from https://python.org"
  exit 1
fi

# Create venv if missing
if [ ! -f "venv/bin/activate" ]; then
  echo "[SETUP] Creating virtual environment..."
  python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install/upgrade dependencies
echo "[SETUP] Installing dependencies..."
pip install -r requirements.txt -q

# Create directories
mkdir -p logs static/models

echo ""
echo "[OK] Server starting at http://localhost:5000"
echo "[OK] Press Ctrl+C to stop"
echo ""

python app.py
