#!/usr/bin/env python3
"""
Generate a river proximity field for Politeia.

This script focuses on the first implementation stage of RiverField:
procedural major-river proximity on a regular lon/lat grid, plus an
auto-generated cfg snippet.

Output format:
  - ESRI ASCII single band: river proximity in [0, 1]
  - optional raw float64 binary, row-major

Examples:
  python fetch_rivers.py --region global --output river_global.asc --cfg-snippet
  python fetch_rivers.py --region china --type china --resolution 256 --output river_china.asc
"""

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path

import numpy as np


REGIONS = {
    "global": {"lat": (-60, 75), "lon": (-180, 180)},
    "china": {"lat": (18, 54), "lon": (73, 135)},
    "europe": {"lat": (35, 72), "lon": (-12, 45)},
    "mesopotamia": {"lat": (28, 42), "lon": (38, 55)},
    "nile": {"lat": (20, 33), "lon": (28, 37)},
    "indus": {"lat": (22, 36), "lon": (64, 78)},
    "oldworld": {"lat": (-10, 60), "lon": (-20, 140)},
}


def river_templates(name: str):
    if name == "nile":
        return [[(31.2, 30.0), (31.0, 26.0), (31.5, 22.5)]]
    if name == "mesopotamia":
        return [
            [(40.5, 37.5), (42.0, 35.0), (43.5, 32.0), (46.0, 30.0)],
            [(44.5, 37.0), (45.0, 34.5), (46.0, 31.5), (46.5, 30.0)],
        ]
    if name == "china":
        return [
            [(96.0, 35.0), (103.0, 36.0), (110.0, 35.5), (118.0, 36.5)],
            [(98.0, 31.0), (107.0, 30.5), (116.0, 30.5), (121.0, 31.0)],
        ]
    if name == "europe":
        return [
            [(8.0, 47.0), (12.0, 48.0), (17.0, 48.0), (23.0, 45.0), (29.0, 45.0)],
            [(7.6, 47.6), (7.5, 50.0), (6.7, 51.7)],
        ]
    if name == "indus":
        return [[(73.0, 34.0), (72.0, 31.5), (68.5, 28.5), (67.5, 24.5)]]
    return [
        [(31.2, 30.0), (31.0, 26.0), (31.5, 22.5)],  # Nile
        [(40.5, 37.5), (42.0, 35.0), (43.5, 32.0), (46.0, 30.0)],  # Euphrates
        [(44.5, 37.0), (45.0, 34.5), (46.0, 31.5), (46.5, 30.0)],  # Tigris
        [(73.0, 34.0), (72.0, 31.5), (68.5, 28.5), (67.5, 24.5)],  # Indus
        [(96.0, 35.0), (103.0, 36.0), (110.0, 35.5), (118.0, 36.5)],  # Yellow
        [(98.0, 31.0), (107.0, 30.5), (116.0, 30.5), (121.0, 31.0)],  # Yangtze
    ]


def segment_distance_sq(px, py, ax, ay, bx, by):
    dx = bx - ax
    dy = by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-15:
        return (px - ax) ** 2 + (py - ay) ** 2
    t = ((px - ax) * dx + (py - ay) * dy) / l2
    t = max(0.0, min(1.0, t))
    qx = ax + t * dx
    qy = ay + t * dy
    return (px - qx) ** 2 + (py - qy) ** 2


def polyline_distance_sq(px, py, points):
    best = 1e18
    for i in range(1, len(points)):
        best = min(best, segment_distance_sq(px, py, *points[i - 1], *points[i]))
    return best


def generate_proximity(lon_range, lat_range, resolution, river_type):
    lon_min, lon_max = lon_range
    lat_min, lat_max = lat_range
    nx = resolution
    ny = max(2, int(nx * (lat_max - lat_min) / max(lon_max - lon_min, 1.0)))

    lons = np.linspace(lon_min, lon_max, nx)
    lats = np.linspace(lat_min, lat_max, ny)
    field = np.zeros((ny, nx), dtype=np.float64)

    lines = river_templates(river_type)
    sigma = max((lon_max - lon_min), (lat_max - lat_min)) / 40.0

    for r, lat in enumerate(lats):
        for c, lon in enumerate(lons):
            prox = 0.0
            for line in lines:
                d2 = polyline_distance_sq(lon, lat, line)
                prox = max(prox, math.exp(-d2 / (2.0 * sigma * sigma)))
            field[r, c] = max(0.0, min(1.0, prox))

    cellsize = min((lon_max - lon_min) / max(nx - 1, 1), (lat_max - lat_min) / max(ny - 1, 1))
    return field, lon_min, lat_min, cellsize


def write_ascii_grid(path: Path, data: np.ndarray, xmin: float, ymin: float, cellsize: float):
    ny, nx = data.shape
    with path.open("w") as f:
        f.write(f"ncols {nx}\n")
        f.write(f"nrows {ny}\n")
        f.write(f"xllcorner {xmin}\n")
        f.write(f"yllcorner {ymin}\n")
        f.write(f"cellsize {cellsize}\n")
        f.write("NODATA_value -9999\n")
        for r in range(ny - 1, -1, -1):
            f.write(" ".join(f"{data[r, c]:.6f}" for c in range(nx)) + "\n")


def write_binary_grid(path: Path, data: np.ndarray):
    with path.open("wb") as f:
        f.write(struct.pack(f"{data.size}d", *data.ravel()))


def write_cfg_snippet(path: Path, asc_path: Path, rows: int, cols: int):
    with path.open("w") as f:
        f.write("# RiverField config snippet\n")
        f.write("river_enabled = true\n")
        f.write("river_mode = file\n")
        f.write(f"river_file = {asc_path}\n")
        f.write("river_format = auto\n")
        f.write(f"river_grid_rows = {rows}\n")
        f.write(f"river_grid_cols = {cols}\n")
        f.write("river_resource_enabled = true\n")
        f.write("river_resource_strength = 1.0\n")
        f.write("river_resource_alpha = 1.0\n")
        f.write("river_capacity_enabled = true\n")
        f.write("river_capacity_strength = 1.0\n")
        f.write("river_capacity_beta = 1.0\n")
        f.write("river_exchange_enabled = true\n")
        f.write("river_exchange_strength = 0.5\n")
        f.write("river_tech_enabled = true\n")
        f.write("river_tech_strength = 0.5\n")
        f.write("river_plague_enabled = false\n")
        f.write("river_force_enabled = false\n")


def main():
    parser = argparse.ArgumentParser(description="Generate river proximity field for Politeia")
    parser.add_argument("--region", default="global", choices=sorted(REGIONS.keys()))
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("LON_MIN", "LON_MAX", "LAT_MIN", "LAT_MAX"))
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument("--type", default="major_rivers",
                        choices=["major_rivers", "nile", "mesopotamia", "china", "europe", "indus"])
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--binary", type=str, default=None)
    parser.add_argument("--cfg-snippet", action="store_true")
    parser.add_argument("--list-regions", action="store_true")
    args = parser.parse_args()

    if args.list_regions:
        for name, region in REGIONS.items():
            print(f"{name:12s} lon={region['lon']} lat={region['lat']}")
        return

    if args.bbox:
        lon_range = (args.bbox[0], args.bbox[1])
        lat_range = (args.bbox[2], args.bbox[3])
        region_name = "custom"
    else:
        region = REGIONS[args.region]
        lon_range = region["lon"]
        lat_range = region["lat"]
        region_name = args.region

    data, xmin, ymin, cellsize = generate_proximity(lon_range, lat_range, args.resolution, args.type)
    output = Path(args.output or f"river_{region_name}.asc")
    write_ascii_grid(output, data, xmin, ymin, cellsize)
    print(f"Wrote {output} ({data.shape[1]}x{data.shape[0]})")

    if args.binary:
        write_binary_grid(Path(args.binary), data)
        print(f"Wrote {args.binary}")

    if args.cfg_snippet:
        snippet = output.with_suffix(".cfg_snippet")
        write_cfg_snippet(snippet, output, data.shape[0], data.shape[1])
        print(f"Wrote {snippet}")


if __name__ == "__main__":
    main()
