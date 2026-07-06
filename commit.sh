#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
git add .
git commit -m "refactor(core): adopt modern Python project structure"
git push origin main
