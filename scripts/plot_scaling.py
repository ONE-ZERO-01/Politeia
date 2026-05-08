#!/usr/bin/env python3
"""
Plot scaling test results from scaling_test.py output.

Usage:
    python plot_scaling.py scaling_results/ [--save scaling.png]
"""

import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description='Politeia scaling plots')
    parser.add_argument('results_dir', help='Directory with scaling CSVs')
    parser.add_argument('--save', type=str, default=None)
    parser.add_argument('--dpi', type=int, default=150)
    args = parser.parse_args()

    strong_path = os.path.join(args.results_dir, 'strong_scaling.csv')
    weak_path = os.path.join(args.results_dir, 'weak_scaling.csv')

    has_strong = os.path.exists(strong_path)
    has_weak = os.path.exists(weak_path)

    if not has_strong and not has_weak:
        print("No scaling data found", file=sys.stderr)
        sys.exit(1)

    n_plots = int(has_strong) * 2 + int(has_weak)
    fig, axes = plt.subplots(1, n_plots, figsize=(5 * n_plots, 4.5))
    if n_plots == 1:
        axes = [axes]
    ax_idx = 0

    # ─── Strong Scaling ───────────────────────────────────
    if has_strong:
        data = np.genfromtxt(strong_path, delimiter=',', names=True,
                             dtype=None, encoding='utf-8')
        P = data['P'].astype(float)
        speedup = data['speedup'].astype(float)
        eff = data['efficiency_pct'].astype(float)

        ax = axes[ax_idx]
        ax.plot(P, speedup, 'bo-', lw=2, markersize=8, label='Measured')
        ax.plot(P, P, 'k--', alpha=0.5, label='Ideal')
        ax.set_xlabel('MPI Processes $P$')
        ax.set_ylabel('Speedup $S(P)$')
        ax.set_title('Strong Scaling')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax_idx += 1

        ax = axes[ax_idx]
        ax.bar(P, eff, width=0.6, color='steelblue', edgecolor='black')
        ax.axhline(y=100, color='k', ls='--', alpha=0.5)
        ax.set_xlabel('MPI Processes $P$')
        ax.set_ylabel('Parallel Efficiency (%)')
        ax.set_title('Strong Scaling Efficiency')
        ax.set_ylim(0, 120)
        ax.grid(True, alpha=0.3, axis='y')
        ax_idx += 1

    # ─── Weak Scaling ─────────────────────────────────────
    if has_weak:
        data = np.genfromtxt(weak_path, delimiter=',', names=True,
                             dtype=None, encoding='utf-8')
        P = data['P'].astype(float)
        eff = data['efficiency_pct'].astype(float)

        ax = axes[ax_idx]
        ax.bar(P, eff, width=0.6, color='seagreen', edgecolor='black')
        ax.axhline(y=100, color='k', ls='--', alpha=0.5)
        ax.set_xlabel('MPI Processes $P$')
        ax.set_ylabel('Weak Scaling Efficiency (%)')
        ax.set_title(f'Weak Scaling (N/proc={int(data["N_per_proc"][0])})')
        ax.set_ylim(0, 120)
        ax.grid(True, alpha=0.3, axis='y')
        ax_idx += 1

    fig.suptitle('Politeia Parallel Scaling', fontsize=14, fontweight='bold')
    plt.tight_layout()

    if args.save:
        plt.savefig(args.save, dpi=args.dpi, bbox_inches='tight')
        print(f"Saved to {args.save}")
    else:
        plt.show()


if __name__ == '__main__':
    main()
