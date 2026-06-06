#!/usr/bin/env bash
set -euo pipefail

python main.py --dry-run --print-config
python main.py
