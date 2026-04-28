#!/usr/bin/env bash
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required. Install Python 3.11+."; exit 1; }
exec python3 "$(dirname "$0")/installer/main.py" "$@"
