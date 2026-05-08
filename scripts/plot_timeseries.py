#!/usr/bin/env python3
"""
Politeia order parameter time series plots.
Reads the console output (piped to a log file) to extract all order parameters
including hierarchy, loyalty, and power metrics.

Usage:
    python plot_timeseries.py <logfile> [--save output.png]
    ./politeia config.cfg 2>&1 | tee run.log
    python plot_timeseries.py run.log --save evolution.png
"""

import argparse
import re
import sys

import matplotlib.pyplot as plt
import numpy as np


def parse_log(filepath):
    """Parse Politeia console output for order parameters."""
    records = []
    pattern = re.compile(
        r'Step\s+(\d+)/\d+'
        r'\s+N=(\d+)'
        r'\s+Gini=([\d.eE+\-]+)'
        r'(?:\s+Q=([\d.eE+\-]+))?'
        r'(?:\s+<eps>=([\d.eE+\-]+))?'
        r'(?:\s+H=(\d+))?'
        r'(?:\s+C=(\d+))?'
        r'(?:\s+F=([\d.eE+\-]+))?'
        r'(?:\s+Psi=([\d.eE+\-]+))?'
        r'(?:\s+<L>=([\d.eE+\-]+))?'
        r'(?:\s+n_attached=(\d+))?'
        r'(?:\s+Gini\(Power\)=([\d.eE+\-]+))?'
    )

    with open(filepath) as f:
        for line in f:
            m = pattern.search(line)
            if m:
                records.append({
                    'step':     int(m.group(1)),
                    'N':        int(m.group(2)),
                    'Gini':     float(m.group(3)),
                    'Q':        float(m.group(4)) if m.group(4) else None,
                    'eps':      float(m.group(5)) if m.group(5) else None,
                    'H':        int(m.group(6)) if m.group(6) else None,
                    'C':        int(m.group(7)) if m.group(7) else None,
                    'F':        float(m.group(8)) if m.group(8) else None,
                    'Psi':      float(m.group(9)) if m.group(9) else None,
                    'L':        float(m.group(10)) if m.group(10) else None,
                    'n_att':    int(m.group(11)) if m.group(11) else None,
                    'Gini_P':   float(m.group(12)) if m.group(12) else None,
                })

    return records


def get(records, key, default=0):
    return [r.get(key, default) or default for r in records]


def has_data(records, key):
    return any(r.get(key) is not None for r in records)


def main():
    parser = argparse.ArgumentParser(description='Politeia time series plots')
    parser.add_argument('logfile', help='Console output log file')
    parser.add_argument('--save', type=str, default=None, help='Save plot to file')
    args = parser.parse_args()

    records = parse_log(args.logfile)
    if not records:
        print(f"No data found in {args.logfile}")
        sys.exit(1)

    steps = [r['step'] for r in records]

    # ── Determine layout ──────────────────────────────────
    panels = []

    panels.append(('N',       'Population N',                 'b', None))
    panels.append(('Gini',    'Wealth Gini',                  'r', (0, 1)))

    if has_data(records, 'Q'):
        panels.append(('Q',   r'Culture order $Q$',           'g', (0, 1)))
    if has_data(records, 'eps'):
        panels.append(('eps', r'$\langle\varepsilon\rangle$', 'm', None))

    # Hierarchy block
    if has_data(records, 'H'):
        panels.append(('H',   'Hierarchy depth $H$',          'k', None))
    if has_data(records, 'C'):
        panels.append(('C',   'Independent polities $C$',     '#555555', None))
    if has_data(records, 'F'):
        panels.append(('F',   'Largest empire $F$',           '#8B0000', (0, 1)))
    if has_data(records, 'Psi'):
        panels.append(('Psi', r'Feudalism $\Psi$',            '#D2691E', (0, 1)))

    # Loyalty block
    if has_data(records, 'L'):
        panels.append(('L',     r'Mean loyalty $\langle L\rangle$', '#2E8B57', (0, 1)))
    if has_data(records, 'n_att'):
        panels.append(('n_att', 'Attached population',              '#4682B4', None))
    if has_data(records, 'Gini_P'):
        panels.append(('Gini_P', 'Power Gini',                      '#8B008B', (0, 1)))

    n_plots = len(panels)
    fig, axes = plt.subplots(n_plots, 1, figsize=(12, 2.5 * n_plots), sharex=True)
    if n_plots == 1:
        axes = [axes]

    for ax, (key, label, color, ylim) in zip(axes, panels):
        data = get(records, key)
        ax.plot(steps, data, '-', color=color, lw=1.5, markersize=3)
        ax.set_ylabel(label, fontsize=10)
        if ylim:
            ax.set_ylim(ylim)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=9)

    axes[-1].set_xlabel('Simulation step', fontsize=11)
    fig.suptitle('Politeia — Civilization Evolution', fontsize=14, fontweight='bold')
    plt.tight_layout()

    if args.save:
        plt.savefig(args.save, dpi=150, bbox_inches='tight')
        print(f"Saved to {args.save}")
    else:
        plt.show()


if __name__ == '__main__':
    main()
