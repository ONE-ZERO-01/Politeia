#!/usr/bin/env python3
"""
Plot order parameters from order_params.csv (structured CSV output).

More reliable than parsing console logs — directly reads the CSV.

Usage:
    python plot_order_params.py output/order_params.csv [--save evolution.png]
"""

import argparse
import sys

import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(
        description='Politeia order parameter time series from CSV')
    parser.add_argument('csv_file', help='order_params.csv')
    parser.add_argument('--save', type=str, default=None)
    parser.add_argument('--dpi', type=int, default=150)
    args = parser.parse_args()

    data = np.genfromtxt(args.csv_file, delimiter=',', names=True,
                         dtype=None, encoding='utf-8')
    if len(data) == 0:
        print("No data found", file=sys.stderr)
        sys.exit(1)

    steps = data['step']

    panels = [
        ('N',             'Population $N$',                          'tab:blue',    None),
        ('Gini',          'Wealth Gini $G$',                         'tab:red',     (0, 1)),
        ('Q',             r'Culture order $Q$',                      'tab:green',   (0, 1)),
        ('mean_eps',      r'$\langle\varepsilon\rangle$',            'tab:purple',  None),
        ('H',             'Hierarchy depth $H$',                     'black',       None),
        ('C',             'Independent polities $C$',                'tab:gray',    None),
        ('F',             'Largest empire $F$',                      'darkred',     (0, 1)),
        ('Psi',           r'Feudalism $\Psi$',                       'tab:orange',  (0, 1)),
        ('mean_loyalty',  r'Mean loyalty $\langle L\rangle$',        'seagreen',    (0, 1)),
        ('n_attached',    'Attached population',                     'steelblue',   None),
        ('Gini_Power',    'Power Gini',                              'darkmagenta', (0, 1)),
    ]

    # Filter to available columns
    active = [(k, l, c, yl) for k, l, c, yl in panels if k in data.dtype.names]

    n = len(active)
    fig, axes = plt.subplots(n, 1, figsize=(12, 2.5 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, (key, label, color, ylim) in zip(axes, active):
        ax.plot(steps, data[key], '-o', color=color, lw=1.5, markersize=4)
        ax.set_ylabel(label, fontsize=10)
        if ylim:
            ax.set_ylim(ylim)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=9)

    axes[-1].set_xlabel('Simulation step', fontsize=11)
    fig.suptitle('Politeia — Civilization Evolution (from CSV)',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()

    if args.save:
        plt.savefig(args.save, dpi=args.dpi, bbox_inches='tight')
        print(f"Saved to {args.save}")
    else:
        plt.show()


if __name__ == '__main__':
    main()
