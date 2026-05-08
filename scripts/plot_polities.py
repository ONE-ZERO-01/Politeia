#!/usr/bin/env python3
"""Polity analysis visualization.

Reads polity_summary.csv, polity_events.csv, and polities_*.csv
to produce:
  1. Polity type composition over time (stacked area)
  2. HHI (political concentration) over time
  3. Largest polity population over time
  4. Polity event timeline
  5. Spatial polity map from snapshot
"""

import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd


TYPE_COLORS = {
    'band':      '#9ecae1',
    'tribe':     '#6baed6',
    'chiefdom':  '#3182bd',
    'state':     '#e6550d',
    'empire':    '#a63603',
}

EVENT_MARKERS = {
    'formation': ('^', 'green'),
    'merger':    ('D', 'blue'),
    'split':     ('v', 'orange'),
    'collapse':  ('X', 'red'),
}


def plot_composition(summary: pd.DataFrame, ax):
    """Stacked area: polity type counts over time."""
    cols = ['bands', 'tribes', 'chiefdoms', 'states', 'empires']
    labels = ['Band', 'Tribe', 'Chiefdom', 'State', 'Empire']
    colors = [TYPE_COLORS[c.rstrip('s')] for c in cols]

    t = summary['time'].values
    data = np.array([summary[c].values for c in cols])

    ax.stackplot(t, data, labels=labels, colors=colors, alpha=0.8)
    ax.set_xlabel('Time')
    ax.set_ylabel('Count')
    ax.set_title('Polity Type Composition')
    ax.legend(loc='upper left', fontsize=8)


def plot_hhi(summary: pd.DataFrame, ax):
    """HHI concentration over time."""
    ax.plot(summary['time'], summary['HHI'], 'k-', linewidth=1.5)
    ax.axhline(y=1.0, color='r', linestyle='--', alpha=0.3, label='Max (monopoly)')
    ax.set_xlabel('Time')
    ax.set_ylabel('HHI')
    ax.set_title('Political Concentration (HHI)')
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8)


def plot_largest(summary: pd.DataFrame, ax):
    """Largest polity population over time."""
    ax.plot(summary['time'], summary['largest_pop'], 'b-', linewidth=1.5)
    ax.set_xlabel('Time')
    ax.set_ylabel('Population')
    ax.set_title('Largest Polity')


def plot_events(events: pd.DataFrame, ax):
    """Event timeline: scatter plot by type."""
    if events.empty:
        ax.text(0.5, 0.5, 'No events', transform=ax.transAxes,
                ha='center', va='center', fontsize=14, color='gray')
        ax.set_title('Polity Events')
        return

    for etype, (marker, color) in EVENT_MARKERS.items():
        subset = events[events['event'] == etype]
        if not subset.empty:
            sizes = np.clip(subset['pop_after'].values, 5, 200)
            ax.scatter(subset['time'], subset['pop_after'],
                       marker=marker, c=color, s=sizes, alpha=0.7,
                       label=etype.capitalize(), edgecolors='k', linewidths=0.3)

    ax.set_xlabel('Time')
    ax.set_ylabel('Population After')
    ax.set_title('Polity Events')
    ax.legend(fontsize=8)


def plot_spatial(polity_file: str, ax):
    """Spatial polity map: circles sized by population, colored by type."""
    df = pd.read_csv(polity_file)
    if df.empty:
        return

    for _, row in df.iterrows():
        color = TYPE_COLORS.get(row['type'], 'gray')
        size = max(20, row['population'] * 2)
        ax.scatter(row['cx'], row['cy'], s=size, c=color,
                   alpha=0.7, edgecolors='k', linewidths=0.5)
        if row['population'] > 5:
            ax.annotate(f"{row['population']}", (row['cx'], row['cy']),
                        fontsize=6, ha='center', va='center')

    handles = [mpatches.Patch(color=c, label=n.capitalize())
               for n, c in TYPE_COLORS.items()]
    ax.legend(handles=handles, fontsize=7, loc='upper right')
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_title(f'Polity Map ({os.path.basename(polity_file)})')
    ax.set_aspect('equal')


def main():
    parser = argparse.ArgumentParser(description='Polity analysis plots')
    parser.add_argument('output_dir', help='Simulation output directory')
    parser.add_argument('--save', default=None, help='Save figure to file')
    args = parser.parse_args()

    summary_file = os.path.join(args.output_dir, 'polity_summary.csv')
    events_file = os.path.join(args.output_dir, 'polity_events.csv')

    if not os.path.exists(summary_file):
        print(f"Error: {summary_file} not found", file=sys.stderr)
        sys.exit(1)

    summary = pd.read_csv(summary_file)
    events = pd.read_csv(events_file) if os.path.exists(events_file) else pd.DataFrame()

    polity_snaps = sorted(glob.glob(os.path.join(args.output_dir, 'polities_*.csv')))
    last_snap = polity_snaps[-1] if polity_snaps else None

    n_panels = 5 if last_snap else 4
    fig, axes = plt.subplots(1, n_panels, figsize=(5 * n_panels, 4.5))

    plot_composition(summary, axes[0])
    plot_hhi(summary, axes[1])
    plot_largest(summary, axes[2])
    plot_events(events, axes[3])

    if last_snap:
        plot_spatial(last_snap, axes[4])

    fig.suptitle('Polity Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()

    if args.save:
        fig.savefig(args.save, dpi=150, bbox_inches='tight')
        print(f"Saved to {args.save}")
    else:
        plt.show()


if __name__ == '__main__':
    main()
