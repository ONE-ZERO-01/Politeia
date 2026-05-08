#!/usr/bin/env python3
"""
Download and convert real-world elevation data to Politeia .asc format.

Uses ETOPO1 global relief data (public domain, NOAA) via HTTP to generate
ESRI ASCII Grid files that Politeia's TerrainGrid::load_ascii() can read.

For regions without network access, can also generate procedural terrain
that approximates real geography (mountain ranges, river valleys, plains).

Usage:
    # Download ETOPO1 and extract China region as .asc
    python fetch_terrain.py --region china --output terrain_china.asc

    # Generate procedural approximation (no download needed)
    python fetch_terrain.py --region china --procedural --output terrain_china.asc

    # Custom bounding box
    python fetch_terrain.py --bbox 73 135 18 54 --resolution 256 --output custom.asc

    # List available regions
    python fetch_terrain.py --list-regions
"""

import argparse
import os
import sys
import struct

import numpy as np

REGIONS = {
    'global':        {'lat': (-60, 75), 'lon': (-180, 180)},
    'china':         {'lat': (18, 54), 'lon': (73, 135)},
    'europe':        {'lat': (35, 72), 'lon': (-12, 45)},
    'mediterranean': {'lat': (28, 48), 'lon': (-10, 42)},
    'mesopotamia':   {'lat': (28, 42), 'lon': (38, 55)},
    'nile':          {'lat': (22, 32), 'lon': (28, 36)},
    'indus':         {'lat': (22, 36), 'lon': (64, 78)},
    'eastasia':      {'lat': (15, 55), 'lon': (70, 145)},
    'oldworld':      {'lat': (-10, 60), 'lon': (-20, 140)},
}


# ─── ETOPO download ────────────────────────────────────────────────────

def download_etopo_region(lon_range, lat_range, resolution=256):
    """Download ETOPO1 elevation data from NOAA for a geographic region.

    Uses the NOAA ERDDAP service which provides ETOPO data via HTTP.
    Returns a 2D numpy array of elevations in meters.
    """
    import urllib.request
    import json

    lon_min, lon_max = lon_range
    lat_min, lat_max = lat_range

    stride_lon = max(1, int(10800 * (lon_max - lon_min) / 360 / resolution))
    stride_lat = max(1, int(5400 * (lat_max - lat_min) / 180 / resolution))

    url = (
        f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/etopo180.json?"
        f"altitude[({lat_min}):({stride_lat}):({lat_max})]"
        f"[({lon_min}):({stride_lon}):({lon_max})]"
    )

    print(f"Downloading ETOPO1 data...")
    print(f"  Region: lon=[{lon_min},{lon_max}] lat=[{lat_min},{lat_max}]")
    print(f"  URL: {url[:120]}...")

    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Politeia/1.0')
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())

        rows = data['table']['rows']
        lats = sorted(set(r[0] for r in rows))
        lons = sorted(set(r[1] for r in rows))

        ny, nx = len(lats), len(lons)
        terrain = np.zeros((ny, nx))

        lat_idx = {lat: i for i, lat in enumerate(lats)}
        lon_idx = {lon: i for i, lon in enumerate(lons)}

        for row in rows:
            lat, lon, alt = row[0], row[1], row[2]
            if alt is not None:
                terrain[lat_idx[lat], lon_idx[lon]] = alt
            else:
                terrain[lat_idx[lat], lon_idx[lon]] = 0.0

        print(f"  Downloaded: {nx}×{ny} grid, "
              f"elevation range [{terrain.min():.0f}, {terrain.max():.0f}] m")
        return terrain, (lon_min, lon_max), (lat_min, lat_max)

    except Exception as e:
        print(f"  Download failed: {e}", file=sys.stderr)
        print("  Falling back to procedural terrain", file=sys.stderr)
        return None, None, None


# ─── Procedural terrain ────────────────────────────────────────────────

def generate_procedural_terrain(lon_range, lat_range, nx=256, ny=256):
    """Generate procedural terrain approximating real geography."""
    from scipy.ndimage import gaussian_filter

    lons = np.linspace(lon_range[0], lon_range[1], nx)
    lats = np.linspace(lat_range[0], lat_range[1], ny)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    terrain = np.zeros((ny, nx))

    lon_norm = (lon_grid - lon_range[0]) / (lon_range[1] - lon_range[0])
    lat_norm = (lat_grid - lat_range[0]) / (lat_range[1] - lat_range[0])

    np.random.seed(12345)

    for _ in range(30):
        cx = np.random.uniform(0, 1)
        cy = np.random.uniform(0, 1)
        sx = np.random.uniform(0.03, 0.15)
        sy = np.random.uniform(0.03, 0.15)
        amp = np.random.uniform(-2000, 4000)
        terrain += amp * np.exp(-((lon_norm - cx)**2 / sx**2 +
                                  (lat_norm - cy)**2 / sy**2))

    for _ in range(5):
        angle = np.random.uniform(0, np.pi)
        offset = np.random.uniform(0.2, 0.8)
        width = np.random.uniform(0.02, 0.06)
        amp = np.random.uniform(1000, 5000)
        dist = np.abs(np.cos(angle) * (lon_norm - 0.5) +
                       np.sin(angle) * (lat_norm - 0.5) - (offset - 0.5))
        terrain += amp * np.exp(-dist**2 / width**2)

    terrain = gaussian_filter(terrain, sigma=3)

    edge_x = np.minimum(lon_norm, 1 - lon_norm)
    edge_y = np.minimum(lat_norm, 1 - lat_norm)
    edge = np.minimum(edge_x, edge_y)
    ocean = np.where(edge < 0.05,
                     -200 * np.exp(-(edge / 0.02)**2), 0)
    terrain += ocean

    terrain = np.clip(terrain, -500, 8000)

    print(f"  Generated procedural terrain: {nx}×{ny}, "
          f"range [{terrain.min():.0f}, {terrain.max():.0f}] m")
    return terrain


# ─── Terrain → Politeia potential ──────────────────────────────────────

def elevation_to_potential(terrain, scale=1.0, sea_level=0.0):
    """Convert elevation to Politeia potential energy.

    Low elevation (river valleys, plains) → negative potential (attractive)
    High elevation (mountains) → positive potential (repulsive)
    Below sea level → very high potential (ocean barrier)
    """
    h_max = np.percentile(terrain[terrain > sea_level], 95) if \
        np.any(terrain > sea_level) else 1.0

    potential = np.zeros_like(terrain)

    land = terrain >= sea_level
    potential[land] = scale * (terrain[land] / h_max) * 100.0

    potential[~land] = scale * 200.0

    potential = -potential + scale * 100.0
    potential = potential - potential.max()

    return potential


# ─── ESRI ASCII Grid writer ────────────────────────────────────────────

def write_ascii_grid(filepath, data, xmin, ymin, cellsize, nodata=-9999):
    """Write a 2D array as ESRI ASCII Grid (.asc) for Politeia."""
    nrows, ncols = data.shape
    with open(filepath, 'w') as f:
        f.write(f"ncols {ncols}\n")
        f.write(f"nrows {nrows}\n")
        f.write(f"xllcorner {xmin}\n")
        f.write(f"yllcorner {ymin}\n")
        f.write(f"cellsize {cellsize}\n")
        f.write(f"NODATA_value {nodata}\n")

        for r in range(nrows - 1, -1, -1):
            row_str = ' '.join(f'{data[r, c]:.2f}' for c in range(ncols))
            f.write(row_str + '\n')

    print(f"  Written: {filepath} ({ncols}×{nrows}, "
          f"cellsize={cellsize:.6f})")


def write_binary_grid(filepath, data):
    """Write a 2D array as float64 binary for Politeia load_binary()."""
    with open(filepath, 'wb') as f:
        f.write(data.astype(np.float64).tobytes())
    print(f"  Written: {filepath} ({data.shape[1]}×{data.shape[0]}, binary)")


# ─── Config generator ──────────────────────────────────────────────────

def generate_terrain_config(region_key, asc_path, nrows, ncols,
                            xmin, ymin, cellsize, output_path):
    """Generate a .cfg snippet for using the terrain file."""
    region = REGIONS[region_key]
    xmax = xmin + ncols * cellsize
    ymax = ymin + nrows * cellsize

    cfg = f"""# Politeia terrain config for {region_key}
# Generated by fetch_terrain.py

# Domain matches terrain grid
domain_xmin = {xmin}
domain_xmax = {xmax:.6f}
domain_ymin = {ymin}
domain_ymax = {ymax:.6f}

# Terrain from file
terrain_file = {asc_path}
terrain_format = auto
terrain_scale = 1.0
terrain_grid_rows = {nrows}
terrain_grid_cols = {ncols}
"""
    with open(output_path, 'w') as f:
        f.write(cfg)
    print(f"  Config: {output_path}")


# ─── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Download/generate terrain data for Politeia')
    parser.add_argument('--region', default='china',
                        choices=list(REGIONS.keys()),
                        help='Geographic region')
    parser.add_argument('--bbox', nargs=4, type=float, default=None,
                        help='Custom bounding box: lon_min lon_max lat_min lat_max')
    parser.add_argument('--resolution', type=int, default=256,
                        help='Grid resolution (default: 256)')
    parser.add_argument('--output', default=None,
                        help='Output .asc file path')
    parser.add_argument('--binary', default=None,
                        help='Also write binary grid to this path')
    parser.add_argument('--config', default=None,
                        help='Generate .cfg file for Politeia')
    parser.add_argument('--procedural', action='store_true',
                        help='Use procedural terrain (no download)')
    parser.add_argument('--scale', type=float, default=1.0,
                        help='Potential energy scale factor')
    parser.add_argument('--list-regions', action='store_true',
                        help='List available regions and exit')
    parser.add_argument('--raw-elevation', action='store_true',
                        help='Write raw elevation instead of potential')
    args = parser.parse_args()

    if args.list_regions:
        print("Available regions:")
        for name, r in REGIONS.items():
            print(f"  {name:15s}  lon={r['lon']}  lat={r['lat']}")
        return

    if args.bbox:
        lon_range = (args.bbox[0], args.bbox[1])
        lat_range = (args.bbox[2], args.bbox[3])
        region_key = 'custom'
    else:
        r = REGIONS[args.region]
        lon_range = r['lon']
        lat_range = r['lat']
        region_key = args.region

    nx = args.resolution
    ny = int(nx * (lat_range[1] - lat_range[0]) /
             (lon_range[1] - lon_range[0]))
    ny = max(ny, 2)

    if args.procedural:
        terrain = generate_procedural_terrain(lon_range, lat_range, nx, ny)
    else:
        terrain, _, _ = download_etopo_region(lon_range, lat_range, nx)
        if terrain is None:
            terrain = generate_procedural_terrain(lon_range, lat_range, nx, ny)
        ny, nx = terrain.shape

    if args.raw_elevation:
        output_data = terrain
    else:
        output_data = elevation_to_potential(terrain, scale=args.scale)
        print(f"  Potential range: [{output_data.min():.1f}, "
              f"{output_data.max():.1f}]")

    cellsize_x = (lon_range[1] - lon_range[0]) / nx
    cellsize_y = (lat_range[1] - lat_range[0]) / ny
    cellsize = min(cellsize_x, cellsize_y)

    out_path = args.output or f'terrain_{region_key}.asc'
    write_ascii_grid(out_path, output_data,
                     xmin=lon_range[0], ymin=lat_range[0],
                     cellsize=cellsize)

    if args.binary:
        write_binary_grid(args.binary, output_data)

    cfg_path = args.config or out_path.replace('.asc', '.cfg')
    generate_terrain_config(
        region_key, out_path, ny, nx,
        lon_range[0], lat_range[0], cellsize, cfg_path)

    print(f"\nDone! To use in Politeia:")
    print(f"  ./politeia {cfg_path}")
    print(f"\nTo visualize on world map:")
    print(f"  python plot_worldmap.py output/ --region {region_key} "
          f"--domain {lon_range[0]} {lon_range[1]} "
          f"{lat_range[0]} {lat_range[1]}")


if __name__ == '__main__':
    main()
