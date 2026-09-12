#!/usr/bin/env bash
# Live-collect and validate a Manual Report on CDP2-DevInt using Gavel.
#
# Usage:
#   export PGPASSWORD='...'
#   ./scripts/validate_manual_report_devint.sh <manual_report_id>
#
# Optional:
#   SANDBOX=manual-report-in1290
#   PGHOST=10.51.50.91 PGDATABASE=pcubed_pro PGUSER=admin
#   GAVEL_WO_URL=http://10.51.50.91:8001
#   GAVEL_DAGSTER_URL=http://10.51.50.91:3001
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SANDBOX="${SANDBOX:-manual-report-in1290}"
OUT="${OUT:-$ROOT/reports/manual-report-${MR_ID}.json}"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

MR_ID="${1:-${GAVEL_MR_ID:-${PROOFLINE_MR_ID:-}}}"

if [[ -z "$MR_ID" ]]; then
  echo "Usage: $0 <manual_report_id>" >&2
  echo "Or set GAVEL_MR_ID (or PROOFLINE_MR_ID) in .env" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT")"

python3 -m gavel.cli validate-manual-report "$MR_ID" \
  --sandbox "$SANDBOX" \
  --output "$OUT"

echo "Report: $OUT"
