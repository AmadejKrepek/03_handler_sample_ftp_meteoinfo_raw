import os
import argparse
from glob import glob
from netCDF4 import Dataset
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as crs
import cartopy.feature as cfeature
from wrf import getvar, latlon_coords, get_cartopy, to_np
from datetime import datetime
from zoneinfo import ZoneInfo

# === Parse CLI arguments ===
parser = argparse.ArgumentParser(description="Plot accumulated precipitation from WRF output")
parser.add_argument("--data_dir", required=True, help="Path to WRF output files (e.g. wrfout_d01_*)")
parser.add_argument("--output_dir", default="output", help="Where to save the plots")
args = parser.parse_args()

data_dir = os.path.abspath(args.data_dir)
output_dir = os.path.abspath(args.output_dir)
os.makedirs(output_dir, exist_ok=True)

# === Load WRF files ===
wrf_files = sorted(glob(os.path.join(data_dir, "wrfout*_d01_*")))
if not wrf_files:
    raise FileNotFoundError("No WRF files found.")

# === Custom precipitation colormap and levels ===
precipitation_colors = [
    "#ffffff", "#e3f0ff", "#cce1ff", "#8fbdff", "#529bdd", "#2876b5", "#208e91",
    "#04aa8a", "#2cc469", "#98d344", "#d7e205", "#ffea92", "#ffd03b", "#ff9124",
    "#e55028", "#ce2715", "#ad0800", "#aa3c90", "#cc52c6", "#d87fdd", "#e89ef2",
    "#f2bdff", "#f5d9fc"
]
precip_levels = [0.1, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 10,
                 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 150]

cmap = mcolors.ListedColormap(precipitation_colors)
norm = mcolors.BoundaryNorm(precip_levels, ncolors=len(precipitation_colors))

# === Initialization ===
prev_total_precip = None
prev_time_str = None
proj, lats, lons = None, None, None

# === Loop through WRF files
for i, f in enumerate(wrf_files):
    ncfile = Dataset(f, mmap=True)

    # === Time handling
    time_val = getvar(ncfile, "times").values
    raw = str(time_val[0]) if isinstance(time_val, np.ndarray) else str(time_val)
    base = raw.split(".", 1)[0]
    dt_utc = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
    dt_local = dt_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Ljubljana"))
    time_str = dt_local.strftime("%Y%m%d_%H%M")
    time_label = dt_local.strftime("%-d. %-m. %Y ob %H:%M")

    # === Total precipitation
    rainc = getvar(ncfile, "RAINC")
    rainnc = getvar(ncfile, "RAINNC")
    total_precip = (rainc + rainnc).copy()

    # Get projection and grid once
    if proj is None:
        proj = get_cartopy(rainc)
        lats, lons = latlon_coords(rainc)

    # === Accumulation logic (starting from 2nd timestep)
    if prev_total_precip is not None:
        accum_precip = (total_precip - prev_total_precip).copy()
        accum_precip = accum_precip.where(accum_precip >= 0)

        print(f"🕒 {prev_time_str} → {time_label}")
        print(f"   ▶ Total now:  max={np.nanmax(to_np(total_precip)):.2f} mm")
        print(f"   ▶ Prev total: max={np.nanmax(to_np(prev_total_precip)):.2f} mm")
        print(f"   ▶ Accumulated: max={np.nanmax(to_np(accum_precip)):.2f} mm")

        fig = plt.figure(figsize=(10, 8))
        ax = plt.axes(projection=proj)
        ax.set_extent([12.4, 16.45, 44.7, 47.2], crs=crs.PlateCarree())
        ax.coastlines('50m', linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.5)
        ax.add_feature(cfeature.STATES, linewidth=0.5)

        mesh = ax.pcolormesh(to_np(lons), to_np(lats), to_np(accum_precip),
                             cmap=cmap, norm=norm, transform=crs.PlateCarree())

        cbar = plt.colorbar(mesh, ax=ax, orientation='vertical',
                            pad=0.02, shrink=0.7, aspect=30, ticks=precip_levels)
        cbar.set_label('Urna akumulacija padavin (mm)')
        ax.set_title(f'WRF – Akumulirane padavine\n{prev_time_str} → {time_label}')

        outfile = os.path.join(output_dir, f"rain_accum_{time_str}.png")
        plt.savefig(outfile, bbox_inches='tight', pad_inches=0.2)
        plt.close(fig)

    # Store current for next frame
    prev_total_precip = total_precip
    prev_time_str = time_label
    ncfile.close()

print(f"✅ Accumulated rainfall plots generated in: {output_dir}")
