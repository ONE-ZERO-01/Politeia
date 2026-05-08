#!/usr/bin/env python3
"""Visualize synthetic terrain with optional particle overlay."""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import sys


def generate_river(nx, ny, xmin, ymin, xmax, ymax):
    h = np.zeros((ny, nx))
    for r in range(ny):
        for c in range(nx):
            x = xmin + c * (xmax - xmin) / (nx - 1)
            y = ymin + r * (ymax - ymin) / (ny - 1)
            norm_x = (x - xmin) / (xmax - xmin)
            norm_y = (y - ymin) / (ymax - ymin)
            river_y = 0.5 + 0.15 * np.sin(norm_x * np.pi * 3.0)
            dist_river = abs(norm_y - river_y)
            river_valley = np.exp(-dist_river**2 * 80.0)
            floodplain = np.exp(-dist_river**2 * 15.0)
            edge_y = min(norm_y, 1.0 - norm_y)
            mountains = np.exp(-edge_y**2 * 20.0) * 80.0
            val = mountains + 30.0 * (1.0 - floodplain) - 5.0 * river_valley
            h[r, c] = max(0.0, val)
    return h


def generate_basins(nx, ny, xmin, ymin, xmax, ymax):
    h = np.zeros((ny, nx))
    basins = [(0.25, 0.35, 0.12, 0.10),
              (0.55, 0.55, 0.15, 0.12),
              (0.25, 0.70, 0.10, 0.08),
              (0.75, 0.35, 0.12, 0.10)]
    for r in range(ny):
        for c in range(nx):
            x = xmin + c * (xmax - xmin) / (nx - 1)
            y = ymin + r * (ymax - ymin) / (ny - 1)
            norm_x = (x - xmin) / (xmax - xmin)
            norm_y = (y - ymin) / (ymax - ymin)
            base = 60.0
            for cx, cy, sx, sy in basins:
                bx = (norm_x - cx) / sx
                by = (norm_y - cy) / sy
                base -= 55.0 * np.exp(-(bx**2 + by**2))
            ex = min(norm_x, 1.0 - norm_x)
            ey = min(norm_y, 1.0 - norm_y)
            edge = min(ex, ey)
            base += 40.0 * np.exp(-edge**2 * 30.0)
            h[r, c] = max(0.0, base)
    return h


def generate_continent(nx, ny, xmin, ymin, xmax, ymax):
    h = np.zeros((ny, nx))
    for r in range(ny):
        for c in range(nx):
            x = xmin + c * (xmax - xmin) / (nx - 1)
            y = ymin + r * (ymax - ymin) / (ny - 1)
            norm_x = (x - xmin) / (xmax - xmin)
            norm_y = (y - ymin) / (ymax - ymin)
            ex = min(norm_x, 1.0 - norm_x)
            ey = min(norm_y, 1.0 - norm_y)
            coast = min(ex, ey)
            ocean = 200.0 * np.exp(-coast**2 * 50.0)
            mt_dist = abs(norm_y - (1.2 - norm_x))
            mountains = 60.0 * np.exp(-mt_dist**2 * 100.0)
            p1dx, p1dy = norm_x - 0.35, norm_y - 0.4
            plain1 = 30.0 * np.exp(-(p1dx**2 + p1dy**2) * 8.0)
            p2dx, p2dy = norm_x - 0.65, norm_y - 0.6
            plain2 = 30.0 * np.exp(-(p2dx**2 + p2dy**2) * 8.0)
            val = ocean + mountains + 20.0 - plain1 - plain2
            h[r, c] = max(0.0, val)
    return h


def generate_china(nx, ny, xmin, ymin, xmax, ymax):
    h = np.zeros((ny, nx))
    for r in range(ny):
        for c in range(nx):
            x = xmin + c * (xmax - xmin) / (nx - 1)
            y = ymin + r * (ymax - ymin) / (ny - 1)
            nx_ = (x - xmin) / (xmax - xmin)
            ny_ = (y - ymin) / (ymax - ymin)
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
            ex = min(nx_, 1 - nx_); ey = min(ny_, 1 - ny_)
            edge = min(ex, ey)
            emt = 30.0 * np.exp(-edge**2 * 40)
            h[r, c] = max(0.0, west + north + south + emt + 40 - plain - yr - yz)
    return h


def generate_europe(nx, ny, xmin, ymin, xmax, ymax):
    h = np.zeros((ny, nx))
    for r in range(ny):
        for c in range(nx):
            x = xmin + c * (xmax - xmin) / (nx - 1)
            y = ymin + r * (ymax - ymin) / (ny - 1)
            nx_ = (x - xmin) / (xmax - xmin)
            ny_ = (y - ymin) / (ymax - ymin)
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
            ex = min(nx_, 1-nx_); ey = min(ny_, 1-ny_)
            ocean = 60.0 * np.exp(-min(ex,ey)**2 * 40)
            h[r, c] = max(0.0, ocean + alps + pyr + carp + scand + 40 - bs)
    return h


GENERATORS = {
    'river': generate_river,
    'basins': generate_basins,
    'continent': generate_continent,
    'china': generate_china,
    'europe': generate_europe,
}


def load_snapshot(filepath):
    """Load particle snapshot for overlay."""
    import csv
    data = {'x': [], 'y': [], 'w': []}
    with open(filepath) as f:
        reader = csv.DictReader(f)
        for row in reader:
            data['x'].append(float(row['x']))
            data['y'].append(float(row['y']))
            data['w'].append(float(row['w']))
    return data


def main():
    parser = argparse.ArgumentParser(description='Visualize synthetic terrain')
    parser.add_argument('terrain_type', choices=list(GENERATORS.keys()) + ['all'])
    parser.add_argument('--nx', type=int, default=256)
    parser.add_argument('--ny', type=int, default=256)
    parser.add_argument('--xmin', type=float, default=0.0)
    parser.add_argument('--ymin', type=float, default=0.0)
    parser.add_argument('--xmax', type=float, default=100.0)
    parser.add_argument('--ymax', type=float, default=100.0)
    parser.add_argument('--overlay', type=str, default=None,
                        help='Path to snap_*.csv to overlay particles')
    parser.add_argument('--save', type=str, default=None)
    parser.add_argument('--dpi', type=int, default=150)
    args = parser.parse_args()

    if args.terrain_type == 'all':
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        for ax, (name, gen_fn) in zip(axes, GENERATORS.items()):
            h = gen_fn(args.nx, args.ny, args.xmin, args.ymin, args.xmax, args.ymax)
            im = ax.imshow(h, origin='lower', cmap='terrain',
                           extent=[args.xmin, args.xmax, args.ymin, args.ymax],
                           aspect='equal')
            ax.set_title(f'Synthetic terrain: {name}', fontsize=12)
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            plt.colorbar(im, ax=ax, label='Elevation h', shrink=0.8)
        plt.tight_layout()
    else:
        gen_fn = GENERATORS[args.terrain_type]
        h = gen_fn(args.nx, args.ny, args.xmin, args.ymin, args.xmax, args.ymax)

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        im0 = axes[0].imshow(h, origin='lower', cmap='terrain',
                              extent=[args.xmin, args.xmax, args.ymin, args.ymax],
                              aspect='equal')
        axes[0].set_title(f'Terrain: {args.terrain_type}', fontsize=13)
        axes[0].set_xlabel('x')
        axes[0].set_ylabel('y')
        plt.colorbar(im0, ax=axes[0], label='Elevation h')

        scale = 0.5
        h_max = h.max()
        V = -scale * (h_max - h)
        production = np.maximum(0, -V) * 0.05
        im1 = axes[1].imshow(production, origin='lower', cmap='YlGn',
                              extent=[args.xmin, args.xmax, args.ymin, args.ymax],
                              aspect='equal')
        axes[1].set_title('Resource production R(x)', fontsize=13)
        axes[1].set_xlabel('x')
        axes[1].set_ylabel('y')
        plt.colorbar(im1, ax=axes[1], label='Production rate')

        if args.overlay:
            snap = load_snapshot(args.overlay)
            for ax in axes:
                ax.scatter(snap['x'], snap['y'], c='red', s=2, alpha=0.5, zorder=5)

        plt.tight_layout()

    if args.save:
        plt.savefig(args.save, dpi=args.dpi, bbox_inches='tight')
        print(f'Saved to {args.save}')
    else:
        plt.show()


if __name__ == '__main__':
    main()
