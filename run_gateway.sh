#!/usr/bin/env bash
# Atalho para subir a tela do gateway. Exemplos:
#   ./run_gateway.sh --simulate --demo-controls       # ensaio sem hardware
#   ./run_gateway.sh --port /dev/ttyUSB0 --demo-controls
cd "$(dirname "$0")"
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
PYTHONPATH=src exec "$PY" -m coldchain.webapp "$@"
