#!/usr/bin/env python3
"""
Multi-terrain comparison experiment.

Runs the same simulation parameters on different terrain types and collects
polity/order-parameter statistics to compare how geography shapes civilization.

Usage:
    python terrain_compare.py --executable ../build/src/politeia \
                              --base-config ../examples/terrain_compare.cfg \
                              --output-dir compare_results \
                              [--terrains river basins continent gaussian] \
                              [--steps 2000] [--timeout 300]
"""

import argparse
import csv
import os
import subprocess
import sys

import numpy as np
import pandas as pd


TERRAINS = ['river', 'basins', 'continent', 'gaussian']

SUMMARY_COLS = [
    'terrain', 'N', 'Gini', 'Q', 'H', 'C', 'F', 'Psi',
    'mean_loyalty', 'Gini_Power', 'HHI',
    'n_polities', 'n_multi', 'largest_pop',
    'bands', 'tribes', 'chiefdoms', 'states', 'empires',
    'n_transitions', 'regime'
]


def generate_config(base_config_path, overrides, output_path):
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


def run_simulation(executable, config_path, timeout=600):
    cmd = [executable, config_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except FileNotFoundError as e:
        return False, str(e)


def extract_results(run_dir):
    result = {}

    op_file = os.path.join(run_dir, 'order_params.csv')
    if os.path.exists(op_file):
        try:
            df = pd.read_csv(op_file)
            if len(df) > 0:
                last = df.iloc[-1]
                for col in ['N', 'Gini', 'Q', 'H', 'C', 'F', 'Psi',
                            'mean_loyalty', 'Gini_Power']:
                    result[col] = last.get(col, 0)
        except Exception:
            pass

    ps_file = os.path.join(run_dir, 'polity_summary.csv')
    if os.path.exists(ps_file):
        try:
            df = pd.read_csv(ps_file)
            if len(df) > 0:
                last = df.iloc[-1]
                for col in ['n_polities', 'n_multi', 'largest_pop', 'HHI',
                            'bands', 'tribes', 'chiefdoms', 'states', 'empires']:
                    result[col] = last.get(col, 0)
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
    if not result:
        return 'failed'
    N = result.get('N', 0)
    if N == 0:
        return 'extinct'
    empires = result.get('empires', 0)
    states = result.get('states', 0)
    chiefdoms = result.get('chiefdoms', 0)
    tribes = result.get('tribes', 0)
    n_multi = result.get('n_multi', 0)
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


def collect_time_series(run_dir):
    """Collect polity_summary time series for plotting."""
    ps_file = os.path.join(run_dir, 'polity_summary.csv')
    op_file = os.path.join(run_dir, 'order_params.csv')
    ps = pd.read_csv(ps_file) if os.path.exists(ps_file) else pd.DataFrame()
    op = pd.read_csv(op_file) if os.path.exists(op_file) else pd.DataFrame()
    return ps, op


def main():
    parser = argparse.ArgumentParser(
        description='Multi-terrain civilization comparison experiment')
    parser.add_argument('--executable', required=True)
    parser.add_argument('--base-config', required=True)
    parser.add_argument('--output-dir', default='compare_results')
    parser.add_argument('--terrains', nargs='+', default=TERRAINS,
                        help='Terrain types to compare')
    parser.add_argument('--steps', type=int, default=2000)
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--particles', type=int, default=200)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    total = len(args.terrains)
    print(f"Terrain comparison: {total} terrains × 1 parameter set")
    print(f"  Steps: {args.steps}, Particles: {args.particles}")

    # output_interval must satisfy: network_window = interval * 10 <= steps
    out_interval = max(1, args.steps // 100)
    out_interval = min(out_interval, args.steps // 10)
    out_interval = max(out_interval, 1)

    summary_path = os.path.join(args.output_dir, 'terrain_summary.csv')
    with open(summary_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=SUMMARY_COLS)
        writer.writeheader()

        for idx, terrain in enumerate(args.terrains):
            print(f"\n[{idx+1}/{total}] terrain={terrain}")

            run_dir = os.path.join(args.output_dir, terrain)
            os.makedirs(run_dir, exist_ok=True)

            config_path = os.path.join(run_dir, 'run.cfg')

            overrides = {
                'terrain_type': terrain,
                'total_steps': str(args.steps),
                'output_dir': run_dir,
                'output_interval': str(out_interval),
                'initial_particles': str(args.particles),
            }

            if terrain == 'gaussian':
                overrides['terrain_type'] = 'gaussian'

            generate_config(args.base_config, overrides, config_path)

            success, log = run_simulation(
                args.executable, config_path, timeout=args.timeout)

            log_path = os.path.join(run_dir, 'stdout.log')
            with open(log_path, 'w') as f:
                f.write(log)

            result = extract_results(run_dir)
            regime = classify_regime(result)

            row = {'terrain': terrain, 'regime': regime}
            row.update(result)
            writer.writerow(row)
            csvfile.flush()

            print(f"  {'OK' if success else 'FAIL'}: N={result.get('N', '?')} "
                  f"regime={regime} "
                  f"polities={result.get('n_multi', '?')} "
                  f"H={result.get('H', '?')} "
                  f"largest={result.get('largest_pop', '?')} "
                  f"Gini={result.get('Gini', 0):.3f} "
                  f"HHI={result.get('HHI', 0):.3f}")

    print(f"\nResults saved to {summary_path}")

    print("\n=== TERRAIN COMPARISON SUMMARY ===")
    df = pd.read_csv(summary_path)
    cols = ['terrain', 'N', 'regime', 'n_multi', 'largest_pop', 'H', 'Gini', 'HHI']
    avail = [c for c in cols if c in df.columns]
    print(df[avail].to_string(index=False))


if __name__ == '__main__':
    main()
