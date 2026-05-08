#!/usr/bin/env python3
"""
Politeia weak/strong scaling test harness.

Strong scaling: fixed total problem size, increase number of processes.
  → Ideal: T(P) = T(1) / P  →  speedup = T(1) / T(P) = P

Weak scaling: problem size proportional to number of processes.
  → Ideal: T(P) = T(1)  →  efficiency = T(1) / T(P) = 1

Usage:
    python scaling_test.py --executable ../build/src/politeia \
                           --output-dir scaling_results \
                           [--procs 1 2 4] \
                           [--strong-n 4000] \
                           [--weak-n-per-proc 1000] \
                           [--steps 1000] \
                           [--omp-threads 1]

Output:
    scaling_results/strong_scaling.csv
    scaling_results/weak_scaling.csv
"""

import argparse
import csv
import math
import os
import re
import subprocess
import sys
import tempfile


def generate_config(template, overrides, output_path):
    """Generate a config file from a template with overrides."""
    lines = [
        "# Auto-generated scaling test config\n",
        f"domain_xmin = 0.0\n",
        f"domain_xmax = {overrides.get('domain_xmax', 200.0)}\n",
        f"domain_ymin = 0.0\n",
        f"domain_ymax = {overrides.get('domain_ymax', 200.0)}\n",
        f"dt = 0.01\n",
        f"total_steps = {overrides['total_steps']}\n",
        f"output_interval = {overrides['total_steps']}\n",
        f"compact_interval = {max(overrides['total_steps'] // 10, 100)}\n",
        f"initial_particles = {overrides['n_particles']}\n",
        f"temperature = 1.0\n",
        f"friction = 1.0\n",
        f"social_strength = 1.0\n",
        f"social_distance = 1.0\n",
        f"interaction_range = 2.5\n",
        f"initial_wealth = 5.0\n",
        f"survival_threshold = 0.1\n",
        f"consumption_rate = 0.002\n",
        f"output_dir = {overrides.get('output_dir', '/tmp/politeia_scaling')}\n",
    ]

    with open(output_path, 'w') as f:
        f.writelines(lines)


def parse_walltime(log_text):
    """Extract wall time from simulation log."""
    m = re.search(r'Wall time:\s+([\d.]+)\s+s', log_text)
    if m:
        return float(m.group(1))
    return None


def parse_final_n(log_text):
    """Extract final particle count."""
    matches = re.findall(r'N=(\d+)', log_text)
    if matches:
        return int(matches[-1])
    return None


def parse_efficiency(log_text):
    """Extract last load balance efficiency."""
    matches = re.findall(r'eff=([\d.]+)%', log_text)
    if matches:
        return float(matches[-1])
    return None


def run_simulation(executable, config_path, np_procs, omp_threads,
                   mpirun='mpirun', timeout=600):
    """Run Politeia and return stdout."""
    env = os.environ.copy()
    env['OMP_NUM_THREADS'] = str(omp_threads)

    if np_procs > 1:
        cmd = [mpirun, '--oversubscribe', '-np', str(np_procs),
               executable, config_path]
    else:
        cmd = [executable, config_path]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {timeout}s", file=sys.stderr)
        return ""
    except FileNotFoundError as e:
        print(f"  Error: {e}", file=sys.stderr)
        return ""


def main():
    parser = argparse.ArgumentParser(
        description='Politeia weak/strong scaling test')
    parser.add_argument('--executable', required=True,
                        help='Path to politeia executable')
    parser.add_argument('--output-dir', default='scaling_results',
                        help='Output directory')
    parser.add_argument('--procs', nargs='+', type=int, default=[1, 2, 4],
                        help='Number of MPI processes to test')
    parser.add_argument('--strong-n', type=int, default=4000,
                        help='Total particles for strong scaling')
    parser.add_argument('--weak-n-per-proc', type=int, default=1000,
                        help='Particles per process for weak scaling')
    parser.add_argument('--steps', type=int, default=1000,
                        help='Simulation steps per test')
    parser.add_argument('--omp-threads', type=int, default=1,
                        help='OpenMP threads per MPI rank')
    parser.add_argument('--repeats', type=int, default=3,
                        help='Repeats per configuration (take median)')
    parser.add_argument('--mpirun', default='mpirun',
                        help='Path to mpirun')
    parser.add_argument('--timeout', type=int, default=300,
                        help='Timeout per run (seconds)')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 60)
    print("Politeia Scaling Test")
    print("=" * 60)
    print(f"Processes:      {args.procs}")
    print(f"OMP threads:    {args.omp_threads}")
    print(f"Strong N:       {args.strong_n}")
    print(f"Weak N/proc:    {args.weak_n_per_proc}")
    print(f"Steps:          {args.steps}")
    print(f"Repeats:        {args.repeats}")
    print()

    # ─── Strong Scaling ────────────────────────────────────
    print("─── Strong Scaling ───")
    print(f"Fixed N = {args.strong_n}, varying P")

    domain_size = math.sqrt(args.strong_n) * 5.0  # ~5 units per particle

    strong_csv = os.path.join(args.output_dir, 'strong_scaling.csv')
    with open(strong_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['P', 'OMP', 'N', 'steps',
                         'walltime_s', 'speedup', 'efficiency_pct',
                         'load_eff_pct', 'final_N'])

        t1 = None
        for P in args.procs:
            times = []
            last_log = ""

            for rep in range(args.repeats):
                config_path = os.path.join(
                    args.output_dir, f'strong_P{P}_r{rep}.cfg')
                generate_config(None, {
                    'n_particles': args.strong_n,
                    'total_steps': args.steps,
                    'domain_xmax': domain_size,
                    'domain_ymax': domain_size,
                    'output_dir': os.path.join(args.output_dir, f'strong_P{P}_r{rep}'),
                }, config_path)

                log = run_simulation(
                    args.executable, config_path, P, args.omp_threads,
                    mpirun=args.mpirun, timeout=args.timeout)
                last_log = log

                wt = parse_walltime(log)
                if wt is not None:
                    times.append(wt)

            if not times:
                print(f"  P={P}: FAILED (no valid runs)")
                continue

            median_t = sorted(times)[len(times) // 2]

            if t1 is None:
                t1 = median_t

            speedup = t1 / median_t if median_t > 0 else 0
            eff = speedup / P * 100
            load_eff = parse_efficiency(last_log) or 0
            final_n = parse_final_n(last_log) or 0

            writer.writerow([P, args.omp_threads, args.strong_n, args.steps,
                             f'{median_t:.3f}', f'{speedup:.2f}',
                             f'{eff:.1f}', f'{load_eff:.1f}', final_n])
            f.flush()

            print(f"  P={P}: {median_t:.3f}s  speedup={speedup:.2f}x  "
                  f"eff={eff:.1f}%  load_eff={load_eff:.0f}%")

    # ─── Weak Scaling ──────────────────────────────────────
    print(f"\n─── Weak Scaling ───")
    print(f"N/proc = {args.weak_n_per_proc}, varying P")

    weak_csv = os.path.join(args.output_dir, 'weak_scaling.csv')
    with open(weak_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['P', 'OMP', 'N', 'N_per_proc', 'steps',
                         'walltime_s', 'efficiency_pct',
                         'load_eff_pct', 'final_N'])

        t1 = None
        for P in args.procs:
            total_n = args.weak_n_per_proc * P
            domain_size = math.sqrt(total_n) * 5.0
            times = []
            last_log = ""

            for rep in range(args.repeats):
                config_path = os.path.join(
                    args.output_dir, f'weak_P{P}_r{rep}.cfg')
                generate_config(None, {
                    'n_particles': total_n,
                    'total_steps': args.steps,
                    'domain_xmax': domain_size,
                    'domain_ymax': domain_size,
                    'output_dir': os.path.join(args.output_dir, f'weak_P{P}_r{rep}'),
                }, config_path)

                log = run_simulation(
                    args.executable, config_path, P, args.omp_threads,
                    mpirun=args.mpirun, timeout=args.timeout)
                last_log = log

                wt = parse_walltime(log)
                if wt is not None:
                    times.append(wt)

            if not times:
                print(f"  P={P} N={total_n}: FAILED (no valid runs)")
                continue

            median_t = sorted(times)[len(times) // 2]

            if t1 is None:
                t1 = median_t

            eff = t1 / median_t * 100 if median_t > 0 else 0
            load_eff = parse_efficiency(last_log) or 0
            final_n = parse_final_n(last_log) or 0

            writer.writerow([P, args.omp_threads, total_n,
                             args.weak_n_per_proc, args.steps,
                             f'{median_t:.3f}', f'{eff:.1f}',
                             f'{load_eff:.1f}', final_n])
            f.flush()

            print(f"  P={P} N={total_n}: {median_t:.3f}s  "
                  f"weak_eff={eff:.1f}%  load_eff={load_eff:.0f}%")

    print(f"\nResults saved to {strong_csv} and {weak_csv}")


if __name__ == '__main__':
    main()
