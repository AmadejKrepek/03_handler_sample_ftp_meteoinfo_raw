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
from matplotlib.cm import ScalarMappable
from datetime import datetime
from scipy.ndimage import zoom
from zoneinfo import ZoneInfo
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib import image as mpimg

# === CLI Arguments ===
parser = argparse.ArgumentParser(description="Plot maximum reflectivity (mdbz) from WRF output")
parser.add_argument("--data_dir", required=True, help="Path to WRF output files (e.g., wrfout_d01_*)")
parser.add_argument("--output_dir", default="output_mdbz", help="Directory to save output images")
parser.add_argument("--logo_path", default="logo_512_39.webp", help="Path to logo image (optional)")
args = parser.parse_args()

data_dir = os.path.abspath(args.data_dir)
output_dir = os.path.join(os.path.abspath(args.output_dir), "mdbz")
logo_path = args.logo_path
os.makedirs(output_dir, exist_ok=True)

# === Color Setup ===
reflectivity_bins = [
    (0, 15), (15, 18), (18, 21), (21, 24), (24, 27),
    (27, 30), (30, 33), (33, 36), (36, 39), (39, 42),
    (42, 45), (45, 48), (48, 51), (51, 54), (54, 57),
    (57, 60), (60, 63), (63, 66), (66, 70)
]

colors = [
    '#0E6B9D', '#068093', '#089E94', '#05C1A0', '#04D883',
    '#5AE65A', '#A9F848', '#F0FF50', '#FFEB19', '#FFC71F',
    '#FF9F32', '#FF7D4A', '#FF6262', '#FF8FC4', '#E3D9FF',
    '#C4B5FD', '#A78BFA', '#8B5CF6', '#7C3AED',
]

light_gray = "#626262"
bin_edges = [low for (low, _) in reflectivity_bins] + [reflectivity_bins[-1][1]]
cmap_full = ListedColormap([light_gray] + colors)
norm_full = BoundaryNorm(bin_edges, ncolors=len(colors))
reflectivity_ticks = list(range(15, 69, 3))
cmap_trimmed = ListedColormap(colors)
norm_trimmed = BoundaryNorm(bin_edges[1:], len(colors))

# === Bounding Box ===
LAT_MIN, LAT_MAX = 44.7, 47.2
LON_MIN, LON_MAX = 12.4, 16.45

def create_logo(path):
    try:
        logo = mpimg.imread(path)
        desired_width, desired_height = 330, 30
        scale = min(desired_width / logo.shape[1], desired_height / logo.shape[0])
        return zoom(logo, (scale, scale, 1))
    except Exception as e:
        print(f"Logo load failed: {e}")
        return None

def plot_one_file(filepath):
    try:
        with Dataset(filepath) as ncfile:
            mdbz = getvar(ncfile, "mdbz")
            lats, lons = latlon_coords(mdbz)
            proj = get_cartopy(mdbz)

            time_var = getvar(ncfile, "times").values
            time_str = str(time_var[0]) if isinstance(time_var, (np.ndarray, list)) else str(time_var)

            if time_str.startswith("1") and time_str.isdigit():
                ts = int(time_str) / 1e9
                model_run_utc = datetime.utcfromtimestamp(ts)
            elif "T" in time_str:
                model_run_utc = datetime.strptime(time_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            else:
                raise ValueError(f"Unrecognized time format: {time_str}")

            # === Zoom and interpolate ===
            factor = 4.0
            mdbz_zoomed = zoom(to_np(mdbz), factor, order=1)
            lat_zoomed = zoom(to_np(lats), factor, order=1)
            lon_zoomed = zoom(to_np(lons), factor, order=1)

            # === Time formatting ===
            dt_local = model_run_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Ljubljana"))
            time_str = dt_local.strftime("%Y%m%d_%H%M")
            time_hr = dt_local.strftime("%-d. %-m. %Y ob %H:%M")

            # === Plotting ===
            fig, ax = plt.subplots(figsize=(12, 12), subplot_kw={'projection': proj})
            fig.set_facecolor('#333333')
            ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=crs.PlateCarree())
            ax.coastlines(resolution='10m', linewidth=0.4, color='white')
            ax.add_feature(cfeature.BORDERS.with_scale('10m'), linewidth=1.0, edgecolor='white')

            mesh = ax.pcolormesh(lon_zoomed, lat_zoomed, mdbz_zoomed,
                                 cmap=cmap_full, norm=norm_full,
                                 transform=crs.PlateCarree(), antialiased=False)

            sm = ScalarMappable(norm=norm_trimmed, cmap=cmap_trimmed)
            sm.set_array([])
            cbar_ax = fig.add_axes([0.13, 0.11, 0.77, 0.025])
            cbar = plt.colorbar(sm, cax=cbar_ax, orientation='horizontal', ticks=reflectivity_ticks)
            cbar.set_label("radarska odbojnost [dBZ]", color='white', labelpad=8)
            cbar.ax.set_xticklabels([f"{x:.0f}" for x in reflectivity_ticks], color='white')
            cbar.outline.set_edgecolor('none')

            logo_resized = create_logo(logo_path)
            if logo_resized is not None:
                fig.figimage(logo_resized, xo=32, yo=1551, zorder=20)

            ax.text(0.5, 1.01, time_hr, transform=ax.transAxes, fontsize=13, color='white', weight='bold', ha='center')
            ax.text(1.0, 1.01, "maksimalna radarska odbojnost", transform=ax.transAxes, fontsize=13, color='white', weight='bold', ha='right')
            ax.text(0.01, -0.12, f"Zagon modela: {dt_local.strftime('%Y-%m-%d %H:%M UTC')}", transform=ax.transAxes, fontsize=10, ha='left', va='top', color='white', weight='bold')
            ax.text(0.99, -0.12, "Vir podatkov: TempoQuest - ICON-D2", transform=ax.transAxes, fontsize=10, ha='right', va='top', color='white', weight='bold')

            output_path = os.path.join(output_dir, f"max_dbz_{time_str}.png")
            plt.savefig(output_path, bbox_inches='tight', dpi=160, pad_inches=0.15)
            plt.close()

    except Exception as e:
        print(f"❌ Failed to process {filepath}: {e}")

# === Load and process files ===
wrf_files = sorted(glob(os.path.join(data_dir, "wrfout*_d01_*")))
if not wrf_files:
    raise FileNotFoundError("No WRF files found.")

print(f"🚀 Starting rendering of {len(wrf_files)} files...")

for filepath in wrf_files:
    plot_one_file(filepath)

print(f"✅ Export complete: {len(wrf_files)} reflectivity plots → {output_dir}")
