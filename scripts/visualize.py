#!/usr/bin/env python3
"""
Politeia spatial visualization: animate particle positions colored by wealth.
Usage: python visualize.py <output_dir> [--save animation.gif]
"""

import argparse
import glob
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np


def load_positions(filepath):
    """Load position CSV: x,y columns."""
    data = np.loadtxt(filepath, delimiter=',', skiprows=1)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    return data


def load_energy(filepath):
    """Load energy CSV: step,time,kinetic,potential_lj,potential_terrain,total."""
    return np.loadtxt(filepath, delimiter=',', skiprows=1)


def find_snapshots(output_dir):
    """Find all pos_*.csv files sorted by step number."""
    files = sorted(glob.glob(os.path.join(output_dir, 'pos_*.csv')))
    return files


def main():
    parser = argparse.ArgumentParser(description='Politeia spatial visualization')
    parser.add_argument('output_dir', help='Directory containing pos_*.csv and energy.csv')
    parser.add_argument('--save', type=str, default=None, help='Save animation to file (e.g., anim.gif)')
    parser.add_argument('--interval', type=int, default=200, help='Animation interval in ms')
    parser.add_argument('--domain', type=float, nargs=4, default=[0, 100, 0, 100],
                        help='Domain bounds: xmin xmax ymin ymax')
    args = parser.parse_args()

    snapshots = find_snapshots(args.output_dir)
    if not snapshots:
        print(f"No pos_*.csv files found in {args.output_dir}")
        sys.exit(1)

    print(f"Found {len(snapshots)} snapshots")

    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    ax.set_xlim(args.domain[0], args.domain[1])
    ax.set_ylim(args.domain[2], args.domain[3])
    ax.set_aspect('equal')
    ax.set_xlabel('x')
    ax.set_ylabel('y')

    scatter = ax.scatter([], [], s=3, c='steelblue', alpha=0.6)
    title = ax.set_title('')

    def update(frame):
        data = load_positions(snapshots[frame])
        scatter.set_offsets(data[:, :2])

        step = int(os.path.basename(snapshots[frame]).replace('pos_', '').replace('.csv', ''))
        title.set_text(f'Step {step}  N={len(data)}')
        return scatter, title

    ani = animation.FuncAnimation(
        fig, update, frames=len(snapshots),
        interval=args.interval, blit=False
    )

    if args.save:
        print(f"Saving animation to {args.save} ...")
        ani.save(args.save, writer='pillow', fps=5)
        print("Done.")
    else:
        plt.show()


if __name__ == '__main__':
    main()
