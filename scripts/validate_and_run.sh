#!/usr/bin/env bash
# Politeia — One-shot build, test, simulate & analyze
# Usage: bash scripts/validate_and_run.sh
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)
NPROC=$(nproc)

banner() { echo ""; echo "══════════════════════════════════════════"; echo "  $1"; echo "══════════════════════════════════════════"; }

banner "Politeia — Full Pipeline"
echo "  Root:    $ROOT"
echo "  Date:    $(date)"
echo "  Threads: $NPROC"

# ── 1. Clean Rebuild ─────────────────────────────────────────────────
banner "1/6  Clean Rebuild (Release + OpenMP)"
rm -rf build
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DPOLITEIA_USE_OPENMP=ON -DPOLITEIA_BUILD_TESTS=ON 2>&1
make -j$NPROC 2>&1
echo ""
echo "Binary:"
ls -lh src/politeia

# ── 2. Social Force Tests ────────────────────────────────────────────
banner "2/6  Social Force Tests"
ctest -R SocialForce --output-on-failure 2>&1

# ── 3. Key Tests ─────────────────────────────────────────────────────
banner "3/6  All Tests (excluding slow integrator)"
ctest --output-on-failure -j$NPROC -E "LangevinHas" 2>&1

# ── 4. Quick Simulation ─────────────────────────────────────────────
banner "4/6  Quick 10K Simulation (200 steps)"
cd "$ROOT"
OUTDIR=/tmp/politeia_run_$$
mkdir -p "$OUTDIR"

cat > /tmp/politeia_cfg_$$.cfg << 'CFGEOF'
initial_conditions_file = examples/genesis_hyde_100k.csv
initial_particles = 10000
domain_xmin = -180.0
domain_xmax = 180.0
domain_ymin = -85.0
domain_ymax = 85.0
dt = 0.01
total_steps = 200
output_interval = 200
compact_interval = 50
temperature = 0.3
friction = 1.0
social_strength = 3.0
social_distance = 1.0
interaction_range = 3.0
initial_wealth = 8.0
survival_threshold = 0.3
consumption_rate = 0.01
base_production = 0.3
gender_enabled = false
terrain_type = continent
terrain_scale = 0.5
network_window_factor = 1
checkpoint_interval = 0
random_seed = 42
density_update_interval = 50
CFGEOF
# inject output_dir (can't use variable in heredoc with 'CFGEOF')
echo "output_dir = $OUTDIR" >> /tmp/politeia_cfg_$$.cfg

echo "Config: /tmp/politeia_cfg_$$.cfg"
echo "Output: $OUTDIR"
echo ""
OMP_NUM_THREADS=$NPROC stdbuf -oL ./build/src/politeia /tmp/politeia_cfg_$$.cfg 2>&1
echo ""

# ── 5. Energy Diagnostics ───────────────────────────────────────────
banner "5/6  Energy Diagnostics"
if [ -f "$OUTDIR/energy.csv" ]; then
    echo "energy.csv contents:"
    cat "$OUTDIR/energy.csv"
    echo ""
    echo "Checking for energy explosion..."
    MAX_SOCIAL=$(awk -F, 'NR>1{v=$4; if(v<0)v=-v; if(v>m)m=v} END{print m+0}' "$OUTDIR/energy.csv")
    echo "  Max |social PE| = $MAX_SOCIAL"
    if python3 -c "import sys; sys.exit(0 if float('$MAX_SOCIAL') < 1e10 else 1)" 2>/dev/null; then
        echo "  ✓ Social PE is healthy"
    else
        echo "  ⚠ Social PE may be elevated"
    fi
else
    echo "  (no energy.csv produced)"
fi
echo ""
echo "Output files:"
ls -lh "$OUTDIR"/ 2>/dev/null || echo "  (empty)"

# ── 6. Analysis ──────────────────────────────────────────────────────
banner "6/6  Analysis & Visualization"
pip3 install matplotlib --user --break-system-packages -q 2>&1 | tail -1
python3 scripts/analyze_run.py "$OUTDIR" --save-dir "$OUTDIR" 2>&1

banner "Done!"
echo "  All output in: $OUTDIR"
echo "  To cleanup:    rm -rf $OUTDIR /tmp/politeia_cfg_$$.cfg"
echo ""
