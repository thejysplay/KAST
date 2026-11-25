#!/usr/bin/env bash
# Unpack bundled artifacts and calculate primary paper metrics and the built-in comparison without API calls.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA="$ROOT/data"
UNPACK="$DATA/_unpacked"

echo "[1/3] Unpacking scenario + trace archives into data/_unpacked/ ..."
mkdir -p "$UNPACK"
for f in "$DATA"/scenarios/*.tar.gz; do
  e="$(basename "$f" .tar.gz)"; mkdir -p "$UNPACK/$e"; tar -xzf "$f" -C "$UNPACK/$e"
done
for f in "$DATA"/traces/*.tar.gz; do
  e="$(basename "$f" .tar.gz)"; mkdir -p "$UNPACK/$e"; tar -xzf "$f" -C "$UNPACK/$e"
done
if [ -f "$DATA/builtin_traces/builtin_attack_traces.tar.gz" ]; then
  mkdir -p "$UNPACK/builtin"; tar -xzf "$DATA/builtin_traces/builtin_attack_traces.tar.gz" -C "$UNPACK/builtin"
fi
echo "      done."

echo "[2/3] recompute_final.py (paper primary) ..."
python3 "$ROOT/pipeline/7_paper_numbers/recompute_final.py"

echo "[3/3] recompute_builtin.py (built-in comparison) ..."
python3 "$ROOT/pipeline/7_paper_numbers/recompute_builtin.py" || echo "   (built-in comparison was not completed; see the preceding error)"

echo
echo "Done. Outputs written under pipeline/7_paper_numbers/outputs/."
