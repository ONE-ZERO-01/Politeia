#!/usr/bin/env python3
"""
Visualize multi-terrain comparison results.

Produces a multi-panel figure:
  Row 1: Terrain elevation maps (one per terrain type)
  Row 2: Final polity spatial maps overlaid on terrain
  Row 3: Order parameter comparison bar chart
  Row 4: Time series comparison (population, HHI, Gini, largest polity)

Usage:
    python plot_terrain_compare.py compare_results/ [--save fig.png]
"""

import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import Normalize
from matplotlib import cm
import numpy as np
import pandas as pd


TYPE_COLORS = {
    'band':      '#9ecae1',
    'tribe':     '#6baed6',
    'chiefdom':  '#3182bd',
    'state':     '#e6550d',
    'empire':    '#a63603',
}

TERRAIN_LABELS = {
    'river':     'River Valley\n(Nile/Yellow River)',
    'basins':    'Multiple Basins\n(Mesopotamia)',
    'continent': 'Continental\n(Generic)',
    'gaussian':  'Single Center\n(Oasis)',
    'china':     'China\n(Great Plain + Rivers)',
    'europe':    'Europe\n(Mountain Barriers)',
}


def generate_terrain(terrain_type, nx=128, ny=128,
                     xmin=0, ymin=0, xmax=50, ymax=50):
    """Generate terrain elevation matching C++ synthetic generator."""
    h = np.zeros((ny, nx))
    for r in range(ny):
        for c in range(nx):
            x = xmin + c * (xmax - xmin) / (nx - 1)
            y = ymin + r * (ymax - ymin) / (ny - 1)
            nx_ = (x - xmin) / (xmax - xmin)
            ny_ = (y - ymin) / (ymax - ymin)

            if terrain_type == 'river':
                river_y = 0.5 + 0.15 * np.sin(nx_ * np.pi * 3.0)
                dr = abs(ny_ - river_y)
                rv = np.exp(-dr**2 * 80.0)
                fp = np.exp(-dr**2 * 15.0)
                ey = min(ny_, 1.0 - ny_)
                mt = np.exp(-ey**2 * 20.0) * 80.0
                h[r, c] = max(0.0, mt + 30.0 * (1.0 - fp) - 5.0 * rv)

            elif terrain_type == 'basins':
                basins = [(0.25, 0.35, 0.12, 0.10),
                          (0.55, 0.55, 0.15, 0.12),
                          (0.25, 0.70, 0.10, 0.08),
                          (0.75, 0.35, 0.12, 0.10)]
                base = 60.0
                for bcx, bcy, bsx, bsy in basins:
                    bx = (nx_ - bcx) / bsx
                    by = (ny_ - bcy) / bsy
                    base -= 55.0 * np.exp(-(bx**2 + by**2))
                ex = min(nx_, 1.0 - nx_)
                ey = min(ny_, 1.0 - ny_)
                edge = min(ex, ey)
                base += 40.0 * np.exp(-edge**2 * 30.0)
                h[r, c] = max(0.0, base)

            elif terrain_type == 'continent':
                ex = min(nx_, 1.0 - nx_)
                ey = min(ny_, 1.0 - ny_)
                coast = min(ex, ey)
                ocean = 200.0 * np.exp(-coast**2 * 50.0)
                mt_d = abs(ny_ - (1.2 - nx_))
                mt = 60.0 * np.exp(-mt_d**2 * 100.0)
                p1 = 30.0 * np.exp(-((nx_-0.35)**2 + (ny_-0.4)**2) * 8.0)
                p2 = 30.0 * np.exp(-((nx_-0.65)**2 + (ny_-0.6)**2) * 8.0)
                h[r, c] = max(0.0, ocean + mt + 20.0 - p1 - p2)

            elif terrain_type == 'gaussian':
                cx, cy = 0.5, 0.5
                r2 = (nx_ - cx)**2 + (ny_ - cy)**2
                h[r, c] = max(0.0, 50.0 * (1.0 - np.exp(-r2 * 5.0)))

            elif terrain_type == 'china':
                west = 100.0 * np.exp(-nx_**2 * 40.0)
                north = 50.0 * np.exp(-(1.0 - ny_)**2 * 30.0)
                sr_d = abs(ny_ - 0.25)
                south = 25.0 * np.exp(-sr_d**2 * 80.0)
                pdx, pdy = nx_ - 0.55, ny_ - 0.55
                plain = 70.0 * np.exp(-(pdx**2 * 3 + pdy**2 * 4))
                yr_y = 0.65 + 0.08 * np.sin(nx_ * np.pi * 2)
                yr = 15.0 * np.exp(-(ny_ - yr_y)**2 * 200)
                yz_y = 0.45 + 0.06 * np.sin(nx_ * np.pi * 2.5 + 1)
                yz = 15.0 * np.exp(-(ny_ - yz_y)**2 * 200)
                ex = min(nx_, 1 - nx_); ey2 = min(ny_, 1 - ny_)
                edge = min(ex, ey2)
                emt = 30.0 * np.exp(-edge**2 * 40)
                h[r, c] = max(0.0, west + north + south + emt + 40 - plain - yr - yz)

            elif terrain_type == 'europe':
                alps_y = 0.55 + 0.08 * np.sin(nx_ * np.pi * 2)
                alps = 90.0 * np.exp(-(ny_ - alps_y)**2 * 120)
                pyr = 70.0 * np.exp(-((nx_-0.25)**2*60 + (ny_-0.3)**2*120))
                cr = np.sqrt((nx_-0.75)**2 + (ny_-0.6)**2)
                ca = np.arctan2(ny_-0.6, nx_-0.75)
                carp = 60.0 * np.exp(-(cr-0.18)**2 * 300)
                if ca < -0.5 or ca > 2.5: carp = 0
                scand = 50.0 * np.exp(-(ny_-0.85)**2*100) * np.exp(-(nx_-0.4)**2*8)
                basins = [(0.25,0.5,0.1,0.08,60),(0.5,0.45,0.06,0.05,50),
                          (0.7,0.55,0.08,0.07,55),(0.2,0.2,0.08,0.07,45),
                          (0.45,0.7,0.1,0.08,55),(0.8,0.4,0.07,0.06,40)]
                bs = sum(d*np.exp(-((nx_-bcx)/bsx)**2-((ny_-bcy)/bsy)**2)
                         for bcx,bcy,bsx,bsy,d in basins)
                ex = min(nx_, 1-nx_); ey2 = min(ny_, 1-ny_)
                ocean = 60.0 * np.exp(-min(ex,ey2)**2 * 40)
                h[r, c] = max(0.0, ocean + alps + pyr + carp + scand + 40 - bs)
    return h


def load_last_snapshot(run_dir):
    snaps = sorted(glob.glob(os.path.join(run_dir, 'snap_*.csv')))
    if not snaps:
        return None
    return pd.read_csv(snaps[-1])


def load_last_polities(run_dir):
    pols = sorted(glob.glob(os.path.join(run_dir, 'polities_*.csv')))
    if not pols:
        return None
    return pd.read_csv(pols[-1])


def main():
    parser = argparse.ArgumentParser(
        description='Multi-terrain comparison visualization')
    parser.add_argument('result_dir', help='Directory containing terrain subdirs')
    parser.add_argument('--save', default=None)
    parser.add_argument('--dpi', type=int, default=150)
    parser.add_argument('--domain', nargs=4, type=float,
                        default=[0, 50, 0, 50],
                        help='xmin xmax ymin ymax')
    args = parser.parse_args()

    xmin, xmax, ymin, ymax = args.domain

    summary_file = os.path.join(args.result_dir, 'terrain_summary.csv')
    if not os.path.exists(summary_file):
        print(f"Error: {summary_file} not found", file=sys.stderr)
        sys.exit(1)

    summary = pd.read_csv(summary_file)
    terrains = summary['terrain'].tolist()
    n_terrains = len(terrains)

    fig = plt.figure(figsize=(5 * n_terrains, 18))

    # Row 1: Terrain elevation
    for i, terrain in enumerate(terrains):
        ax = fig.add_subplot(4, n_terrains, i + 1)
        h = generate_terrain(terrain, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)
        im = ax.imshow(h, origin='lower', cmap='terrain',
                       extent=[xmin, xmax, ymin, ymax], aspect='equal')
        label = TERRAIN_LABELS.get(terrain, terrain)
        ax.set_title(label, fontsize=11, fontweight='bold')
        if i == 0:
            ax.set_ylabel('Elevation', fontsize=10)
        plt.colorbar(im, ax=ax, shrink=0.7, pad=0.02)

    # Row 2: Population on terrain + polity boundaries
    for i, terrain in enumerate(terrains):
        ax = fig.add_subplot(4, n_terrains, n_terrains + i + 1)
        h = generate_terrain(terrain, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)

        scale = 0.5
        h_max = h.max()
        V = -scale * (h_max - h)
        prod = np.maximum(0, -V)
        ax.imshow(prod, origin='lower', cmap='YlGn', alpha=0.6,
                  extent=[xmin, xmax, ymin, ymax], aspect='equal')

        run_dir = os.path.join(args.result_dir, terrain)
        snap = load_last_snapshot(run_dir)
        polities = load_last_polities(run_dir)

        if snap is not None and len(snap) > 0:
            ax.scatter(snap['x'], snap['y'], c='navy', s=3, alpha=0.5, zorder=3)

        if polities is not None and len(polities) > 0:
            for _, row in polities.iterrows():
                color = TYPE_COLORS.get(row.get('type', ''), 'gray')
                pop = row.get('population', 1)
                size = max(30, pop * 3)
                ax.scatter(row['cx'], row['cy'], s=size, c=color,
                           alpha=0.8, edgecolors='k', linewidths=1, zorder=5)
                if pop > 3:
                    ax.annotate(str(int(pop)),
                                (row['cx'], row['cy']),
                                fontsize=7, ha='center', va='center',
                                fontweight='bold', color='white', zorder=6)

        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        if i == 0:
            ax.set_ylabel('Population + Polities', fontsize=10)

        row_data = summary[summary['terrain'] == terrain].iloc[0]
        regime = row_data.get('regime', '?')
        ax.set_title(f"N={int(row_data.get('N', 0))}  regime={regime}",
                     fontsize=9)

    # Row 3: Bar chart comparison
    ax3 = fig.add_subplot(4, 1, 3)
    metrics = ['Gini', 'HHI', 'F', 'Psi', 'mean_loyalty']
    metric_labels = ['Gini\n(Inequality)', 'HHI\n(Concentration)',
                     'F\n(Largest fraction)', 'Ψ\n(Feudalism)',
                     'Loyalty\n(Mean)']
    x_pos = np.arange(len(metrics))
    width = 0.8 / n_terrains
    colors = plt.cm.Set2(np.linspace(0, 1, n_terrains))

    for i, terrain in enumerate(terrains):
        row_data = summary[summary['terrain'] == terrain].iloc[0]
        vals = [float(row_data.get(m, 0)) for m in metrics]
        ax3.bar(x_pos + i * width - 0.4 + width/2, vals,
                width=width, label=terrain, color=colors[i], edgecolor='gray')

    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(metric_labels, fontsize=9)
    ax3.set_ylabel('Value', fontsize=10)
    ax3.set_title('Order Parameter Comparison', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=9)
    ax3.set_ylim(0, 1.05)
    ax3.grid(axis='y', alpha=0.3)

    # Row 4: Polity structure bar chart
    ax4 = fig.add_subplot(4, 1, 4)
    polity_types = ['bands', 'tribes', 'chiefdoms', 'states', 'empires']
    polity_labels = ['Bands', 'Tribes', 'Chiefdoms', 'States', 'Empires']
    x_pos2 = np.arange(len(polity_types))
    bar_colors = [TYPE_COLORS[t.rstrip('s')] for t in polity_types]

    bottom = np.zeros(n_terrains)
    x_terrain = np.arange(n_terrains)

    for j, ptype in enumerate(polity_types):
        vals = []
        for terrain in terrains:
            row_data = summary[summary['terrain'] == terrain].iloc[0]
            vals.append(int(row_data.get(ptype, 0)))
        ax4.bar(x_terrain, vals, bottom=bottom, label=polity_labels[j],
                color=bar_colors[j], edgecolor='gray', linewidth=0.5)
        bottom += np.array(vals)

    ax4.set_xticks(x_terrain)
    ax4.set_xticklabels([TERRAIN_LABELS.get(t, t).replace('\n', ' ')
                         for t in terrains], fontsize=9)
    ax4.set_ylabel('Count', fontsize=10)
    ax4.set_title('Polity Type Distribution by Terrain', fontsize=12,
                  fontweight='bold')
    ax4.legend(fontsize=9, loc='upper right')
    ax4.grid(axis='y', alpha=0.3)

    # Add text summary
    for i, terrain in enumerate(terrains):
        row_data = summary[summary['terrain'] == terrain].iloc[0]
        text = (f"H={int(row_data.get('H', 0))} "
                f"max={int(row_data.get('largest_pop', 0))}")
        ax4.annotate(text, (i, bottom[i] + 0.5), ha='center', fontsize=8)

    fig.suptitle('Geography → Civilization: Multi-Terrain Comparison',
                 fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    if args.save:
        fig.savefig(args.save, dpi=args.dpi, bbox_inches='tight')
        print(f"Saved to {args.save}")
    else:
        plt.show()


if __name__ == '__main__':
    main()
