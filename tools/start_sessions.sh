#!/usr/bin/env bash
# Start one live_session per QA test company (ports 8801..8808), writes on. Logs: artifacts/verify/session_<port>.log
cd "$(dirname "$0")/.."
declare -a CO=("QA Chemist" "QA Pharma Distribution" "QA Billing General" "QA Grocery" "QA Garment" "QA Mobile Trade" "QA Computer Hardware" "QA Automobile")
for i in "${!CO[@]}"; do
  port=$((8801 + i))
  [ -n "$ONLY" ] && [[ " $ONLY " != *" $port "* ]] && continue
  if curl -s -m 5 "http://127.0.0.1:$port/state" >/dev/null 2>&1; then echo "$port already up"; continue; fi
  HEADLESS=true PYTHONIOENCODING=utf-8 nohup .venv/Scripts/python -m tools.live_session --port "$port" --company "${CO[$i]}" --writes \
    > "artifacts/verify/session_$port.log" 2>&1 &
  echo "$port starting: ${CO[$i]}"
done
