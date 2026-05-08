#!/usr/bin/env python3
"""
Politeia parameter space scanning with polity analysis.

Scans a 2D grid of (Temperature, social_strength) values, runs simulations,
and collects final-state order parameters + polity statistics for phase diagram
construction.

Reads results from CSV files (more reliable than log parsing).

Usage:
    python param_scan.py --executable ../build/src/politeia \
                         --base-config ../examples/scan_base.cfg \
                         --output-dir scan_results \
                         [--T-range 0.1 5.0 8] \
                         [--sigma-range 0.1 3.0 8] \
                         [--np 1] [--steps 5000]
"""

import argparse
import csv
import itertools
import os
import subprocess
import sys

import numpy as np
import pandas as pd


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
    """Run Politeia with given config. Returns (success, stdout)."""
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

    # Order parameters (last row)
    op_file = os.path.join(run_dir, 'order_params.csv')
    if os.path.exists(op_file):
        try:
            df = pd.read_csv(op_file)
            if len(df) > 0:
                last = df.iloc[-1]
                result['N'] = int(last.get('N', 0))
                result['Gini'] = float(last.get('Gini', 0))
                result['Q'] = float(last.get('Q', 0))
                result['H'] = int(last.get('H', 0))
                result['C'] = int(last.get('C', 0))
                result['F'] = float(last.get('F', 0))
                result['Psi'] = float(last.get('Psi', 0))
                result['mean_loyalty'] = float(last.get('mean_loyalty', 0))
                result['Gini_Power'] = float(last.get('Gini_Power', 0))
        except Exception:
            pass

    # Polity summary (last row)
    ps_file = os.path.join(run_dir, 'polity_summary.csv')
    if os.path.exists(ps_file):
        try:
            df = pd.read_csv(ps_file)
            if len(df) > 0:
                last = df.iloc[-1]
                result['n_polities'] = int(last.get('n_polities', 0))
                result['n_multi'] = int(last.get('n_multi', 0))
                result['largest_pop'] = int(last.get('largest_pop', 0))
                result['HHI'] = float(last.get('HHI', 0))
                result['bands'] = int(last.get('bands', 0))
                result['tribes'] = int(last.get('tribes', 0))
                result['chiefdoms'] = int(last.get('chiefdoms', 0))
                result['states'] = int(last.get('states', 0))
                result['empires'] = int(last.get('empires', 0))
        except Exception:
            pass

    # Phase transitions (count)
    pt_file = os.path.join(run_dir, 'phase_transitions.csv')
    if os.path.exists(pt_file):
        try:
            df = pd.read_csv(pt_file)
            result['n_transitions'] = len(df)
        except Exception:
            result['n_transitions'] = 0

    return result


def classify_regime(result):
    """Classify the final political regime from polity statistics."""
    if not result:
        return 'failed'

    empires = result.get('empires', 0)
    states = result.get('states', 0)
    chiefdoms = result.get('chiefdoms', 0)
    tribes = result.get('tribes', 0)
    n_multi = result.get('n_multi', 0)
    hhi = result.get('HHI', 0)
    N = result.get('N', 0)

    if N == 0:
        return 'extinct'
    if empires > 0:
        return 'empire'
    if states > 0:
        return 'state'
    if chiefdoms > 0:
        if hhi > 0.3:
            return 'dominant_chiefdom'
        return 'chiefdoms'
    if tribes > 0:
        return 'tribal'
    if n_multi == 0:
        return 'atomized'
    return 'bands'


SCAN_COLUMNS = [
    'T', 'sigma', 'N', 'Gini', 'Q', 'H', 'C', 'F', 'Psi',
    'mean_loyalty', 'Gini_Power', 'HHI',
    'n_polities', 'n_multi', 'largest_pop',
    'bands', 'tribes', 'chiefdoms', 'states', 'empires',
    'n_transitions', 'regime'
]


def main():
    parser = argparse.ArgumentParser(
        description='Politeia (T, σ) parameter scan with polity analysis')
    parser.add_argument('--executable', required=True)
    parser.add_argument('--base-config', required=True)
    parser.add_argument('--output-dir', default='scan_results')
    parser.add_argument('--T-range', nargs=3, type=float,
                        default=[0.1, 3.0, 6],
                        help='Temperature: min max num_points')
    parser.add_argument('--sigma-range', nargs=3, type=float,
                        default=[0.1, 3.0, 6],
                        help='social_strength: min max num_points')
    parser.add_argument('--np', type=int, default=1)
    parser.add_argument('--steps', type=int, default=5000)
    parser.add_argument('--mpirun', default='mpirun')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    T_values = np.linspace(args.T_range[0], args.T_range[1],
                           int(args.T_range[2]))
    sigma_values = np.linspace(args.sigma_range[0], args.sigma_range[1],
                               int(args.sigma_range[2]))

    total = len(T_values) * len(sigma_values)
    print(f"Parameter scan: {len(T_values)} T × {len(sigma_values)} σ "
          f"= {total} runs")

    summary_path = os.path.join(args.output_dir, 'scan_summary.csv')
    with open(summary_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=SCAN_COLUMNS)
        writer.writeheader()

        for idx, (T, sigma) in enumerate(
                itertools.product(T_values, sigma_values)):
            print(f"\n[{idx+1}/{total}] T={T:.3f} σ={sigma:.3f}")

            run_dir = os.path.join(
                args.output_dir, f"T{T:.3f}_s{sigma:.3f}")
            os.makedirs(run_dir, exist_ok=True)

            config_path = os.path.join(run_dir, 'run.cfg')
            # network_window = output_interval × 10, and we need at least
            # one full analysis window within total_steps
            out_interval = max(1, args.steps // 100)
            # ensure network_window = out_interval * 10 <= total_steps
            out_interval = min(out_interval, args.steps // 10)
            out_interval = max(out_interval, 1)
            generate_config(args.base_config, {
                'temperature': str(T),
                'social_strength': str(sigma),
                'total_steps': str(args.steps),
                'output_dir': run_dir,
                'output_interval': str(out_interval),
            }, config_path)

            if args.dry_run:
                print(f"  Would run: {args.executable} {config_path}")
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

            row = {'T': T, 'sigma': sigma, 'regime': regime}
            row.update(result)
            writer.writerow(row)
            csvfile.flush()

            print(f"  {'OK' if success else 'FAIL'}: N={result.get('N', '?')} "
                  f"regime={regime} "
                  f"polities={result.get('n_multi', '?')} "
                  f"largest={result.get('largest_pop', '?')} "
                  f"HHI={result.get('HHI', 0):.3f}")

    print(f"\nResults saved to {summary_path}")


if __name__ == '__main__':
    main()
