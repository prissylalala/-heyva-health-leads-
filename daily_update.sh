#!/bin/bash
# Heyva Health — Daily Lead Discovery
PROJECT_DIR="/Users/Priscilla/Downloads/suss_openclaw_export/suss_openclaw"
PYTHON="/usr/bin/python3"
LOG="$PROJECT_DIR/logs/daily_update.log"
# Set GITHUB_TOKEN in your environment or .env file — never hardcode here
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

mkdir -p "$PROJECT_DIR/logs"
echo "=== Daily update started: $(date) ===" >> "$LOG"

cd "$PROJECT_DIR"

# Discover and add new leads
$PYTHON main.py --discover >> "$LOG" 2>&1

# Push to GitHub so Streamlit updates
git add leads_data/indonesia_analyzed.json leads_data/raw_leads.json leads_data/manual_leads.csv >> "$LOG" 2>&1
git commit -m "chore: daily lead update $(date '+%Y-%m-%d')" >> "$LOG" 2>&1
git push https://prissylalala:${GITHUB_TOKEN}@github.com/prissylalala/-heyva-health-leads-.git main >> "$LOG" 2>&1

echo "=== Daily update done: $(date) ===" >> "$LOG"
