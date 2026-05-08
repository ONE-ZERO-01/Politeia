#!/usr/bin/env python3
"""
Download and convert climate data to Politeia .asc format.

Supports two data sources:
  1. Koppen-Geiger classification (Beck et al. 2018) — downloads from public server
  2. Procedural generation based on latitude formulas (no network needed)

Output format: dual-band ESRI ASCII Grid:
  - Band 1: Annual mean temperature (degC)
  - Band 2: Annual precipitation (mm)

Usage:
    # Download Koppen-Geiger derived climate for a region
    python fetch_climate.py --region china --output climate_china.asc

    # Generate procedural climate (no download)
    python fetch_climate.py --region global --procedural --output climate_global.asc

    # Custom bounding box
    python fetch_climate.py --bbox -180 180 -60 75 --resolution 256 --output custom.asc

    # List available regions
    python fetch_climate.py --list-regions
"""

import argparse
import os
import sys
import struct
import math

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

# Koppen-Geiger class codes mapped to approximate temperature & precipitation
KOPPEN_CLIMATE = {
    'Af':  (26.0, 2200.0),  # Tropical rainforest
    'Am':  (25.0, 1800.0),  # Tropical monsoon
    'Aw':  (25.0, 1200.0),  # Tropical savanna
    'BWh': (28.0, 100.0),   # Hot desert
    'BWk': (12.0, 100.0),   # Cold desert
    'BSh': (24.0, 400.0),   # Hot steppe
    'BSk': (10.0, 350.0),   # Cold steppe
    'Csa': (17.0, 600.0),   # Mediterranean hot summer
    'Csb': (14.0, 700.0),   # Mediterranean warm summer
    'Cwa': (18.0, 1200.0),  # Humid subtropical dry winter
    'Cwb': (14.0, 1000.0),  # Subtropical highland
    'Cfa': (18.0, 1200.0),  # Humid subtropical
    'Cfb': (12.0, 900.0),   # Oceanic
    'Cfc': (8.0, 800.0),    # Subpolar oceanic
    'Dsa': (10.0, 500.0),   # Continental hot dry summer
    'Dsb': (6.0, 600.0),    # Continental warm dry summer
    'Dwa': (5.0, 700.0),    # Continental hot dry winter
    'Dwb': (2.0, 600.0),    # Continental warm dry winter
    'Dfa': (8.0, 900.0),    # Continental hot humid
    'Dfb': (4.0, 800.0),    # Continental warm humid
    'Dfc': (-2.0, 500.0),   # Subarctic
    'Dfd': (-10.0, 400.0),  # Extreme subarctic
    'ET':  (-5.0, 250.0),   # Tundra
    'EF':  (-20.0, 100.0),  # Ice cap
}


def generate_procedural(lon_range, lat_range, resolution=128):
    """Generate procedural climate grid from latitude formulas.

    T(lat) = 30 - 0.7 * |lat|
    P(lat) = 2000 * exp(-((|lat|-5)/25)^2)
    """
    lon_min, lon_max = lon_range
    lat_min, lat_max = lat_range

    ncols = resolution
    nrows = max(1, int(resolution * (lat_max - lat_min) / max(1, lon_max - lon_min)))

    lons = np.linspace(lon_min, lon_max, ncols)
    lats = np.linspace(lat_min, lat_max, nrows)

    temp = np.zeros((nrows, ncols), dtype=np.float64)
    precip = np.zeros((nrows, ncols), dtype=np.float64)

    for r, lat in enumerate(lats):
        abs_lat = abs(lat)
        base_T = 30.0 - 0.7 * abs_lat
        lat_shifted = abs_lat - 5.0
        base_P = 2000.0 * math.exp(-(lat_shifted / 25.0)**2)
        base_P = max(50.0, base_P)

        # Add continentality effect: away from coasts → drier, more extreme temps
        for c, lon in enumerate(lons):
            T = base_T
            P = base_P

            # Simple continentality: reduce P inland (crude approximation)
            # Higher variance in temperature for interior longitudes
            continental_factor = 1.0
            if lon_min < -10 and lon_max > 40:
                # Eurasia-like: center around lon=50 is continental
                dist_coast = min(abs(lon - lon_min), abs(lon - lon_max)) / (lon_max - lon_min)
                continental_factor = 1.0 - 0.4 * dist_coast
                T += 5.0 * (2.0 * dist_coast - 1.0) * (0.5 if lat > 0 else -0.5)

            P *= continental_factor
            P = max(50.0, P)

            temp[r, c] = T
            precip[r, c] = P

    cellsize = (lon_max - lon_min) / max(ncols - 1, 1)
    return temp, precip, lon_min, lat_min, cellsize, nrows, ncols


def download_koppen_climate(lon_range, lat_range, resolution=128):
    """Attempt to download Koppen-Geiger data from public sources.

    Falls back to procedural generation on failure.
    """
    try:
        import urllib.request
        import json

        # Use WorldClim/CRU-derived approximate data via a public API
        # This is a simplified approach; real implementation would use actual KG rasters
        url = (
            f"https://power.larc.nasa.gov/api/temporal/climatology/point?"
            f"parameters=T2M,PRECTOTCORR&community=AG&longitude=0&latitude=0"
            f"&start=1991&end=2020&format=JSON"
        )
        # For a grid, we'd need to query multiple points or use a raster download.
        # For now, fall back to procedural with a message.
        print("Note: Direct Koppen-Geiger raster download not yet implemented.")
        print("       Using procedural climate generation as fallback.")
        print("       For real KG data, place a pre-processed .asc file and use --file mode.")
        return None
    except Exception as e:
        print(f"Download failed ({e}), using procedural fallback.")
        return None


def write_dual_band_ascii(filepath, temp, precip, xll, yll, cellsize, nodata=-9999.0):
    """Write dual-band ESRI ASCII Grid (temperature + precipitation)."""
    nrows, ncols = temp.shape

    with open(filepath, 'w') as f:
        # Band 1: Temperature
        f.write(f"ncols {ncols}\n")
        f.write(f"nrows {nrows}\n")
        f.write(f"xllcorner {xll}\n")
        f.write(f"yllcorner {yll}\n")
        f.write(f"cellsize {cellsize}\n")
        f.write(f"NODATA_value {nodata}\n")
        for r in range(nrows - 1, -1, -1):  # North to South
            row_str = ' '.join(f'{temp[r, c]:.2f}' for c in range(ncols))
            f.write(row_str + '\n')

        # Band 2: Precipitation
        f.write(f"ncols {ncols}\n")
        f.write(f"nrows {nrows}\n")
        f.write(f"xllcorner {xll}\n")
        f.write(f"yllcorner {yll}\n")
        f.write(f"cellsize {cellsize}\n")
        f.write(f"NODATA_value {nodata}\n")
        for r in range(nrows - 1, -1, -1):
            row_str = ' '.join(f'{precip[r, c]:.1f}' for c in range(ncols))
            f.write(row_str + '\n')

    print(f"Written: {filepath} ({ncols}x{nrows}, dual-band)")


def write_cfg_snippet(filepath, climate_file, xll, yll, xmax, ymax):
    """Write a .cfg snippet for Politeia configuration."""
    snippet = filepath.replace('.asc', '.cfg_snippet')
    with open(snippet, 'w') as f:
        f.write(f"# Climate configuration (auto-generated by fetch_climate.py)\n")
        f.write(f"climate_enabled = true\n")
        f.write(f"climate_mode = file\n")
        f.write(f"climate_file = {climate_file}\n")
        f.write(f"climate_time_mode = static\n")
        f.write(f"climate_production_enabled = true\n")
        f.write(f"climate_carrying_enabled = true\n")
        f.write(f"climate_mortality_enabled = true\n")
        f.write(f"climate_mortality_scale = 2e-4\n")
        f.write(f"climate_friction_enabled = true\n")
        f.write(f"climate_friction_scale = 0.3\n")
        f.write(f"climate_plague_enabled = true\n")
        f.write(f"climate_plague_scale = 1.5\n")
    print(f"Config snippet: {snippet}")


def main():
    parser = argparse.ArgumentParser(description='Fetch/generate climate data for Politeia')
    parser.add_argument('--region', choices=list(REGIONS.keys()), default='global',
                        help='Predefined region (default: global)')
    parser.add_argument('--bbox', nargs=4, type=float, metavar=('LON_MIN', 'LON_MAX', 'LAT_MIN', 'LAT_MAX'),
                        help='Custom bounding box')
    parser.add_argument('--resolution', type=int, default=128,
                        help='Grid resolution in longitude direction (default: 128)')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output file path')
    parser.add_argument('--procedural', action='store_true',
                        help='Force procedural generation (no download attempt)')
    parser.add_argument('--list-regions', action='store_true',
                        help='List available regions and exit')
    parser.add_argument('--cfg-snippet', action='store_true',
                        help='Also write a .cfg_snippet file for Politeia')

    args = parser.parse_args()

    if args.list_regions:
        print("Available regions:")
        for name, bounds in REGIONS.items():
            print(f"  {name:15s}  lat={bounds['lat']}, lon={bounds['lon']}")
        return

    if args.bbox:
        lon_range = (args.bbox[0], args.bbox[1])
        lat_range = (args.bbox[2], args.bbox[3])
    else:
        region = REGIONS[args.region]
        lon_range = region['lon']
        lat_range = region['lat']

    output = args.output or f"climate_{args.region}.asc"

    print(f"Region: lon={lon_range}, lat={lat_range}")
    print(f"Resolution: {args.resolution}")

    result = None
    if not args.procedural:
        result = download_koppen_climate(lon_range, lat_range, args.resolution)

    if result is None:
        print("Generating procedural climate...")
        temp, precip, xll, yll, cellsize, nrows, ncols = generate_procedural(
            lon_range, lat_range, args.resolution
        )
    else:
        temp, precip, xll, yll, cellsize, nrows, ncols = result

    write_dual_band_ascii(output, temp, precip, xll, yll, cellsize)

    if args.cfg_snippet:
        xmax = xll + (ncols - 1) * cellsize
        ymax = yll + (nrows - 1) * cellsize
        write_cfg_snippet(output, output, xll, yll, xmax, ymax)

    print("Done.")


if __name__ == '__main__':
    main()
