#!/usr/bin/env python3
"""
Politeia ablation experiment: systematic module on/off scanning.

Runs a matrix of module-switch combinations to identify which mechanisms are
necessary / sufficient for civilization emergence (hierarchy, inequality,
technology jumps, population growth).

Predefined experiment sets:
  A-series: Core module ablation (culture, technology, loyalty, conquest,
            reproduction, carrying_capacity, plague)
  B-series: Enhancement module ablation (lifespan coupling, gender, war cost,
            casualties, pillage, deterrence)
  C-series: Conceptual experiments from docs/why-humans-not-animals.md
            (human vs animal capability ablation)

Usage:
    python rule_scan.py --executable ../build/src/politeia \\
                        --base-config ../examples/scan_base.cfg \\
                        --output-dir ablation_results \\
                        [--series A B C] [--steps 5000] [--timeout 300]
"""

import argparse
import csv
import os
import subprocess
import sys
from collections import OrderedDict

import numpy as np
import pandas as pd


# ─── Experiment definitions ────────────────────────────────────────────

EXPERIMENTS = OrderedDict()

# A-series: core module ablation (one module off at a time)
EXPERIMENTS['A0'] = {
    'label': 'Full model (baseline)',
    'overrides': {},
}
EXPERIMENTS['A1'] = {
    'label': 'No culture',
    'overrides': {'culture_enabled': 'false'},
}
EXPERIMENTS['A2'] = {
    'label': 'No technology',
    'overrides': {'technology_enabled': 'false'},
}
EXPERIMENTS['A3'] = {
    'label': 'No loyalty/hierarchy',
    'overrides': {'loyalty_enabled': 'false'},
}
EXPERIMENTS['A4'] = {
    'label': 'No conquest',
    'overrides': {'conquest_enabled': 'false'},
}
EXPERIMENTS['A5'] = {
    'label': 'No reproduction',
    'overrides': {'reproduction_enabled': 'false'},
}
EXPERIMENTS['A6'] = {
    'label': 'No plague',
    'overrides': {'plague_enabled': 'false'},
}
EXPERIMENTS['A7'] = {
    'label': 'No carrying capacity',
    'overrides': {'carrying_capacity_enabled': 'false'},
}

# B-series: enhancement module ablation (Phase 26 features)
EXPERIMENTS['B1'] = {
    'label': 'No lifespan-wealth coupling',
    'overrides': {'lifespan_wealth_enabled': 'false',
                  'lifespan_tech_enabled': 'false'},
}
EXPERIMENTS['B2'] = {
    'label': 'Gender enabled',
    'overrides': {'gender_enabled': 'true'},
}
EXPERIMENTS['B3'] = {
    'label': 'Gender + war cost',
    'overrides': {'gender_enabled': 'true', 'war_cost_enabled': 'true'},
}
EXPERIMENTS['B4'] = {
    'label': 'Gender + war casualties',
    'overrides': {'gender_enabled': 'true',
                  'war_casualties_enabled': 'true'},
}
EXPERIMENTS['B5'] = {
    'label': 'Gender + pillage',
    'overrides': {'gender_enabled': 'true', 'pillage_enabled': 'true'},
}
EXPERIMENTS['B6'] = {
    'label': 'Gender + deterrence',
    'overrides': {'gender_enabled': 'true', 'deterrence_enabled': 'true'},
}
EXPERIMENTS['B7'] = {
    'label': 'Full enhancement (gender+lifespan+war)',
    'overrides': {'gender_enabled': 'true',
                  'lifespan_wealth_enabled': 'true',
                  'lifespan_tech_enabled': 'true',
                  'war_cost_enabled': 'true',
                  'war_casualties_enabled': 'true',
                  'pillage_enabled': 'true',
                  'deterrence_enabled': 'true'},
}

# C-series: human vs animal conceptual experiments
EXPERIMENTS['C0'] = {
    'label': 'Human (full)',
    'overrides': {},
}
EXPERIMENTS['C1'] = {
    'label': 'Smart social animal (culture only, no ε)',
    'overrides': {'technology_enabled': 'false'},
}
EXPERIMENTS['C2'] = {
    'label': 'Tool animal (ε drift, no culture, no jump)',
    'overrides': {'culture_enabled': 'false',
                  'tech_jump_base_rate': '0.0',
                  'tech_spread_rate': '0.0'},
}
EXPERIMENTS['C3'] = {
    'label': 'Social insect (no culture, no ε)',
    'overrides': {'culture_enabled': 'false',
                  'technology_enabled': 'false'},
}
EXPERIMENTS['C4'] = {
    'label': 'Gradualist civilization (culture+drift, no jump)',
    'overrides': {'tech_jump_base_rate': '0.0'},
}
EXPERIMENTS['C5'] = {
    'label': 'Genius island (ε drift+jump, no culture)',
    'overrides': {'culture_enabled': 'false'},
}
EXPERIMENTS['C6'] = {
    'label': 'Jump without drift (culture+jump, no drift)',
    'overrides': {'tech_drift_rate': '0.0'},
}

SERIES_MAP = {
    'A': [k for k in EXPERIMENTS if k.startswith('A')],
    'B': [k for k in EXPERIMENTS if k.startswith('B')],
    'C': [k for k in EXPERIMENTS if k.startswith('C')],
}


# ─── Utilities (shared pattern with param_scan.py / terrain_compare.py) ──

def generate_config(base_config_path, overrides, output_path):
    """Read base config file, apply overrides, write to output_path."""
    lines = []
    keys_written = set()
    with open(base_config_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key = stripped.split('=')[0].strip()
                if key in overrides:
                    lines.append(f"{key} = {overrides[key]}\n")
                    keys_written.add(key)
                else:
                    lines.append(line)
            else:
                lines.append(line)

    for key, val in overrides.items():
        if key not in keys_written:
            lines.append(f"{key} = {val}\n")

    with open(output_path, 'w') as f:
        f.writelines(lines)


def run_simulation(executable, config_path, np_procs=1, mpirun='mpirun',
                   timeout=600):
    """Run Politeia with given config. Returns (success, stdout+stderr)."""
    if np_procs > 1:
        cmd = [mpirun, '--oversubscribe', '-np', str(np_procs),
               executable, config_path]
    else:
        cmd = [executable, config_path]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except FileNotFoundError as e:
        return False, str(e)


def extract_results(run_dir):
    """Extract final-state stats from CSV output files."""
    result = {}

    op_file = os.path.join(run_dir, 'order_params.csv')
    if os.path.exists(op_file):
        try:
            df = pd.read_csv(op_file)
            if len(df) > 0:
                last = df.iloc[-1]
                for col in ['N', 'Gini', 'Q', 'H', 'C', 'F', 'Psi',
                            'mean_loyalty', 'Gini_Power', 'mean_eps']:
                    if col in last.index:
                        result[col] = float(last[col])
        except Exception:
            pass

    ps_file = os.path.join(run_dir, 'polity_summary.csv')
    if os.path.exists(ps_file):
        try:
            df = pd.read_csv(ps_file)
            if len(df) > 0:
                last = df.iloc[-1]
                for col in ['n_polities', 'n_multi', 'largest_pop', 'HHI',
                            'bands', 'tribes', 'chiefdoms', 'states',
                            'empires']:
                    if col in last.index:
                        result[col] = float(last[col])
        except Exception:
            pass

    pt_file = os.path.join(run_dir, 'phase_transitions.csv')
    if os.path.exists(pt_file):
        try:
            df = pd.read_csv(pt_file)
            result['n_transitions'] = len(df)
        except Exception:
            result['n_transitions'] = 0

    return result


def classify_regime(result):
    """Classify the final political regime."""
    if not result:
        return 'failed'
    N = result.get('N', 0)
    if N == 0:
        return 'extinct'
    empires = int(result.get('empires', 0))
    states = int(result.get('states', 0))
    chiefdoms = int(result.get('chiefdoms', 0))
    tribes = int(result.get('tribes', 0))
    n_multi = int(result.get('n_multi', 0))
    hhi = result.get('HHI', 0)

    if empires > 0:
        return 'empire'
    if states > 0:
        return 'state'
    if chiefdoms > 0:
        return 'dominant_chiefdom' if hhi > 0.3 else 'chiefdoms'
    if tribes > 0:
        return 'tribal'
    if n_multi == 0:
        return 'atomized'
    return 'bands'


# ─── Main ───────────────────────────────────────────────────────────────

SUMMARY_COLS = [
    'experiment', 'label',
    'N', 'Gini', 'Q', 'H', 'C', 'F', 'Psi',
    'mean_loyalty', 'Gini_Power', 'mean_eps', 'HHI',
    'n_polities', 'n_multi', 'largest_pop',
    'bands', 'tribes', 'chiefdoms', 'states', 'empires',
    'n_transitions', 'regime'
]


def main():
    parser = argparse.ArgumentParser(
        description='Politeia ablation experiment scanner')
    parser.add_argument('--executable', required=True,
                        help='Path to politeia binary')
    parser.add_argument('--base-config', required=True,
                        help='Base .cfg file (template)')
    parser.add_argument('--output-dir', default='ablation_results',
                        help='Root output directory')
    parser.add_argument('--series', nargs='+', default=['A', 'B', 'C'],
                        choices=['A', 'B', 'C'],
                        help='Experiment series to run')
    parser.add_argument('--experiments', nargs='+', default=None,
                        help='Run specific experiments (e.g. A0 A1 C3)')
    parser.add_argument('--np', type=int, default=1,
                        help='MPI ranks')
    parser.add_argument('--mpirun', default='mpirun')
    parser.add_argument('--steps', type=int, default=5000,
                        help='Simulation steps per experiment')
    parser.add_argument('--particles', type=int, default=200,
                        help='Initial particle count')
    parser.add_argument('--timeout', type=int, default=600,
                        help='Per-run timeout in seconds')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print commands without running')
    args = parser.parse_args()

    if args.experiments:
        exp_keys = args.experiments
        for k in exp_keys:
            if k not in EXPERIMENTS:
                print(f"Unknown experiment: {k}", file=sys.stderr)
                sys.exit(1)
    else:
        exp_keys = []
        for s in args.series:
            exp_keys.extend(SERIES_MAP[s])

    os.makedirs(args.output_dir, exist_ok=True)
    total = len(exp_keys)

    out_interval = max(1, args.steps // 100)
    out_interval = min(out_interval, args.steps // 10)
    out_interval = max(out_interval, 1)

    print(f"Ablation scan: {total} experiments")
    print(f"  Series: {args.series}")
    print(f"  Steps: {args.steps}, Particles: {args.particles}")
    print()

    summary_path = os.path.join(args.output_dir, 'ablation_summary.csv')
    with open(summary_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=SUMMARY_COLS)
        writer.writeheader()

        for idx, exp_key in enumerate(exp_keys):
            exp = EXPERIMENTS[exp_key]
            label = exp['label']
            print(f"[{idx+1}/{total}] {exp_key}: {label}")

            run_dir = os.path.join(args.output_dir, exp_key)
            os.makedirs(run_dir, exist_ok=True)

            config_path = os.path.join(run_dir, 'run.cfg')
            overrides = {
                'total_steps': str(args.steps),
                'output_dir': run_dir,
                'output_interval': str(out_interval),
                'initial_particles': str(args.particles),
            }
            overrides.update(exp['overrides'])

            generate_config(args.base_config, overrides, config_path)

            if args.dry_run:
                n_overrides = len(exp['overrides'])
                print(f"  Would run with {n_overrides} overrides: "
                      f"{list(exp['overrides'].keys())}")
                continue

            success, log = run_simulation(
                args.executable, config_path,
                np_procs=args.np, mpirun=args.mpirun,
                timeout=args.timeout)

            log_path = os.path.join(run_dir, 'stdout.log')
            with open(log_path, 'w') as f:
                f.write(log)

            result = extract_results(run_dir)
            regime = classify_regime(result)

            row = {'experiment': exp_key, 'label': label, 'regime': regime}
            row.update(result)
            writer.writerow(row)
            csvfile.flush()

            status = 'OK' if success else 'FAIL'
            N = result.get('N', '?')
            H = result.get('H', '?')
            eps = result.get('mean_eps', '?')
            gini = result.get('Gini', 0)
            print(f"  {status}: N={N} H={H} ε={eps} "
                  f"Gini={gini:.3f} regime={regime}")

    print(f"\nResults saved to {summary_path}")

    if not args.dry_run:
        print("\n=== ABLATION SUMMARY ===")
        df = pd.read_csv(summary_path)
        cols = ['experiment', 'label', 'N', 'regime', 'H', 'Gini',
                'mean_eps', 'HHI', 'n_multi']
        avail = [c for c in cols if c in df.columns]
        print(df[avail].to_string(index=False))


if __name__ == '__main__':
    main()
