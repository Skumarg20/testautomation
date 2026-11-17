#!/usr/bin/env bash
# One-command entry point. Usage: ./run.sh smoke | regression | discover | explore | triage
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
python -m playwright install --with-deps chromium >/dev/null 2>&1 || true

case "${1:-smoke}" in
  smoke)      pytest --tags smoke ;;
  regression) pytest -m "not destructive or destructive" ;;
  safe)       pytest -m "not destructive" ;;
  discover)   python -m agent.discover --all ;;
  explore)    shift; python -m agent.explore "$@" ;;
  generate)   shift; python -m agent.generate "$@" ;;
  triage)     python -m agent.triage ;;
  *)          pytest "$@" ;;
esac
