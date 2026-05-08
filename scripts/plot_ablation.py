#!/usr/bin/env python3
"""
Visualize ablation experiment results from rule_scan.py.

Produces a multi-panel figure:
  Panel 1: Heatmap of final-state order parameters per experiment
  Panel 2: Bar chart of regime classification
  Panel 3: Time series comparison of key metrics (Gini, H, ε, N)
  Panel 4: Radar chart comparing A0 baseline vs each ablation

Usage:
    python plot_ablation.py ablation_results/ [--save fig.png] [--series A C]
"""

import argparse
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd


REGIME_COLORS = {
    'empire':            '#a63603',
    'state':             '#e6550d',
    'dominant_chiefdom': '#fd8d3c',
    'chiefdoms':         '#fdae6b',
    'tribal':            '#6baed6',
    'bands':             '#9ecae1',
    'atomized':          '#d9d9d9',
    'extinct':           '#252525',
    'failed':            '#f0f0f0',
}

HEATMAP_METRICS = ['Gini', 'Q', 'H', 'F', 'Psi', 'mean_loyalty',
                   'Gini_Power', 'HHI']
HEATMAP_LABELS = ['Gini\n(Inequality)', 'Q\n(Culture\norder)',
                  'H\n(Hierarchy\ndepth)', 'F\n(Largest\nfraction)',
                  'Ψ\n(Feudalism)', 'Loyalty\n(Mean)',
                  'Gini\n(Power)', 'HHI\n(Concen-\ntration)']

TIMESERIES_METRICS = ['Gini', 'H', 'N']


def load_time_series(run_dir):
    """Load order_params.csv as time series."""
    op_file = os.path.join(run_dir, 'order_params.csv')
    if os.path.exists(op_file):
        try:
            return pd.read_csv(op_file)
        except Exception:
            pass
    return pd.DataFrame()


def plot_heatmap(ax, summary, experiments):
    """Plot heatmap of final-state order parameters."""
    n_exp = len(experiments)
    n_met = len(HEATMAP_METRICS)
    data = np.zeros((n_exp, n_met))

    for i, exp in enumerate(experiments):
        row = summary[summary['experiment'] == exp]
        if len(row) == 0:
            continue
        row = row.iloc[0]
        for j, metric in enumerate(HEATMAP_METRICS):
            val = row.get(metric, 0)
            data[i, j] = float(val) if pd.notna(val) else 0.0

    im = ax.imshow(data, aspect='auto', cmap='YlOrRd', vmin=0, vmax=1)

    ax.set_xticks(range(n_met))
    ax.set_xticklabels(HEATMAP_LABELS, fontsize=8, ha='center')
    ax.set_yticks(range(n_exp))

    labels = []
    for exp in experiments:
        row = summary[summary['experiment'] == exp]
        label = row.iloc[0]['label'] if len(row) > 0 else exp
        labels.append(f"{exp}: {label}")
    ax.set_yticklabels(labels, fontsize=8)

    for i in range(n_exp):
        for j in range(n_met):
            val = data[i, j]
            color = 'white' if val > 0.5 else 'black'
            fmt = f'{val:.2f}' if metric != 'H' else f'{val:.0f}'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                    fontsize=7, color=color)

    plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    ax.set_title('Order Parameters by Experiment', fontsize=12,
                 fontweight='bold')


def plot_regime_bars(ax, summary, experiments):
    """Plot regime classification bar chart."""
    regimes = []
    colors = []
    labels = []

    for exp in experiments:
        row = summary[summary['experiment'] == exp]
        if len(row) == 0:
            regimes.append('failed')
        else:
            regimes.append(row.iloc[0].get('regime', 'failed'))
        colors.append(REGIME_COLORS.get(regimes[-1], '#cccccc'))
        labels.append(exp)

    y_pos = np.arange(len(experiments))
    ax.barh(y_pos, [1] * len(experiments), color=colors, edgecolor='gray',
            linewidth=0.5, height=0.7)

    for i, regime in enumerate(regimes):
        ax.text(0.5, i, regime, ha='center', va='center', fontsize=9,
                fontweight='bold',
                color='white' if regime in ('empire', 'state', 'extinct')
                else 'black')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    ax.set_title('Regime Classification', fontsize=12, fontweight='bold')
    ax.invert_yaxis()

    legend_items = []
    seen = set()
    for r in regimes:
        if r not in seen:
            seen.add(r)
            legend_items.append(
                mpatches.Patch(color=REGIME_COLORS.get(r, '#ccc'), label=r))
    ax.legend(handles=legend_items, fontsize=7, loc='lower right',
              ncol=2)


def plot_timeseries(axes, result_dir, summary, experiments):
    """Plot time series comparison for key metrics."""
    colors = plt.cm.tab10(np.linspace(0, 1, len(experiments)))

    for ax, metric in zip(axes, TIMESERIES_METRICS):
        for i, exp in enumerate(experiments):
            run_dir = os.path.join(result_dir, exp)
            ts = load_time_series(run_dir)
            if len(ts) == 0 or metric not in ts.columns:
                continue

            x = ts['step'] if 'step' in ts.columns else range(len(ts))
            ax.plot(x, ts[metric], label=exp, color=colors[i],
                    linewidth=1.2, alpha=0.8)

        ax.set_ylabel(metric, fontsize=10)
        ax.grid(alpha=0.3)
        if ax == axes[-1]:
            ax.set_xlabel('Step', fontsize=10)
        ax.legend(fontsize=6, ncol=3, loc='upper left')

    axes[0].set_title('Time Series Comparison', fontsize=12,
                      fontweight='bold')


def plot_radar(ax, summary, experiments, baseline='A0'):
    """Radar chart comparing baseline vs ablations."""
    metrics = ['Gini', 'Q', 'F', 'Psi', 'mean_loyalty', 'HHI']
    metric_labels = ['Gini', 'Q', 'F', 'Ψ', 'Loyalty', 'HHI']
    n_metrics = len(metrics)

    angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    angles += angles[:1]

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(0)

    ax.set_thetagrids(np.degrees(angles[:-1]), metric_labels, fontsize=8)
    ax.set_ylim(0, 1)

    colors = plt.cm.Set2(np.linspace(0, 1, len(experiments)))

    for i, exp in enumerate(experiments):
        row = summary[summary['experiment'] == exp]
        if len(row) == 0:
            continue
        row = row.iloc[0]

        values = []
        for m in metrics:
            v = row.get(m, 0)
            values.append(float(v) if pd.notna(v) else 0.0)
        values += values[:1]

        linewidth = 2.5 if exp == baseline else 1.2
        linestyle = '-' if exp == baseline else '--'
        ax.plot(angles, values, linewidth=linewidth, linestyle=linestyle,
                label=exp, color=colors[i])
        ax.fill(angles, values, alpha=0.05, color=colors[i])

    ax.legend(fontsize=6, loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax.set_title('Radar: Baseline vs Ablations', fontsize=12,
                 fontweight='bold', pad=20)


def main():
    parser = argparse.ArgumentParser(
        description='Visualize ablation experiment results')
    parser.add_argument('result_dir',
                        help='Directory containing experiment subdirs')
    parser.add_argument('--save', default=None,
                        help='Save figure to file')
    parser.add_argument('--dpi', type=int, default=150)
    parser.add_argument('--series', nargs='+', default=None,
                        help='Filter by series (A, B, C)')
    args = parser.parse_args()

    summary_file = os.path.join(args.result_dir, 'ablation_summary.csv')
    if not os.path.exists(summary_file):
        print(f"Error: {summary_file} not found", file=sys.stderr)
        print("Run rule_scan.py first.", file=sys.stderr)
        sys.exit(1)

    summary = pd.read_csv(summary_file)
    experiments = summary['experiment'].tolist()

    if args.series:
        experiments = [e for e in experiments
                       if any(e.startswith(s) for s in args.series)]

    if not experiments:
        print("No experiments to plot.", file=sys.stderr)
        sys.exit(1)

    n_exp = len(experiments)
    n_ts = len(TIMESERIES_METRICS)

    fig = plt.figure(figsize=(20, 5 + n_exp * 0.5 + n_ts * 2.5))
    gs = GridSpec(2 + n_ts, 2, figure=fig, hspace=0.4, wspace=0.3,
                  height_ratios=[max(3, n_exp * 0.4)] * 2 + [2] * n_ts)

    ax_heat = fig.add_subplot(gs[0, 0])
    plot_heatmap(ax_heat, summary, experiments)

    ax_regime = fig.add_subplot(gs[0, 1])
    plot_regime_bars(ax_regime, summary, experiments)

    ax_radar = fig.add_subplot(gs[1, 0], polar=True)
    baseline = experiments[0]
    plot_radar(ax_radar, summary, experiments, baseline=baseline)

    ax_summary = fig.add_subplot(gs[1, 1])
    ax_summary.axis('off')
    cols = ['experiment', 'N', 'regime', 'H', 'Gini', 'mean_eps']
    avail = [c for c in cols if c in summary.columns]
    sub = summary[summary['experiment'].isin(experiments)][avail]
    table = ax_summary.table(
        cellText=sub.values,
        colLabels=sub.columns,
        loc='center',
        cellLoc='center',
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 1.3)
    ax_summary.set_title('Summary Table', fontsize=12, fontweight='bold')

    ts_axes = []
    for i in range(n_ts):
        ax_ts = fig.add_subplot(gs[2 + i, :])
        ts_axes.append(ax_ts)
    plot_timeseries(ts_axes, args.result_dir, summary, experiments)

    series_str = '+'.join(args.series) if args.series else 'All'
    fig.suptitle(f'Politeia Ablation Study — Series {series_str}',
                 fontsize=16, fontweight='bold', y=0.99)

    if args.save:
        fig.savefig(args.save, dpi=args.dpi, bbox_inches='tight')
        print(f"Saved to {args.save}")
    else:
        plt.show()


if __name__ == '__main__':
    main()
