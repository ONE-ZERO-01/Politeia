#!/usr/bin/env python3
"""
Analyze and visualize a Politeia simulation run.
Generates multi-panel figures: order parameters, snapshot, polity map.

Usage:
    python3 scripts/analyze_run.py examples/genesis_hyde_100k_output/
"""
import argparse
import glob
import os
import sys

import numpy as np

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
except ImportError:
    print("ERROR: matplotlib not installed. Run: pip3 install matplotlib --user --break-system-packages")
    sys.exit(1)


def plot_order_params(output_dir, save_dir):
    csv_path = os.path.join(output_dir, 'order_params.csv')
    if not os.path.exists(csv_path):
        print(f"  SKIP: {csv_path} not found")
        return
    data = np.genfromtxt(csv_path, delimiter=',', names=True, dtype=None, encoding='utf-8')
    if data.size == 0:
        print("  SKIP: order_params.csv is empty")
        return

    time = data['time'] if 'time' in data.dtype.names else data['step']

    panels = [
        ('N',        'Population $N$',              'tab:blue'),
        ('Gini',     'Wealth Gini $G$',             'tab:red'),
        ('Q',        r'Culture order $Q$',           'tab:green'),
        ('mean_eps', r'$\langle\varepsilon\rangle$', 'tab:purple'),
        ('H',        'Hierarchy depth $H$',          'black'),
        ('C',        'Independent polities $C$',     'tab:gray'),
    ]
    available = [(k, l, c) for k, l, c in panels if k in data.dtype.names]
    n = len(available)
    if n == 0:
        print("  SKIP: no recognized columns in order_params.csv")
        return

    fig, axes = plt.subplots(n, 1, figsize=(10, 2.5 * n), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, (key, label, color) in zip(axes, available):
        ax.plot(time, data[key], '-o', color=color, markersize=3, linewidth=1.5)
        ax.set_ylabel(label, fontsize=11)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel('Simulation time (years)', fontsize=11)
    fig.suptitle('Politeia — Order Parameter Evolution', fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(save_dir, 'order_params.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_snapshot(output_dir, save_dir):
    snaps = sorted(glob.glob(os.path.join(output_dir, 'snap_*.csv')))
    if not snaps:
        print("  SKIP: no snapshot files")
        return
    snap_file = snaps[-1]
    step = os.path.basename(snap_file).replace('snap_', '').replace('.csv', '')
    data = np.genfromtxt(snap_file, delimiter=',', names=True, dtype=None, encoding='utf-8')
    if data.size == 0:
        return

    x, y = data['x'], data['y']
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Wealth distribution
    ax = axes[0, 0]
    w = np.clip(data['w'], 0.1, None)
    sc = ax.scatter(x, y, c=w, s=0.3, cmap='YlOrRd', norm=LogNorm(), alpha=0.6, rasterized=True)
    fig.colorbar(sc, ax=ax, label='Wealth', shrink=0.8)
    ax.set_title('Wealth Distribution')
    ax.set_xlim(-180, 180)
    ax.set_ylim(-85, 85)
    ax.set_aspect('equal')

    # Power/hierarchy
    ax = axes[0, 1]
    power = np.clip(data['power'], 0.1, None)
    sc = ax.scatter(x, y, c=power, s=0.3, cmap='Purples', norm=LogNorm(), alpha=0.6, rasterized=True)
    fig.colorbar(sc, ax=ax, label='Power', shrink=0.8)
    ax.set_title('Political Power')
    ax.set_xlim(-180, 180)
    ax.set_ylim(-85, 85)
    ax.set_aspect('equal')

    # Technology (epsilon)
    ax = axes[1, 0]
    sc = ax.scatter(x, y, c=data['eps'], s=0.3, cmap='viridis', alpha=0.6, rasterized=True)
    fig.colorbar(sc, ax=ax, label=r'$\varepsilon$', shrink=0.8)
    ax.set_title('Technology Level')
    ax.set_xlim(-180, 180)
    ax.set_ylim(-85, 85)
    ax.set_aspect('equal')

    # Age
    ax = axes[1, 1]
    sc = ax.scatter(x, y, c=data['age'], s=0.3, cmap='coolwarm', alpha=0.6, rasterized=True)
    fig.colorbar(sc, ax=ax, label='Age', shrink=0.8)
    ax.set_title('Age Distribution')
    ax.set_xlim(-180, 180)
    ax.set_ylim(-85, 85)
    ax.set_aspect('equal')

    fig.suptitle(f'Politeia — Snapshot at step {step}  (N={len(data):,})', fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(save_dir, f'snapshot_{step}.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def diagnose_energy(output_dir):
    """Print a quick health check of the energy values."""
    csv_path = os.path.join(output_dir, 'energy.csv')
    if not os.path.exists(csv_path):
        return
    data = np.genfromtxt(csv_path, delimiter=',', names=True, dtype=None, encoding='utf-8')
    if data.size == 0:
        return

    print("  ── Energy Diagnostics ──")
    for col in data.dtype.names:
        if col in ('step', 'time'):
            continue
        vals = data[col]
        vmin, vmax, vmean = np.min(vals), np.max(vals), np.mean(vals)
        flag = ""
        if np.any(np.abs(vals) > 1e15):
            flag = " ⚠ EXPLOSION"
        elif np.any(np.isnan(vals)) or np.any(np.isinf(vals)):
            flag = " ⚠ NaN/Inf"
        print(f"    {col:25s}  min={vmin:12.3e}  max={vmax:12.3e}  mean={vmean:12.3e}{flag}")

    social = data['potential_social'] if 'potential_social' in data.dtype.names else None
    if social is not None:
        max_abs = np.max(np.abs(social))
        if max_abs > 1e15:
            print(f"  ⚠ Social PE max |{max_abs:.2e}| > 1e15 — soft-core r_min may need adjustment")
        elif max_abs > 1e10:
            print(f"  ⚠ Social PE max |{max_abs:.2e}| > 1e10 — elevated but may stabilize")
        else:
            print(f"  ✓ Social PE max |{max_abs:.2e}| — within healthy range")
    print()


def plot_energy(output_dir, save_dir):
    csv_path = os.path.join(output_dir, 'energy.csv')
    if not os.path.exists(csv_path):
        print("  SKIP: energy.csv not found")
        return
    data = np.genfromtxt(csv_path, delimiter=',', names=True, dtype=None, encoding='utf-8')
    if data.size == 0:
        return

    time = data['time'] if 'time' in data.dtype.names else data['step']
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    ax = axes[0]
    ax.plot(time, data['kinetic'], '-o', label='Kinetic', markersize=3)
    if 'potential_terrain' in data.dtype.names:
        ax.plot(time, data['potential_terrain'], '-s', label='Terrain PE', markersize=3)
    ax.set_ylabel('Energy')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_title('Physical Energy Components')

    ax = axes[1]
    if 'potential_social' in data.dtype.names:
        social = data['potential_social']
        ax.semilogy(time, np.abs(social), '-o', color='red', markersize=3)
        max_val = np.max(np.abs(social))
        color = 'green' if max_val < 1e10 else ('orange' if max_val < 1e15 else 'red')
        ax.axhline(y=1e10, color='orange', linestyle='--', alpha=0.5, label='Warning threshold')
        ax.set_ylabel('|Social Potential|')
        ax.set_title(f'Social PE (log) — max |{max_val:.2e}|', color=color)
    ax.set_xlabel('Time (years)')
    ax.grid(True, alpha=0.3)

    fig.suptitle('Politeia — Energy Evolution', fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(save_dir, 'energy.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_polity_summary(output_dir, save_dir):
    csv_path = os.path.join(output_dir, 'polity_summary.csv')
    if not os.path.exists(csv_path):
        print("  SKIP: polity_summary.csv not found")
        return
    data = np.genfromtxt(csv_path, delimiter=',', names=True, dtype=None, encoding='utf-8')
    if data.size == 0:
        return

    time = data['time']
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    ax = axes[0, 0]
    for col, label, color in [('bands', 'Bands', '#2196F3'),
                               ('tribes', 'Tribes', '#4CAF50'),
                               ('chiefdoms', 'Chiefdoms', '#FF9800'),
                               ('states', 'States', '#F44336'),
                               ('empires', 'Empires', '#9C27B0')]:
        if col in data.dtype.names:
            ax.plot(time, data[col], '-o', label=label, color=color, markersize=4)
    ax.set_ylabel('Count')
    ax.set_title('Political Organization Types')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[0, 1]
    ax.plot(time, data['largest_pop'], '-o', color='tab:red', markersize=4)
    ax.set_ylabel('Population')
    ax.set_title('Largest Polity Size')
    ax.grid(True, alpha=0.3)

    ax = axes[1, 0]
    ax.plot(time, data['n_polities'], '-o', color='tab:blue', markersize=4)
    ax.set_ylabel('Count')
    ax.set_title('Total Polities')
    ax.set_xlabel('Time (years)')
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    ax.plot(time, data['HHI'], '-o', color='tab:orange', markersize=4)
    ax.set_ylabel('HHI')
    ax.set_title('Political Concentration (HHI)')
    ax.set_xlabel('Time (years)')
    ax.grid(True, alpha=0.3)

    fig.suptitle('Politeia — Political Evolution', fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(save_dir, 'polity_evolution.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_polity_map(output_dir, save_dir):
    """Plot the largest polities on a map at the final step."""
    polity_files = sorted(glob.glob(os.path.join(output_dir, 'polities_*.csv')))
    snap_files = sorted(glob.glob(os.path.join(output_dir, 'snap_*.csv')))
    if not polity_files or not snap_files:
        print("  SKIP: polity/snapshot files not found")
        return

    polity_file = polity_files[-1]
    snap_file = snap_files[-1]
    step = os.path.basename(snap_file).replace('snap_', '').replace('.csv', '')

    polities = np.genfromtxt(polity_file, delimiter=',', names=True, dtype=None, encoding='utf-8')
    snap = np.genfromtxt(snap_file, delimiter=',', names=True, dtype=None, encoding='utf-8')
    if polities.size == 0 or snap.size == 0:
        return

    top_n = min(20, len(polities))
    pop_sorted = np.argsort(polities['population'])[::-1][:top_n]
    top_roots = set(polities['root_gid'][pop_sorted])

    fig, ax = plt.subplots(figsize=(14, 7))

    independent = snap['superior'] == -1
    ax.scatter(snap['x'][~independent], snap['y'][~independent],
               c='lightgray', s=0.1, alpha=0.3, rasterized=True, label='Subjects')
    ax.scatter(snap['x'][independent], snap['y'][independent],
               c='gray', s=0.5, alpha=0.5, rasterized=True, label='Independent')

    cmap = plt.cm.tab20
    for idx, pi in enumerate(pop_sorted):
        root = polities['root_gid'][pi]
        cx, cy = polities['cx'][pi], polities['cy'][pi]
        pop = polities['population'][pi]
        ptype = polities['type'][pi] if 'type' in polities.dtype.names else '?'
        color = cmap(idx / top_n)
        ax.scatter(cx, cy, c=[color], s=max(30, pop / 2), edgecolors='black',
                   linewidth=0.5, zorder=10, marker='*')
        ax.annotate(f'{ptype}\nN={pop}', (cx, cy), fontsize=6,
                    ha='center', va='bottom', color=color, fontweight='bold')

    ax.set_xlim(-180, 180)
    ax.set_ylim(-85, 85)
    ax.set_aspect('equal')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title(f'Top-{top_n} Polities at step {step}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    path = os.path.join(save_dir, f'polity_map_{step}.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_distributions(output_dir, save_dir):
    """Plot distribution histograms from the final snapshot."""
    snaps = sorted(glob.glob(os.path.join(output_dir, 'snap_*.csv')))
    if not snaps:
        print("  SKIP: no snapshot files")
        return
    snap_file = snaps[-1]
    step = os.path.basename(snap_file).replace('snap_', '').replace('.csv', '')
    data = np.genfromtxt(snap_file, delimiter=',', names=True, dtype=None, encoding='utf-8')
    if data.size == 0:
        return

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))

    configs = [
        ('w',     'Wealth',       axes[0,0], 'tab:red',    True),
        ('eps',   'Technology ε', axes[0,1], 'tab:purple', False),
        ('age',   'Age',          axes[0,2], 'tab:blue',   False),
    ]

    for col, label, ax, color, use_log in configs:
        if col not in data.dtype.names:
            ax.set_visible(False)
            continue
        vals = data[col]
        vals = vals[np.isfinite(vals)]
        if len(vals) == 0:
            continue
        if use_log:
            vals = vals[vals > 0]
            if len(vals) > 0:
                ax.hist(np.log10(vals), bins=50, color=color, alpha=0.7, edgecolor='black', linewidth=0.5)
                ax.set_xlabel(f'log₁₀({label})')
        else:
            ax.hist(vals, bins=50, color=color, alpha=0.7, edgecolor='black', linewidth=0.5)
            ax.set_xlabel(label)
        ax.set_ylabel('Count')
        ax.set_title(f'{label} Distribution')
        ax.grid(True, alpha=0.3)
        stats_text = f'N={len(vals):,}\nμ={np.mean(vals):.2f}\nσ={np.std(vals):.2f}'
        ax.text(0.95, 0.95, stats_text, transform=ax.transAxes, fontsize=8,
                va='top', ha='right', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    if 'power' in data.dtype.names:
        ax = axes[1, 0]
        power = data['power']
        power = power[power > 0]
        if len(power) > 0:
            ax.hist(np.log10(power), bins=50, color='tab:orange', alpha=0.7, edgecolor='black', linewidth=0.5)
            ax.set_xlabel('log₁₀(Power)')
            ax.set_ylabel('Count')
            ax.set_title('Power Distribution')
            ax.grid(True, alpha=0.3)
    else:
        axes[1, 0].set_visible(False)

    if 'loyalty' in data.dtype.names:
        ax = axes[1, 1]
        loyalty = data['loyalty']
        loyalty = loyalty[np.isfinite(loyalty) & (loyalty > 0)]
        if len(loyalty) > 0:
            ax.hist(loyalty, bins=50, color='tab:green', alpha=0.7, edgecolor='black', linewidth=0.5)
            ax.set_xlabel('Loyalty')
            ax.set_ylabel('Count')
            ax.set_title('Loyalty Distribution')
            ax.grid(True, alpha=0.3)
    else:
        axes[1, 1].set_visible(False)

    ax = axes[1, 2]
    if 'w' in data.dtype.names:
        w = np.sort(data['w'])[::-1]
        n = len(w)
        cum = np.cumsum(w)
        total = cum[-1] if cum[-1] > 0 else 1
        ax.plot(np.arange(1, n+1) / n * 100, cum / total * 100, color='tab:red', linewidth=2)
        ax.plot([0, 100], [0, 100], '--', color='gray', alpha=0.5, label='Perfect equality')
        trapz_fn = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
        gini = 1 - 2 * trapz_fn(cum / total, dx=1/n)
        ax.fill_between(np.arange(1, n+1) / n * 100, cum / total * 100,
                         np.arange(1, n+1) / n * 100, alpha=0.2, color='tab:red')
        ax.set_xlabel('Population %')
        ax.set_ylabel('Wealth %')
        ax.set_title(f'Lorenz Curve (Gini = {gini:.3f})')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    fig.suptitle(f'Politeia — Distributions at step {step}  (N={len(data):,})', fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(save_dir, f'distributions_{step}.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def print_summary(output_dir):
    """Print a concise text summary of key emergent results."""
    print("  ── Emergent Phenomena Summary ──")

    op_path = os.path.join(output_dir, 'order_params.csv')
    if os.path.exists(op_path):
        data = np.genfromtxt(op_path, delimiter=',', names=True, dtype=None, encoding='utf-8')
        if data.size > 0:
            if data.ndim == 0:
                data = np.array([data])
            names = data.dtype.names
            last = {k: data[k][-1] if k in names else None for k in
                    ['N', 'Gini', 'Q', 'H', 'C', 'mean_eps', 'F']}
            first = {k: data[k][0] if k in names else None for k in
                     ['N', 'Gini', 'Q', 'H', 'C']}
            fmt = lambda v: f"{v:.4f}" if v is not None and abs(v) < 100 else (f"{v:.0f}" if v is not None else "N/A")
            print(f"    Population:      {fmt(first.get('N'))} → {fmt(last.get('N'))}")
            print(f"    Wealth Gini:     {fmt(first.get('Gini'))} → {fmt(last.get('Gini'))}")
            print(f"    Culture Q:       {fmt(first.get('Q'))} → {fmt(last.get('Q'))}")
            print(f"    Hierarchy H:     {fmt(first.get('H'))} → {fmt(last.get('H'))}")
            print(f"    Polities C:      {fmt(first.get('C'))} → {fmt(last.get('C'))}")
            if last.get('Gini') is not None and last['Gini'] > 0.5:
                print("    → Inequality emerged from symmetric rules!")
            if last.get('H') is not None and last['H'] > 3:
                print("    → Political hierarchies deepened spontaneously!")
    print()


def main():
    parser = argparse.ArgumentParser(description='Analyze Politeia simulation results')
    parser.add_argument('output_dir', help='Path to simulation output directory')
    parser.add_argument('--save-dir', default=None, help='Directory to save plots (default: output_dir)')
    args = parser.parse_args()

    output_dir = args.output_dir
    save_dir = args.save_dir or output_dir

    if not os.path.isdir(output_dir):
        print(f"ERROR: {output_dir} does not exist or is not a directory")
        sys.exit(1)

    os.makedirs(save_dir, exist_ok=True)

    print(f"{'='*50}")
    print(f"  Politeia Run Analysis")
    print(f"{'='*50}")
    print(f"  Output directory: {output_dir}")
    print(f"  Save directory:   {save_dir}")
    print()

    files = os.listdir(output_dir)
    snaps = sorted([f for f in files if f.startswith('snap_') and f.endswith('.csv')])
    csvs = [f for f in files if f.endswith('.csv')]
    print(f"  Found {len(csvs)} CSV files, {len(snaps)} snapshots")
    print()

    print("[1/7] Energy diagnostics...")
    diagnose_energy(output_dir)

    print("[2/7] Order parameters...")
    plot_order_params(output_dir, save_dir)

    print("[3/7] Energy evolution...")
    plot_energy(output_dir, save_dir)

    print("[4/7] Final snapshot map...")
    plot_snapshot(output_dir, save_dir)

    print("[5/7] Distribution histograms...")
    plot_distributions(output_dir, save_dir)

    print("[6/7] Political evolution...")
    plot_polity_summary(output_dir, save_dir)

    print("[7/7] Polity map...")
    plot_polity_map(output_dir, save_dir)

    print()
    print_summary(output_dir)

    print(f"{'='*50}")
    print(f"  Analysis complete!")
    print(f"{'='*50}")
    pngs = sorted([f for f in os.listdir(save_dir) if f.endswith('.png')])
    print(f"  Generated {len(pngs)} PNG files in {save_dir}/")
    for p in pngs:
        size = os.path.getsize(os.path.join(save_dir, p))
        print(f"    {p}  ({size / 1024:.0f} KB)")


if __name__ == '__main__':
    main()
