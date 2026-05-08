#!/usr/bin/env python3
"""
Politeia wealth distribution analysis.
Reads final pos_*.csv snapshot(s) or a specific file and plots P(w).

Usage: python plot_distributions.py <output_dir> [--step 10000] [--save dist.png]
"""

import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt
import numpy as np


def load_snapshot_with_wealth(filepath):
    """Load CSV with x,y columns. Wealth not in pos files — need energy.csv or extended output."""
    data = np.loadtxt(filepath, delimiter=',', skiprows=1)
    return data


def load_energy_timeseries(output_dir):
    """Load energy.csv for time series."""
    filepath = os.path.join(output_dir, 'energy.csv')
    if not os.path.exists(filepath):
        return None
    return np.loadtxt(filepath, delimiter=',', skiprows=1)


def main():
    parser = argparse.ArgumentParser(description='Politeia distribution analysis')
    parser.add_argument('output_dir', help='Output directory')
    parser.add_argument('--save', type=str, default=None, help='Save plot')
    args = parser.parse_args()

    energy = load_energy_timeseries(args.output_dir)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    if energy is not None and len(energy) > 0:
        steps = energy[:, 0]
        time = energy[:, 1]
        ke = energy[:, 2]
        pe_lj = energy[:, 3]
        pe_terrain = energy[:, 4]
        total = energy[:, 5]

        # Energy time series
        axes[0, 0].plot(steps, ke, label='KE', alpha=0.8)
        axes[0, 0].plot(steps, pe_lj, label='PE_LJ', alpha=0.8)
        axes[0, 0].plot(steps, pe_terrain, label='PE_terrain', alpha=0.8)
        axes[0, 0].plot(steps, total, label='Total', alpha=0.8, lw=2)
        axes[0, 0].set_xlabel('Step')
        axes[0, 0].set_ylabel('Energy')
        axes[0, 0].set_title('Energy time series')
        axes[0, 0].legend(fontsize=8)
        axes[0, 0].grid(True, alpha=0.3)

        # KE distribution (should be related to temperature)
        axes[0, 1].hist(ke, bins=30, alpha=0.7, color='steelblue')
        axes[0, 1].set_xlabel('Kinetic Energy')
        axes[0, 1].set_title('KE distribution over time')
        axes[0, 1].grid(True, alpha=0.3)

    # Load final snapshot for spatial distribution
    snapshots = sorted(glob.glob(os.path.join(args.output_dir, 'pos_*.csv')))
    if snapshots:
        final = load_snapshot_with_wealth(snapshots[-1])
        first = load_snapshot_with_wealth(snapshots[0])

        # Initial vs final spatial distribution
        axes[1, 0].scatter(first[:, 0], first[:, 1], s=1, alpha=0.3, label=f'Initial (N={len(first)})')
        axes[1, 0].scatter(final[:, 0], final[:, 1], s=1, alpha=0.5, c='red', label=f'Final (N={len(final)})')
        axes[1, 0].set_xlim(0, 100)
        axes[1, 0].set_ylim(0, 100)
        axes[1, 0].set_aspect('equal')
        axes[1, 0].set_title('Spatial distribution')
        axes[1, 0].legend(fontsize=8)
        axes[1, 0].grid(True, alpha=0.3)

        # Particle count over snapshots
        counts = []
        snap_steps = []
        for s in snapshots:
            d = load_snapshot_with_wealth(s)
            counts.append(len(d))
            step_num = int(os.path.basename(s).replace('pos_', '').replace('.csv', ''))
            snap_steps.append(step_num)

        axes[1, 1].plot(snap_steps, counts, 'b-o', markersize=3)
        axes[1, 1].set_xlabel('Step')
        axes[1, 1].set_ylabel('N particles')
        axes[1, 1].set_title('Population over time')
        axes[1, 1].grid(True, alpha=0.3)

    fig.suptitle('Politeia Analysis Dashboard', fontsize=14)
    plt.tight_layout()

    if args.save:
        plt.savefig(args.save, dpi=150, bbox_inches='tight')
        print(f"Saved to {args.save}")
    else:
        plt.show()


if __name__ == '__main__':
    main()
