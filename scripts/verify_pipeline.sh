#!/usr/bin/env bash
# verify_pipeline.sh — Step-by-step PoC validation for macOS
#
# Run from project root with venv activated:
#   source .venv/bin/activate
#   ./scripts/verify_pipeline.sh

set -euo pipefail

PASS="✓"
FAIL="✗"

echo "=== airband-monitor macOS PoC Verification ==="
echo ""

# --- Stage 1: Hardware ---
echo "--- Stage 1: RTL-SDR Hardware ---"
if command -v rtl_test &>/dev/null; then
  echo "$PASS rtl_test found: $(which rtl_test)"
  echo "Running rtl_test -t (5 seconds)..."
  if rtl_test -t 2>&1 | grep -q "Found"; then
    echo "$PASS RTL-SDR device detected"
  else
    echo "$FAIL No RTL-SDR device found. Check USB connection."
    exit 1
  fi
else
  echo "$FAIL rtl_test not found. Install with: brew install librtlsdr"
  exit 1
fi
echo ""

# --- Stage 2: Python environment ---
echo "--- Stage 2: Python Dependencies ---"
python -c "import yaml; print('$PASS pyyaml')"
python -c "import numpy; print('$PASS numpy', numpy.__version__)"
python -c "import scipy; print('$PASS scipy', scipy.__version__)"

TF_OK=false
if python -c "import tensorflow; print('$PASS tensorflow', tensorflow.__version__)" 2>/dev/null; then
  TF_OK=true
  python -c "import tensorflow_hub; print('$PASS tensorflow-hub', tensorflow_hub.__version__)"
else
  echo "  (tensorflow not available — will use heuristic classifier)"
fi
echo ""

# --- Stage 3: Heuristic classifier smoke test ---
echo "--- Stage 3: Heuristic Classifier ---"
if [ -f "test_audio/music_inject/"*.wav ] 2>/dev/null; then
  MUSIC_FILE=$(ls test_audio/music_inject/*.wav | head -1)
  echo "Testing with: $MUSIC_FILE"
  python - <<'PYEOF'
from pathlib import Path
import glob, sys
files = glob.glob("test_audio/music_inject/*.wav")
if not files:
    print("No music injection WAV found — skipping")
    sys.exit(0)
from src.airband_monitor.classifier import HeuristicAudioClassifier
c = HeuristicAudioClassifier()
prob, labels = c.classify_music_probability(Path(files[0]))
print(f"  music_prob={prob:.3f}  labels={labels}")
if prob > 0.4:
    print("✓ Heuristic classifier returned elevated music score for music file")
else:
    print("  (low score — try with FM broadcast recording)")
PYEOF
else
  echo "  No test audio yet. Run scripts/capture_macos.sh first to generate samples."
fi
echo ""

# --- Stage 4: Watch-mode pipeline (dry run) ---
echo "--- Stage 4: Pipeline Dry Run (3 loops) ---"
if ls test_audio/live/*.wav &>/dev/null 2>&1; then
  python -m airband_monitor.main \
    --config configs/poc_macos.yaml \
    --input-wav-dir test_audio/live \
    --wav-freq 121.5 \
    --watch \
    --max-loops 3 \
    --poll-interval 1 \
    --classifier-backend heuristic
  echo "$PASS Pipeline watch-mode ran successfully"
else
  echo "  No live WAV files yet. Skipping pipeline run."
fi
echo ""

echo "=== Verification complete ==="
echo ""
echo "Next steps:"
echo "  1. brew install librtlsdr sox   (if not done)"
echo "  2. ./scripts/capture_macos.sh 121.5 60 test_audio/live"
echo "  3. ./scripts/capture_macos.sh 89.0 30 test_audio/music_inject"
echo "  4. ./scripts/verify_pipeline.sh"
echo "  5. python -m airband_monitor.main --config configs/poc_macos.yaml \\"
echo "       --input-wav-dir test_audio/live --wav-freq 121.5 \\"
echo "       --watch --classifier-backend auto"
