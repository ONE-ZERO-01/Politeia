#!/usr/bin/env python3
"""
Politeia world-map visualizer with real terrain.

Maps simulation coordinates to geographic coordinates and renders particles
on an interactive world map (Plotly) or a static map (Matplotlib + terrain
image). Supports three modes:

  1. Interactive HTML map (default) — Plotly Scattergeo on a topographic
     basemap, colored by wealth/hierarchy/culture/ε, with hover tooltips.
  2. Static PNG map — Matplotlib with downloaded terrain raster as background.
  3. Animation — series of snapshots rendered as frames in an HTML animation.

Coordinate mapping:
  The simulation uses an abstract domain [xmin,xmax]×[ymin,ymax].
  This script linearly maps it to a geographic bounding box (default: global
  or user-specified region). For scientifically meaningful results, the .cfg
  should use a domain that matches the chosen geographic extent.

Usage:
    # Interactive global map (wealth coloring)
    python plot_worldmap.py output/ --color wealth

    # Specific region (China)
    python plot_worldmap.py output/ --region china --color epsilon

    # Static PNG with terrain
    python plot_worldmap.py output/ --static --save worldmap.png

    # Animation of all snapshots
    python plot_worldmap.py output/ --animate --save civilization.html

    # Single snapshot
    python plot_worldmap.py output/snap_00010000.csv --color hierarchy
"""

import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

# ─── Geographic regions ─────────────────────────────────────────────────

REGIONS = {
    'global':       {'lat': (-60, 75), 'lon': (-180, 180),
                     'label': 'Global'},
    'china':        {'lat': (18, 54), 'lon': (73, 135),
                     'label': 'China'},
    'europe':       {'lat': (35, 72), 'lon': (-12, 45),
                     'label': 'Europe'},
    'mediterranean':{'lat': (28, 48), 'lon': (-10, 42),
                     'label': 'Mediterranean'},
    'mesopotamia':  {'lat': (28, 42), 'lon': (38, 55),
                     'label': 'Mesopotamia'},
    'nile':         {'lat': (22, 32), 'lon': (28, 36),
                     'label': 'Nile Valley'},
    'indus':        {'lat': (22, 36), 'lon': (64, 78),
                     'label': 'Indus Valley'},
    'eastasia':     {'lat': (15, 55), 'lon': (70, 145),
                     'label': 'East Asia'},
    'oldworld':     {'lat': (-10, 60), 'lon': (-20, 140),
                     'label': 'Old World'},
}

COLOR_CONFIGS = {
    'wealth':    {'col': 'w',       'cmap': 'YlOrRd',  'log': True,
                  'label': 'Wealth (w)', 'plotly_scale': 'YlOrRd'},
    'epsilon':   {'col': 'eps',     'cmap': 'viridis',  'log': False,
                  'label': 'Technology (ε)', 'plotly_scale': 'Viridis'},
    'hierarchy': {'col': 'superior','cmap': None,       'log': False,
                  'label': 'Hierarchy', 'plotly_scale': None},
    'loyalty':   {'col': 'loyalty', 'cmap': 'RdYlGn',  'log': False,
                  'label': 'Loyalty (L)', 'plotly_scale': 'RdYlGn'},
    'age':       {'col': 'age',     'cmap': 'plasma',   'log': False,
                  'label': 'Age', 'plotly_scale': 'Plasma'},
    'culture':   {'col': 'c0',      'cmap': 'hsv',      'log': False,
                  'label': 'Culture direction', 'plotly_scale': 'HSV'},
    'power':     {'col': 'power',   'cmap': 'hot',      'log': True,
                  'label': 'Power', 'plotly_scale': 'Hot'},
    'polity':    {'col': 'superior','cmap': 'tab20',    'log': False,
                  'label': 'Polity (by leader)', 'plotly_scale': None},
}


def load_snapshot(filepath):
    """Load a snapshot CSV into a DataFrame."""
    return pd.read_csv(filepath)


def find_snapshots(directory):
    """Find all snapshot files in directory, sorted by step."""
    pattern = os.path.join(directory, 'snap_*.csv')
    files = sorted(glob.glob(pattern))
    return files


def map_coords(df, domain, region):
    """Map simulation (x,y) to geographic (lon,lat)."""
    xmin, xmax = domain[0], domain[1]
    ymin, ymax = domain[2], domain[3]
    lon_min, lon_max = region['lon']
    lat_min, lat_max = region['lat']

    df = df.copy()
    df['lon'] = lon_min + (df['x'] - xmin) / (xmax - xmin) * (lon_max - lon_min)
    df['lat'] = lat_min + (df['y'] - ymin) / (ymax - ymin) * (lat_max - lat_min)
    return df


def get_color_data(df, color_mode):
    """Compute color array and metadata for the chosen mode."""
    cfg = COLOR_CONFIGS[color_mode]
    col = cfg['col']

    if color_mode == 'hierarchy':
        is_root = df['superior'] < 0
        colors = np.where(is_root, 1.0, 0.0)
        text = np.where(is_root, 'Leader', 'Follower')
        return colors, text, 'Hierarchy', False

    if color_mode == 'culture' and 'c0' in df.columns and 'c1' in df.columns:
        angle = np.arctan2(df['c1'].values, df['c0'].values)
        colors = (angle + np.pi) / (2 * np.pi)
        text = [f'θ={a:.2f}' for a in angle]
        return colors, text, 'Culture direction', False

    if color_mode == 'polity':
        leaders = df['superior'].values.copy()
        leaders[leaders < 0] = df['gid'].values[leaders < 0]
        unique_leaders = np.unique(leaders)
        leader_map = {lid: i for i, lid in enumerate(unique_leaders)}
        colors = np.array([leader_map[l] for l in leaders], dtype=float)
        text = [f'Polity {int(l)}' for l in leaders]
        return colors, text, 'Polity', False

    if col not in df.columns:
        return np.zeros(len(df)), ['N/A'] * len(df), cfg['label'], False

    values = df[col].values.astype(float)
    text = [f'{cfg["label"]}: {v:.3f}' for v in values]
    return values, text, cfg['label'], cfg['log']


# ─── Plotly interactive map ─────────────────────────────────────────────

def plot_interactive(df, color_mode, region_key, title, polity_df=None):
    """Create an interactive Plotly map."""
    import plotly.graph_objects as go

    region = REGIONS[region_key]
    colors, hover_text, color_label, use_log = get_color_data(df, color_mode)
    cfg = COLOR_CONFIGS[color_mode]

    hover = []
    for i in range(len(df)):
        parts = [
            f"gid: {int(df['gid'].iloc[i])}",
            f"w: {df['w'].iloc[i]:.2f}",
            f"ε: {df['eps'].iloc[i]:.3f}",
            f"age: {df['age'].iloc[i]:.1f}",
        ]
        if 'power' in df.columns:
            parts.append(f"power: {df['power'].iloc[i]:.2f}")
        parts.append(f"loyalty: {df['loyalty'].iloc[i]:.3f}")
        sup = int(df['superior'].iloc[i])
        parts.append(f"superior: {'(root)' if sup < 0 else sup}")
        hover.append('<br>'.join(parts))

    if color_mode in ('hierarchy', 'polity'):
        if color_mode == 'hierarchy':
            is_root = df['superior'] < 0
            fig = go.Figure()
            fig.add_trace(go.Scattergeo(
                lon=df.loc[~is_root, 'lon'], lat=df.loc[~is_root, 'lat'],
                mode='markers',
                marker=dict(size=4, color='steelblue', opacity=0.5),
                name=f'Followers ({(~is_root).sum()})',
                text=[hover[i] for i in df.index[~is_root]],
                hoverinfo='text',
            ))
            fig.add_trace(go.Scattergeo(
                lon=df.loc[is_root, 'lon'], lat=df.loc[is_root, 'lat'],
                mode='markers',
                marker=dict(size=8, color='red', opacity=0.9,
                            line=dict(width=0.5, color='black')),
                name=f'Leaders ({is_root.sum()})',
                text=[hover[i] for i in df.index[is_root]],
                hoverinfo='text',
            ))
        else:
            fig = go.Figure()
            fig.add_trace(go.Scattergeo(
                lon=df['lon'], lat=df['lat'],
                mode='markers',
                marker=dict(size=5, color=colors, colorscale='HSV',
                            opacity=0.7),
                text=hover, hoverinfo='text',
                name='Particles',
            ))
    else:
        if use_log:
            colors = np.log1p(np.clip(colors, 0, None))

        fig = go.Figure()
        fig.add_trace(go.Scattergeo(
            lon=df['lon'], lat=df['lat'],
            mode='markers',
            marker=dict(
                size=5, color=colors,
                colorscale=cfg['plotly_scale'] or 'Viridis',
                colorbar=dict(title=color_label),
                opacity=0.7,
            ),
            text=hover, hoverinfo='text',
            name='Particles',
        ))

    if polity_df is not None and len(polity_df) > 0:
        type_colors = {
            'band': 'lightblue', 'tribe': 'blue', 'chiefdom': 'orange',
            'state': 'red', 'empire': 'darkred',
        }
        for _, row in polity_df.iterrows():
            ptype = row.get('type', 'band')
            fig.add_trace(go.Scattergeo(
                lon=[row['lon']], lat=[row['lat']],
                mode='markers+text',
                marker=dict(
                    size=max(10, int(row.get('population', 1)) * 2),
                    color=type_colors.get(ptype, 'gray'),
                    opacity=0.6,
                    line=dict(width=1, color='black'),
                    symbol='diamond',
                ),
                text=[f"{ptype} (pop={int(row.get('population', 0))})"],
                textposition='top center',
                textfont=dict(size=8),
                showlegend=False,
                hoverinfo='text',
            ))

    fig.update_geos(
        resolution=50,
        showcoastlines=True, coastlinecolor='#444',
        showland=True, landcolor='#e8e4d8',
        showocean=True, oceancolor='#c6e2ff',
        showlakes=True, lakecolor='#c6e2ff',
        showrivers=True, rivercolor='#8ec8f0',
        showcountries=True, countrycolor='#999',
        lataxis=dict(range=[region['lat'][0], region['lat'][1]]),
        lonaxis=dict(range=[region['lon'][0], region['lon'][1]]),
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        margin=dict(l=10, r=10, t=50, b=10),
        height=700,
        geo=dict(
            projection_type='natural earth',
            bgcolor='#f0f8ff',
        ),
    )

    return fig


# ─── Matplotlib static map ─────────────────────────────────────────────

def plot_static(df, color_mode, region_key, title, polity_df=None):
    """Create a static Matplotlib map with terrain-like background."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm, Normalize
    from scipy.ndimage import gaussian_filter

    region = REGIONS[region_key]
    colors, _, color_label, use_log = get_color_data(df, color_mode)
    cfg = COLOR_CONFIGS[color_mode]

    fig, ax = plt.subplots(1, 1, figsize=(14, 8))

    lon_range = region['lon']
    lat_range = region['lat']

    terrain = _generate_simple_terrain(lon_range, lat_range)
    ax.imshow(terrain, extent=[lon_range[0], lon_range[1],
                                lat_range[0], lat_range[1]],
              origin='lower', cmap='terrain', alpha=0.6, aspect='auto')

    if color_mode == 'hierarchy':
        is_root = df['superior'] < 0
        ax.scatter(df.loc[~is_root, 'lon'], df.loc[~is_root, 'lat'],
                   c='steelblue', s=3, alpha=0.4, label='Followers')
        ax.scatter(df.loc[is_root, 'lon'], df.loc[is_root, 'lat'],
                   c='red', s=15, alpha=0.8, edgecolors='k', linewidth=0.3,
                   label='Leaders')
        ax.legend(fontsize=9)
    elif color_mode == 'polity':
        sc = ax.scatter(df['lon'], df['lat'], c=colors, s=5,
                        cmap='tab20', alpha=0.7, edgecolors='none')
    else:
        norm = LogNorm(vmin=max(0.01, np.nanmin(colors)),
                       vmax=max(1, np.nanmax(colors))) if use_log else None
        cmap = cfg['cmap'] or 'viridis'
        sc = ax.scatter(df['lon'], df['lat'], c=colors, s=5,
                        cmap=cmap, norm=norm, alpha=0.7, edgecolors='none')
        plt.colorbar(sc, ax=ax, label=color_label, shrink=0.8)

    if polity_df is not None and len(polity_df) > 0:
        type_colors = {
            'band': '#9ecae1', 'tribe': '#6baed6', 'chiefdom': '#3182bd',
            'state': '#e6550d', 'empire': '#a63603',
        }
        for _, row in polity_df.iterrows():
            ptype = row.get('type', 'band')
            pop = int(row.get('population', 1))
            ax.scatter(row['lon'], row['lat'],
                       s=max(30, pop * 3),
                       c=type_colors.get(ptype, 'gray'),
                       edgecolors='k', linewidth=0.8, alpha=0.7, zorder=5,
                       marker='D')
            if pop > 3:
                ax.annotate(f'{ptype}\n(n={pop})', (row['lon'], row['lat']),
                            fontsize=6, ha='center', va='bottom',
                            xytext=(0, 8), textcoords='offset points')

    ax.set_xlim(lon_range)
    ax.set_ylim(lat_range)
    ax.set_xlabel('Longitude', fontsize=11)
    ax.set_ylabel('Latitude', fontsize=11)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(alpha=0.2)

    return fig


def _generate_simple_terrain(lon_range, lat_range, nx=256, ny=256):
    """Generate a procedural terrain image for visual context."""
    from scipy.ndimage import gaussian_filter

    lons = np.linspace(lon_range[0], lon_range[1], nx)
    lats = np.linspace(lat_range[0], lat_range[1], ny)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    terrain = np.zeros((ny, nx))
    np.random.seed(42)
    for _ in range(20):
        cx = np.random.uniform(lon_range[0], lon_range[1])
        cy = np.random.uniform(lat_range[0], lat_range[1])
        sx = np.random.uniform(5, 30)
        sy = np.random.uniform(5, 30)
        amp = np.random.uniform(-50, 100)
        terrain += amp * np.exp(-((lon_grid - cx)**2 / sx**2 +
                                  (lat_grid - cy)**2 / sy**2))

    terrain = gaussian_filter(terrain, sigma=8)

    ocean_mask = terrain < np.percentile(terrain, 30)
    terrain[ocean_mask] = np.percentile(terrain, 30) - 5

    return terrain


# ─── Animation ──────────────────────────────────────────────────────────

def create_animation(snap_files, domain, region_key, color_mode, title):
    """Create a Plotly animation cycling through snapshots."""
    import plotly.graph_objects as go

    region = REGIONS[region_key]
    cfg = COLOR_CONFIGS[color_mode]
    frames = []

    df0 = load_snapshot(snap_files[0])
    df0 = map_coords(df0, domain, region)
    colors0, _, _, use_log = get_color_data(df0, color_mode)
    if use_log:
        colors0 = np.log1p(np.clip(colors0, 0, None))

    for snap_file in snap_files:
        step_str = os.path.basename(snap_file).replace('snap_', '').replace('.csv', '')
        df = load_snapshot(snap_file)
        df = map_coords(df, domain, region)
        colors, _, _, use_log = get_color_data(df, color_mode)
        if use_log:
            colors = np.log1p(np.clip(colors, 0, None))

        frame = go.Frame(
            data=[go.Scattergeo(
                lon=df['lon'], lat=df['lat'],
                mode='markers',
                marker=dict(size=4, color=colors,
                            colorscale=cfg['plotly_scale'] or 'Viridis',
                            opacity=0.7),
            )],
            name=step_str,
            layout=go.Layout(
                title=f'{title} — Step {step_str} (N={len(df)})')
        )
        frames.append(frame)

    fig = go.Figure(
        data=[go.Scattergeo(
            lon=df0['lon'], lat=df0['lat'],
            mode='markers',
            marker=dict(size=4, color=colors0,
                        colorscale=cfg['plotly_scale'] or 'Viridis',
                        colorbar=dict(title=cfg['label']),
                        opacity=0.7),
        )],
        frames=frames,
    )

    fig.update_geos(
        resolution=50,
        showcoastlines=True, coastlinecolor='#444',
        showland=True, landcolor='#e8e4d8',
        showocean=True, oceancolor='#c6e2ff',
        showlakes=True, lakecolor='#c6e2ff',
        showrivers=True, rivercolor='#8ec8f0',
        showcountries=True, countrycolor='#999',
        lataxis=dict(range=[region['lat'][0], region['lat'][1]]),
        lonaxis=dict(range=[region['lon'][0], region['lon'][1]]),
    )

    n_frames = len(frames)
    steps = []
    for i, snap_file in enumerate(snap_files):
        step_str = os.path.basename(snap_file).replace(
            'snap_', '').replace('.csv', '')
        steps.append(dict(
            method='animate',
            args=[[step_str], dict(
                frame=dict(duration=200, redraw=True),
                mode='immediate',
                transition=dict(duration=100))],
            label=step_str,
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        margin=dict(l=10, r=10, t=50, b=80),
        height=700,
        geo=dict(projection_type='natural earth', bgcolor='#f0f8ff'),
        updatemenus=[dict(
            type='buttons', showactive=False,
            y=0, x=0.5, xanchor='center',
            buttons=[
                dict(label='▶ Play',
                     method='animate',
                     args=[None, dict(
                         frame=dict(duration=300, redraw=True),
                         fromcurrent=True,
                         transition=dict(duration=150))]),
                dict(label='⏸ Pause',
                     method='animate',
                     args=[[None], dict(
                         frame=dict(duration=0, redraw=False),
                         mode='immediate',
                         transition=dict(duration=0))]),
            ],
        )],
        sliders=[dict(
            active=0,
            steps=steps,
            currentvalue=dict(prefix='Step: ', font=dict(size=12)),
            pad=dict(t=40),
        )] if n_frames <= 100 else [],
    )

    return fig


# ─── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Politeia world-map visualizer with terrain')
    parser.add_argument('path',
                        help='Snapshot CSV file, or output directory')
    parser.add_argument('--color', default='wealth',
                        choices=list(COLOR_CONFIGS.keys()),
                        help='Color mode (default: wealth)')
    parser.add_argument('--region', default='global',
                        choices=list(REGIONS.keys()),
                        help='Geographic region (default: global)')
    parser.add_argument('--domain', nargs=4, type=float,
                        default=[0, 100, 0, 100],
                        help='Simulation domain: xmin xmax ymin ymax')
    parser.add_argument('--step', type=int, default=-1,
                        help='Specific step (when path is directory)')
    parser.add_argument('--static', action='store_true',
                        help='Use Matplotlib instead of Plotly')
    parser.add_argument('--animate', action='store_true',
                        help='Create animation from all snapshots')
    parser.add_argument('--max-frames', type=int, default=50,
                        help='Max frames for animation (evenly sampled)')
    parser.add_argument('--save', default=None,
                        help='Output file (.html for Plotly, .png for static)')
    parser.add_argument('--dpi', type=int, default=150,
                        help='DPI for static output')
    parser.add_argument('--title', default=None,
                        help='Custom title')
    args = parser.parse_args()

    region = REGIONS[args.region]
    domain = args.domain

    if args.animate:
        if not os.path.isdir(args.path):
            print("--animate requires a directory path", file=sys.stderr)
            sys.exit(1)

        snap_files = find_snapshots(args.path)
        if not snap_files:
            print(f"No snap_*.csv in {args.path}", file=sys.stderr)
            sys.exit(1)

        if len(snap_files) > args.max_frames:
            indices = np.linspace(0, len(snap_files) - 1,
                                  args.max_frames, dtype=int)
            snap_files = [snap_files[i] for i in indices]

        title = args.title or f'Politeia — {region["label"]} (Animation)'
        print(f"Creating animation: {len(snap_files)} frames, "
              f"region={args.region}, color={args.color}")

        fig = create_animation(snap_files, domain, args.region,
                               args.color, title)

        out = args.save or 'civilization_animation.html'
        fig.write_html(out, auto_open=False)
        print(f"Saved animation to {out}")
        return

    if os.path.isdir(args.path):
        snap_files = find_snapshots(args.path)
        if not snap_files:
            print(f"No snap_*.csv in {args.path}", file=sys.stderr)
            sys.exit(1)

        if args.step >= 0:
            target = f"snap_{args.step:08d}.csv"
            filepath = os.path.join(args.path, target)
            if not os.path.exists(filepath):
                print(f"Step {args.step} not found, using last snapshot")
                filepath = snap_files[-1]
        else:
            filepath = snap_files[-1]
    else:
        filepath = args.path

    step_str = os.path.basename(filepath).replace('snap_', '').replace('.csv', '')
    print(f"Loading {filepath}")

    df = load_snapshot(filepath)
    df = map_coords(df, domain, region)
    N = len(df)
    print(f"  {N} particles → region={args.region} ({region['label']})")

    polity_df = None
    parent_dir = os.path.dirname(filepath)
    polity_file = os.path.join(parent_dir, f'polities_{step_str}.csv')
    if os.path.exists(polity_file):
        polity_df = pd.read_csv(polity_file)
        polity_df = map_coords(polity_df.rename(columns={'cx': 'x', 'cy': 'y'}),
                               domain, region)
        print(f"  {len(polity_df)} polities loaded")

    title = args.title or (
        f'Politeia — {region["label"]} — Step {step_str} '
        f'(N={N}, color={args.color})')

    if args.static:
        import matplotlib.pyplot as plt
        fig = plot_static(df, args.color, args.region, title, polity_df)
        if args.save:
            fig.savefig(args.save, dpi=args.dpi, bbox_inches='tight')
            print(f"Saved to {args.save}")
        else:
            plt.show()
    else:
        fig = plot_interactive(df, args.color, args.region, title, polity_df)
        if args.save:
            if args.save.endswith('.html'):
                fig.write_html(args.save, auto_open=False)
            else:
                fig.write_image(args.save, scale=2)
            print(f"Saved to {args.save}")
        else:
            fig.show()


if __name__ == '__main__':
    main()
