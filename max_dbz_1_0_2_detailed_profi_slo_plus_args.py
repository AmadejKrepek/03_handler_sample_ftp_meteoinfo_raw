import os
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
from scipy.ndimage import gaussian_filter, zoom
from zoneinfo import ZoneInfo
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib import image as mpimg
import argparse


# === Custom Reflectivity Bins and Colors ===
reflectivity_bins = [(2,4),(4,6),(6,7),(7,8),(8,9),(9,10),(10,11),(11,12),(12,13),(13,14),(14,15),(15,16),
                     (16,17),(17,18),(18,19),(19,20),(20,21),(21,22),(22,23),(23,24),(24,25),(25,26),
                     (26,27),(27,28),(28,29),(29,30),(30,31),(31,32),(32,33),(33,34),(34,35),(35,36),
                     (36,37),(37,38),(38,39),(39,40),(40,41),(41,42),(42,43),(43,44),(44,45),(45,46),
                     (46,47),(47,48),(48,49),(49,50),(50,51),(51,52),(52,53),(53,54),(54,55),(55,56),
                     (56,57),(57,58),(58,59),(59,60),(60,61),(61,62),(62,63),(63,64),(64,65),(65,66),
                     (66,67),(67,68),(68,69),(69,70)]

colors = ['#626262','#656565','#507D80','#3A979E','#29ACB6','#14C7D4','#00E2EE','#00CEF0','#01BEF2','#01AFF4',
          '#01A0F6','#018CF6','#0178F6','#0150F6','#0028F6','#0000F6','#00FF00','#00F700','#00EF00','#00E700',
          '#00DF00','#00D700','#00CF00','#00C700','#00BF00','#00B700','#00AF00','#00A700','#009F00','#009700',
          '#008F00','#FFFF00','#F9F000','#F3E100','#EDD200','#E7C300','#E7B400','#EDA400','#F39400','#F98400',
          '#FF7400','#FF6400','#FF5000','#FF3C00','#FF2800','#FF1400','#FF0000','#F50000','#EB0000','#E10000',
          '#D70000','#CD0000','#C20000','#B70000','#AB0000','#9E0000','#FFC8FF','#F4B4F4','#E8A0E8','#DD8CDD',
          '#D178D1','#C664C6','#BA50BA','#AF3CAF','#A328A3','#981498',"#E0E0E0"]

# Light gray RGBA for background <2 dBZ
light_gray = "#626262"  # You can also use (0.9, 0.9, 0.9, 1.0)

# Full bin edges: include <2 dBZ bin
bin_edges = [0] + [low for (low, _) in reflectivity_bins] + [reflectivity_bins[-1][1]]  # [0, 2, 4, ..., 70]

# Full colormap: light gray + reflectivity colors
cmap_full = ListedColormap([light_gray] + colors)

# BoundaryNorm that matches each bin range
norm_full = BoundaryNorm(bin_edges, ncolors=len(cmap_full.colors), extend='max')

# Optional: trimmed colormap for legend without light gray
cmap_trimmed = ListedColormap(colors)
norm_trimmed = BoundaryNorm(bin_edges[1:], len(colors))

# Optional: colorbar ticks
reflectivity_ticks = list(range(10, 75, 5))

def createLogo(path):
    try:
        logo = mpimg.imread(path)
        desired_width, desired_height = 330, 30
        scale_w = desired_width / logo.shape[1]
        scale_h = desired_height / logo.shape[0]
        scale = min(scale_w, scale_h)
        return zoom(logo, (scale, scale, 1))
    except Exception as e:
        print(f"Logo load failed: {e}")
        return None

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

# === Load WRF Files ===
wrf_files = sorted(glob(os.path.join(data_dir, "wrfout*_d01_*")))
if not wrf_files:
    raise FileNotFoundError("No WRF files found.")

# === Projection and model run time from first file ===
first_nc = Dataset(wrf_files[0], mmap=True)
proj_var = getvar(first_nc, "HGT")
base_lats, base_lons = latlon_coords(proj_var)
base_proj = get_cartopy(proj_var)
first_time_val = getvar(first_nc, "times").values
first_base = str(first_time_val[0] if isinstance(first_time_val, (np.ndarray, list)) else first_time_val).split(".", 1)[0]
model_run_utc = datetime.strptime(first_base, "%Y-%m-%dT%H:%M:%S")
first_nc.close()

# === Bounding box ===
LAT_MIN, LAT_MAX = 44.7, 47.2
LON_MIN, LON_MAX = 12.4, 16.45

# === Plotting loop ===
for f in wrf_files:
    ncfile = Dataset(f, mmap=True)
    time_val = getvar(ncfile, "times").values
    base = str(time_val[0] if isinstance(time_val, (np.ndarray, list)) else time_val).split(".", 1)[0]
    dt_utc = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
    dt_local = dt_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Ljubljana"))
    time_str = dt_local.strftime("%Y%m%d_%H%M")
    time_hr = dt_local.strftime("%-d. %-m. %Y ob %H:%M")

    try:
        mdbz = getvar(ncfile, "mdbz")
    except:
        print(f"Skipping {f}: mdbz not found.")
        continue

    mdbz_np = to_np(mdbz)
    ncfile.close()

    mdbz_smooth = gaussian_filter(mdbz_np, sigma=0.8)
    factor = 3
    mdbz_zoomed = zoom(mdbz_smooth, factor)
    lat_zoomed = zoom(to_np(base_lats), factor)
    lon_zoomed = zoom(to_np(base_lons), factor)

    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw={'projection': base_proj})
    ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=crs.PlateCarree())
    fig.set_facecolor('#333333')

    ax.coastlines(resolution='10m', linewidth=0.4, color='white')
    ax.add_feature(cfeature.BORDERS.with_scale('10m'), linewidth=1.0, edgecolor='white')
    #ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=0.7, edgecolor='white')

    mesh = ax.pcolormesh(lon_zoomed, lat_zoomed, mdbz_zoomed,
                         cmap=cmap_full, norm=norm_full, transform=crs.PlateCarree())

    sm = ScalarMappable(norm=norm_trimmed, cmap=cmap_trimmed)
    sm.set_array([])
    cbar_ax = fig.add_axes([0.13, 0.11, 0.77, 0.025])
    cbar = plt.colorbar(sm, cax=cbar_ax, orientation='horizontal',
                        ticks=reflectivity_ticks, extend='max')
    cbar.set_label("Odbita radarska jakost (dBZ)", color='white', labelpad=8, weight='bold')
    cbar.ax.set_xticklabels([f"{x:.0f}" for x in reflectivity_ticks], color='white', weight='bold')
    cbar.outline.set_edgecolor('none')

    logo_resized = createLogo('logo_512_39.webp')
    if logo_resized is not None:
        fig.figimage(logo_resized, xo=25, yo=1551, zorder=20)

    ax.text(0.5, 1.01, time_hr,
            transform=ax.transAxes, fontsize=13, color='white', weight='bold', ha='center')
    ax.text(1.0, 1.01, "Največja reflektivnost (dBZ)",
            transform=ax.transAxes, fontsize=13, color='white', weight='bold', ha='right')
    ax.text(0.01, -0.12, f"Model run: {model_run_utc.strftime('%Y-%m-%d %H:%M UTC')}",
            transform=ax.transAxes, fontsize=10, ha='left', va='top', color='white', weight='bold')
    ax.text(0.99, -0.12, "Vir podatkov: TempoQuest - ICON-D2",
            transform=ax.transAxes, fontsize=10, ha='right', va='top', color='white', weight='bold')

    plt.savefig(os.path.join(output_dir, f"max_dbz_{time_str}.png"), bbox_inches='tight', dpi=160, pad_inches=0.15)
    plt.close()

print(f"✅ Export complete: {len(wrf_files)} reflectivity plots → {output_dir}")
