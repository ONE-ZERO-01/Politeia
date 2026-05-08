#!/usr/bin/env python3
"""
Politeia particle snapshot visualizer.

Reads snap_*.csv files and creates multi-panel visualizations showing
spatial distribution colored by different attributes (wealth, culture,
hierarchy, power, loyalty).

Usage:
    python plot_snapshot.py output/snap_00010000.csv [--save snapshot.png]
    python plot_snapshot.py output/ --step 10000 [--save snapshot.png]
"""

import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm, Normalize


def load_snapshot(filepath):
    """Load a snapshot CSV into a numpy structured array."""
    return np.genfromtxt(filepath, delimiter=',', names=True,
                         dtype=None, encoding='utf-8')


def find_snapshot(directory, step):
    """Find snapshot file for a given step."""
    fname = f"snap_{step:08d}.csv"
    path = os.path.join(directory, fname)
    if os.path.exists(path):
        return path
    # Try listing directory for closest match
    snaps = sorted(f for f in os.listdir(directory) if f.startswith('snap_'))
    if snaps:
        return os.path.join(directory, snaps[-1])
    return None


def main():
    parser = argparse.ArgumentParser(description='Politeia snapshot visualizer')
    parser.add_argument('path', help='Snapshot CSV file or output directory')
    parser.add_argument('--step', type=int, default=-1,
                        help='Step number (when path is directory)')
    parser.add_argument('--save', type=str, default=None)
    parser.add_argument('--dpi', type=int, default=150)
    parser.add_argument('--size', type=float, default=3.0,
                        help='Point size scaling')
    args = parser.parse_args()

    if os.path.isdir(args.path):
        filepath = find_snapshot(args.path, args.step)
        if filepath is None:
            print(f"No snapshot found in {args.path}", file=sys.stderr)
            sys.exit(1)
    else:
        filepath = args.path

    print(f"Loading {filepath}")
    data = load_snapshot(filepath)
    N = len(data)
    print(f"  {N} particles")

    x = data['x']
    y = data['y']
    w = data['w']
    eps = data['eps']
    sup = data['superior']
    loyalty = data['loyalty']

    has_power = 'power' in data.dtype.names
    power = data['power'] if has_power else np.zeros(N)

    # Culture: color by first two culture dimensions
    has_c0 = 'c0' in data.dtype.names
    has_c1 = 'c1' in data.dtype.names

    # ── Layout ────────────────────────────────────────────
    n_panels = 4 + int(has_power) + int(has_c0)
    ncols = 3
    nrows = (n_panels + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4.5 * nrows))
    axes = axes.flatten()

    s = args.size
    idx = 0

    # 1. Wealth
    ax = axes[idx]; idx += 1
    w_plot = np.clip(w, 0.01, np.percentile(w[w > 0], 99) if np.any(w > 0) else 1)
    sc = ax.scatter(x, y, c=w_plot, s=s, cmap='YlOrRd',
                    norm=LogNorm(vmin=max(w_plot.min(), 0.01), vmax=w_plot.max()),
                    edgecolors='none', alpha=0.7)
    fig.colorbar(sc, ax=ax, label='Wealth $w$')
    ax.set_title(f'Wealth (N={N})')
    ax.set_aspect('equal')

    # 2. Hierarchy (color by superior: roots vs attached)
    ax = axes[idx]; idx += 1
    is_root = sup < 0
    colors = np.where(is_root, 'red', 'steelblue')
    sizes = np.where(is_root, s * 5, s)
    ax.scatter(x[~is_root], y[~is_root], c='steelblue', s=s, alpha=0.4,
               edgecolors='none', label=f'Attached ({(~is_root).sum()})')
    ax.scatter(x[is_root], y[is_root], c='red', s=s * 5, alpha=0.8,
               edgecolors='black', linewidth=0.5, label=f'Roots ({is_root.sum()})')
    ax.legend(fontsize=8, loc='upper right')
    ax.set_title('Hierarchy (red=leaders)')
    ax.set_aspect('equal')

    # 3. Loyalty
    ax = axes[idx]; idx += 1
    attached = ~is_root
    if attached.any():
        sc = ax.scatter(x[attached], y[attached], c=loyalty[attached], s=s,
                        cmap='RdYlGn', vmin=0, vmax=1, edgecolors='none', alpha=0.7)
        fig.colorbar(sc, ax=ax, label='Loyalty $L$')
    ax.scatter(x[is_root], y[is_root], c='gray', s=s * 2, alpha=0.3,
               edgecolors='none')
    ax.set_title('Loyalty (attached only)')
    ax.set_aspect('equal')

    # 4. Technology level ε
    ax = axes[idx]; idx += 1
    sc = ax.scatter(x, y, c=eps, s=s, cmap='viridis', edgecolors='none', alpha=0.7)
    fig.colorbar(sc, ax=ax, label=r'$\varepsilon$')
    ax.set_title(r'Technology $\varepsilon$')
    ax.set_aspect('equal')

    # 5. Power (if available)
    if has_power:
        ax = axes[idx]; idx += 1
        p_plot = np.clip(power, 0.01, None)
        sc = ax.scatter(x, y, c=p_plot, s=s, cmap='hot',
                        norm=LogNorm(vmin=max(p_plot.min(), 0.01),
                                     vmax=max(p_plot.max(), 1)),
                        edgecolors='none', alpha=0.7)
        fig.colorbar(sc, ax=ax, label='Power')
        ax.set_title('Effective Power')
        ax.set_aspect('equal')

    # 6. Culture (if available)
    if has_c0 and has_c1:
        ax = axes[idx]; idx += 1
        c0 = data['c0']
        c1 = data['c1']
        # Map 2D culture to RGB via angle
        angle = np.arctan2(c1, c0)
        norm_angle = (angle + np.pi) / (2 * np.pi)
        sc = ax.scatter(x, y, c=norm_angle, s=s, cmap='hsv',
                        vmin=0, vmax=1, edgecolors='none', alpha=0.7)
        fig.colorbar(sc, ax=ax, label=r'Culture direction $\theta$')
        ax.set_title('Culture (color=direction)')
        ax.set_aspect('equal')

    # Hide unused axes
    for i in range(idx, len(axes)):
        axes[i].set_visible(False)

    step_str = os.path.basename(filepath).replace('snap_', '').replace('.csv', '')
    fig.suptitle(f'Politeia Snapshot — Step {step_str} (N={N})',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()

    if args.save:
        plt.savefig(args.save, dpi=args.dpi, bbox_inches='tight')
        print(f"Saved to {args.save}")
    else:
        plt.show()


if __name__ == '__main__':
    main()
