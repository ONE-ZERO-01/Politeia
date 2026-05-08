#!/usr/bin/env python3
"""
Plot political regime phase diagrams from parameter scan results.

Reads scan_summary.csv and produces:
  1. Regime classification map (T vs σ)
  2. Gini heatmap
  3. HHI heatmap
  4. Largest polity heatmap
  5. Mean loyalty heatmap
  6. Regime boundary overlay

Usage:
    python plot_phase_diagram.py scan_results/scan_summary.csv
    python plot_phase_diagram.py scan_results/scan_summary.csv --save phase_diagram.png
"""

import argparse
import sys

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd


REGIME_COLORS = {
    'extinct':           '#808080',
    'atomized':          '#d9d9d9',
    'bands':             '#9ecae1',
    'tribal':            '#6baed6',
    'chiefdoms':         '#3182bd',
    'dominant_chiefdom': '#08519c',
    'state':             '#e6550d',
    'empire':            '#a63603',
    'failed':            '#ff0000',
}

REGIME_ORDER = ['extinct', 'atomized', 'bands', 'tribal',
                'chiefdoms', 'dominant_chiefdom', 'state', 'empire', 'failed']


def pivot_data(df, value_col):
    """Pivot scan data into a 2D grid for heatmap."""
    T_vals = np.sort(df['T'].unique())
    sigma_vals = np.sort(df['sigma'].unique())

    grid = np.full((len(sigma_vals), len(T_vals)), np.nan)
    for _, row in df.iterrows():
        ti = np.searchsorted(T_vals, row['T'])
        si = np.searchsorted(sigma_vals, row['sigma'])
        if ti < len(T_vals) and si < len(sigma_vals):
            grid[si, ti] = row[value_col]

    return T_vals, sigma_vals, grid


def plot_regime_map(df, ax):
    """Categorical regime map."""
    T_vals = np.sort(df['T'].unique())
    sigma_vals = np.sort(df['sigma'].unique())

    regime_to_int = {r: i for i, r in enumerate(REGIME_ORDER)}
    grid = np.full((len(sigma_vals), len(T_vals)), -1.0)

    for _, row in df.iterrows():
        ti = np.searchsorted(T_vals, row['T'])
        si = np.searchsorted(sigma_vals, row['sigma'])
        if ti < len(T_vals) and si < len(sigma_vals):
            regime = row.get('regime', 'failed')
            grid[si, ti] = regime_to_int.get(regime, -1)

    colors = [REGIME_COLORS.get(r, 'gray') for r in REGIME_ORDER]
    cmap = mcolors.ListedColormap(colors)
    bounds = list(range(len(REGIME_ORDER) + 1))
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    dT = (T_vals[-1] - T_vals[0]) / (len(T_vals) - 1) if len(T_vals) > 1 else 1
    ds = (sigma_vals[-1] - sigma_vals[0]) / (len(sigma_vals) - 1) if len(sigma_vals) > 1 else 1
    extent = [T_vals[0] - dT/2, T_vals[-1] + dT/2,
              sigma_vals[0] - ds/2, sigma_vals[-1] + ds/2]

    ax.imshow(grid, origin='lower', aspect='auto', extent=extent,
              cmap=cmap, norm=norm, interpolation='nearest')

    for i, r in enumerate(REGIME_ORDER):
        if r in df['regime'].values:
            ax.scatter([], [], c=REGIME_COLORS[r], s=80,
                       label=r.replace('_', ' ').title(), marker='s')
    ax.legend(fontsize=7, loc='upper right')
    ax.set_xlabel('Temperature T')
    ax.set_ylabel('Social Strength σ')
    ax.set_title('Political Regime Phase Diagram')


def plot_heatmap(df, col, ax, title, cmap='viridis'):
    """Generic heatmap for a numeric column."""
    T_vals, sigma_vals, grid = pivot_data(df, col)

    dT = (T_vals[-1] - T_vals[0]) / (len(T_vals) - 1) if len(T_vals) > 1 else 1
    ds = (sigma_vals[-1] - sigma_vals[0]) / (len(sigma_vals) - 1) if len(sigma_vals) > 1 else 1
    extent = [T_vals[0] - dT/2, T_vals[-1] + dT/2,
              sigma_vals[0] - ds/2, sigma_vals[-1] + ds/2]

    im = ax.imshow(grid, origin='lower', aspect='auto', extent=extent,
                   cmap=cmap, interpolation='bilinear')
    plt.colorbar(im, ax=ax, fraction=0.046)
    ax.set_xlabel('Temperature T')
    ax.set_ylabel('Social Strength σ')
    ax.set_title(title)


def main():
    parser = argparse.ArgumentParser(description='Political regime phase diagram')
    parser.add_argument('summary_csv', help='scan_summary.csv path')
    parser.add_argument('--save', default=None, help='Save figure')
    args = parser.parse_args()

    df = pd.read_csv(args.summary_csv)
    if df.empty:
        print("Error: empty scan summary", file=sys.stderr)
        sys.exit(1)

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    plot_regime_map(df, axes[0, 0])

    numeric_cols = [
        ('Gini', 'Wealth Inequality (Gini)', 'RdYlGn_r'),
        ('HHI', 'Political Concentration (HHI)', 'YlOrRd'),
        ('largest_pop', 'Largest Polity Population', 'YlGnBu'),
        ('mean_loyalty', 'Mean Loyalty ⟨L⟩', 'PuBuGn'),
        ('n_multi', 'Number of Polities (multi)', 'Spectral_r'),
    ]

    for i, (col, title, cmap) in enumerate(numeric_cols):
        if col in df.columns:
            ax = axes.flat[i + 1]
            plot_heatmap(df, col, ax, title, cmap)

    fig.suptitle('Politeia Phase Diagram: (T, σ) Parameter Space',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()

    if args.save:
        fig.savefig(args.save, dpi=150, bbox_inches='tight')
        print(f"Saved to {args.save}")
    else:
        plt.show()


if __name__ == '__main__':
    main()
