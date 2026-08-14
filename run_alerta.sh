#!/usr/bin/env bash
# Roda o alerta orçamentário do CFC. Disparado diariamente via cron.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f "$DIR/.env" ]; then
  set -a
  source "$DIR/.env"
  set +a
fi

python3 "$DIR/cfc_orcamento.py" --alertar
