import os
from glob import glob
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import ListedColormap, BoundaryNorm
from scipy.ndimage import zoom
import cartopy.crs as crs
import cartopy.feature as cfeature
from matplotlib import image as mpimg
from shapely.geometry import Point, Polygon

# Optional: Can be extended for other sources (e.g., NetCDF, PNG, GRIB)
from netCDF4 import Dataset
from wrf import getvar, latlon_coords, get_cartopy, to_np

REGIONS = {
    "slovenia_istria": {
        "lat_min": 44.7,
        "lat_max": 47.2,
        "lon_min": 12.4,
        "lon_max": 16.45,
        "logo_position": (32, 1551),
        "cbar_position": [0.13, 0.11, 0.77, 0.025],
        "label_padding": {
            "left": 0.06,
            "right": 0.3,
            "top": 0.07,
            "bottom": 0.06
        },
        "edge_threshold": {
            "lat": 0.20, #0.15
            "lon": 0.20 #0.25
        }
    },
    "slovenia": {
        "lat_min": 45.4,
        "lat_max": 47.2,
        "lon_min": 13.3,
        "lon_max": 16.45,
        "logo_position": (25, 1465),
        "cbar_position": [0.13, 0.13, 0.77, 0.025],
        "label_padding": {
            "left": 0.08,
            "right": 0.16,
            "top": 0.06,
            "bottom": 0.08
        },
        "edge_threshold": {
            "lat": 0.15,
            "lon": 0.25
        }
    },
    "slovenia_centered": {
        "lat_min": 45.18,
        "lat_max": 46.98,
        "lon_min": 13.3,
        "lon_max": 16.45,
        "logo_position": (25, 1465),
        "cbar_position": [0.13, 0.13, 0.77, 0.025],
        "label_padding": {
            "left": 0.08,
            "right": 0.16,
            "top": 0.015,
            "bottom": 0.08
        },
        "edge_threshold": {
            "lat": 0.15,
            "lon": 0.25
        }
    }
    # Add more regions here as needed
}

class DataSource:
    def __init__(self, filepath):
        self.filepath = filepath

    def open(self):
        raise NotImplementedError

    def get_data(self):
        raise NotImplementedError

    def get_latlon(self):
        raise NotImplementedError

    def get_projection(self):
        raise NotImplementedError

    def get_valid_time(self):
        raise NotImplementedError

    def get_model_run_time(self):
        raise NotImplementedError

class NetCDFWRFSource(DataSource):
    def __init__(self, filepath, variable_name):
        super().__init__(filepath)
        self.variable_name = variable_name
        self._data = None

    def open(self):
        self.ncfile = Dataset(self.filepath)

    def close(self):
        self.ncfile.close()

    def get_data(self):
        if self._data is None:
            self._data = getvar(self.ncfile, self.variable_name)
        return self._data

    def get_latlon(self):
        return latlon_coords(self.get_data())

    def get_projection(self):
        return get_cartopy(self.get_data())

    def get_valid_time(self):
        time_var = getvar(self.ncfile, "times").values
        time_str = str(time_var[0]) if isinstance(time_var, (np.ndarray, list)) else str(time_var)
        if "T" in time_str:
            dt = datetime.strptime(time_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
        else:
            dt = datetime.utcfromtimestamp(int(time_str) / 1e9)
        return dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Ljubljana"))

    def get_model_run_time(self):
        return self.get_valid_time()

class TemperatureWRFSource(NetCDFWRFSource):
    def get_data(self):
        kelvin = super().get_data()
        self._raw_data = kelvin
        return kelvin - 273.15

    def get_latlon(self):
        return latlon_coords(self._raw_data)

    def get_projection(self):
        return get_cartopy(self._raw_data)

class GridLabeler:
    def __init__(self, stride):
        self.stride = stride

    def annotate(self, ax, data, lats, lons, lat_min, lat_max, lon_min, lon_max, crs_proj, padding, threshold):
        if not self.stride:
            return

        pad_left = padding.get("left", 0.08)
        pad_right = padding.get("right", 0.08)
        pad_top = padding.get("top", 0.08)
        pad_bottom = padding.get("bottom", 0.08)

        polygon = Polygon([
            (lon_min - pad_left, lat_min - pad_bottom),
            (lon_max + pad_right, lat_min - pad_bottom),
            (lon_max + pad_right, lat_max + pad_top),
            (lon_min - pad_left, lat_max + pad_top)
        ])

        for i in range(0, lats.shape[0], self.stride):
            for j in range(0, lons.shape[1], self.stride):
                lat = lats[i, j]
                lon = lons[i, j]
                point = Point(lon, lat)

                if polygon.contains(point):
                    edge_threshold_lat = threshold.get("lat", 0.15)
                    edge_threshold_lon = threshold.get("lon", 0.25)
                    is_edge = (
                        abs(lat - lat_min) < edge_threshold_lat or
                        abs(lat - lat_max) < edge_threshold_lat or
                        abs(lon - lon_min) < edge_threshold_lon or
                        abs(lon - lon_max) < edge_threshold_lon
                    )
                    if not is_edge:
                        pass  # allow interior points as well now
                else:
                    continue

                try:
                    var_val = data[i, j]
                    if np.isnan(var_val):
                        continue
                    label = f"{int(round(var_val))}"
                except Exception:
                    continue

                ax.text(lon, lat, label, fontsize=8, ha='center', va='center', color='black',
                        transform=crs_proj, zorder=10, clip_on=True)
class WRFPlotter:
    def __init__(self, data_dir, output_dir="outputs", logo_path='logo_512_39.webp', region="Slovenia_Istria", stride=None,
                 weather_model="unknown"):
        self.data_dir = data_dir
        self.base_output_dir = os.path.abspath(output_dir)
        self.logo_path = logo_path
        self.region = region
        self.weather_model = weather_model
        self.grid_labeler = GridLabeler(stride)

        self.region_config = REGIONS.get(region)

        if self.region_config is None:
            raise ValueError(f"Region '{region}' is not defined in REGIONS dictionary.")

        self.LAT_MIN = self.region_config["lat_min"]
        self.LAT_MAX = self.region_config["lat_max"]
        self.LON_MIN = self.region_config["lon_min"]
        self.LON_MAX = self.region_config["lon_max"]
        self.logo_position = self.region_config.get("logo_position", (32, 1551))
        self.cbar_position = self.region_config.get("cbar_position", [0.13, 0.11, 0.77, 0.025])

        self.output_dir = self.get_output_path()
        os.makedirs(self.output_dir, exist_ok=True)

    def get_variable_folder(self):
        return self.__class__.__name__.lower()

    def get_output_path(self):
        path = os.path.join(self.base_output_dir, self.weather_model, self.region, self.get_variable_folder())
        os.makedirs(path, exist_ok=True)
        return path


    def create_logo(self):
        try:
            logo = mpimg.imread(self.logo_path)
            scale = min(330 / logo.shape[1], 30 / logo.shape[0])
            return zoom(logo, (scale, scale, 1))
        except Exception as e:
            print(f"Logo load failed: {e}")
            return None

    def create_source(self, filepath):
        raise NotImplementedError

    def configure_colormap(self):
        raise NotImplementedError

    def colorbar_label(self):
        return ""
    
    def friendly_name(self):
        return ""

    def plot_file(self, filepath):
        try:
            source = self.create_source(filepath)
            source.open()

            data = source.get_data()
            lats, lons = source.get_latlon()
            proj = source.get_projection()

            model_run_local = self.get_model_run_time_from_first_file()
            model_run_str = model_run_local.strftime("%-d. %-m. %Y ob %H:%M")

            dt_local = source.get_valid_time()
            time_str = dt_local.strftime("%Y%m%d_%H%M")
            time_hr = dt_local.strftime("%-d. %-m. %Y ob %H:%M")

            factor = 4.0
            data_zoomed = zoom(to_np(data), factor, order=1)
            lat_zoomed = zoom(to_np(lats), factor, order=1)
            lon_zoomed = zoom(to_np(lons), factor, order=1)

            cmap, norm, ticks = self.configure_colormap()

            fig, ax = plt.subplots(figsize=(12, 12), subplot_kw={'projection': proj})
            fig.set_facecolor('#333333')
            ax.set_extent([self.LON_MIN, self.LON_MAX, self.LAT_MIN, self.LAT_MAX], crs=crs.PlateCarree())

            ax.coastlines(resolution='10m', linewidth=0.4, color='white')
            ax.add_feature(cfeature.BORDERS.with_scale('10m'), linewidth=1.0, edgecolor='white')

            ax.pcolormesh(lon_zoomed, lat_zoomed, data_zoomed, cmap=cmap,
                          norm=norm, transform=crs.PlateCarree(), antialiased=False)

            self.grid_labeler.annotate(
                ax=ax,
                data=to_np(data),         # unzoomed
                lats=to_np(lats),         # unzoomed
                lons=to_np(lons),         # unzoomed
                lat_min=self.LAT_MIN,
                lat_max=self.LAT_MAX,
                lon_min=self.LON_MIN,
                lon_max=self.LON_MAX,
                crs_proj=crs.PlateCarree(),
                padding=self.region_config["label_padding"],
                threshold=self.region_config["edge_threshold"]
            )

            sm = ScalarMappable(norm=norm, cmap=cmap)
            sm.set_array([])
            cbar_ax = fig.add_axes(self.cbar_position)
            cbar = plt.colorbar(sm, cax=cbar_ax, orientation='horizontal', ticks=ticks)
            cbar.set_label(self.colorbar_label(), color='white', labelpad=8, weight='bold')
            cbar.ax.set_xticklabels([f"{x:.0f}" for x in ticks], color='white')
            cbar.outline.set_edgecolor('none')

            logo_resized = self.create_logo()
            if logo_resized is not None:
                fig.figimage(logo_resized, xo=self.logo_position[0], yo=self.logo_position[1], zorder=20)

            ax.text(0.5, 1.01, time_hr, transform=ax.transAxes, fontsize=13, color='white', weight='bold', ha='center')
            ax.text(1.0, 1.01, self.friendly_name(), transform=ax.transAxes, fontsize=13,
                    color='white', weight='bold', ha='right')
            ax.text(0.01, -0.12, f"Zagon modela: {model_run_str}", transform=ax.transAxes,
                    fontsize=10, ha='left', va='top', color='white', weight='bold')
            ax.text(0.99, -0.12, "Vir podatkov: TempoQuest - ICON-D2", transform=ax.transAxes,
                    fontsize=10, ha='right', va='top', color='white', weight='bold')

            output_path = os.path.join(self.output_dir, f"{self.get_variable_folder()}_{time_str}.png")
            plt.savefig(output_path, bbox_inches='tight', dpi=160, pad_inches=0.15)
            plt.close()
            source.close()

        except Exception as e:
            print(f"❌ Failed to process {filepath}: {e}")

    def run_all(self):
        wrf_files = sorted(glob(os.path.join(self.data_dir, "wrfout*_d01_*")))
        if not wrf_files:
            raise FileNotFoundError("No WRF files found.")

        print(f"🚀 Starting rendering with {len(wrf_files)} files...")
        for filepath in wrf_files:
            self.plot_file(filepath)
        print(f"✅ Export complete: {len(wrf_files)} plots → {self.output_dir}")

    def get_model_run_time_from_first_file(self):
        wrf_files = sorted(glob(os.path.join(self.data_dir, "wrfout*_d01_*")))
        if not wrf_files:
            return None
        try:
            first = Dataset(wrf_files[0])
            time_var = getvar(first, "times").values
            time_str = str(time_var[0]) if isinstance(time_var, (np.ndarray, list)) else str(time_var)
            dt = datetime.strptime(time_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            return dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/Ljubljana"))
        except Exception as e:
            print(f"❌ Could not get model run time: {e}")
            return None

class Max_Dbz(WRFPlotter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variable_name = "mdbz"
        self.reflectivity_bins = [
            (0, 15), (15, 18), (18, 21), (21, 24), (24, 27),
            (27, 30), (30, 33), (33, 36), (36, 39), (39, 42),
            (42, 45), (45, 48), (48, 51), (51, 54), (54, 57),
            (57, 60), (60, 63), (63, 66), (66, 70)
        ]
        self.colors = [
            '#0E6B9D', '#068093', '#089E94', '#05C1A0', '#04D883',
            '#5AE65A', '#A9F848', '#F0FF50', '#FFEB19', '#FFC71F',
            '#FF9F32', '#FF7D4A', '#FF6262', '#FF8FC4', '#E3D9FF',
            '#C4B5FD', '#A78BFA', '#8B5CF6', '#7C3AED',
        ]
        self.light_gray = "#626262"

    def create_source(self, filepath):
        return NetCDFWRFSource(filepath, self.variable_name)

    def configure_colormap(self):
        bin_edges = [low for (low, _) in self.reflectivity_bins] + [self.reflectivity_bins[-1][1]]
        cmap = ListedColormap([self.light_gray] + self.colors)
        norm = BoundaryNorm(bin_edges, ncolors=len(self.colors))
        ticks = list(range(15, 69, 3))
        return cmap, norm, ticks

    def colorbar_label(self):
        return "radarska odbojnost [dBZ]"
    
    def friendly_name(self):
        return "maksimalna radarska odbojnost"

class Temperature(WRFPlotter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variable_name = "T2"
        self.temperature_colors = "#dba1cf,#c180bc,#a779ba,#896db5,#6d66ad,#6c7bc4,#6091d8,#4ba7f1,#56bbfe," \
                                  "#6cc9fe,#84d4fe,#6199a2,#74ad83,#75bd6c,#a0c969,#cad778,#e7ea7f,#fff683," \
                                  "#fef9ce,#fee4a6,#fed67c,#febb5b,#fea24f,#f88438,#f36a36,#e24f2c,#e13027," \
                                  "#bf2b25,#962727,#a03937,#b55757,#ba8080".split(',')
        self.temperature_ticks = list(range(-20, 42, 2))
        self.temperature_levels = list(range(-20, 42, 2))

    def create_source(self, filepath):
        return TemperatureWRFSource(filepath, self.variable_name)

    def configure_colormap(self):
        cmap = ListedColormap(self.temperature_colors)
        norm = BoundaryNorm(self.temperature_levels, ncolors=cmap.N, extend='both')
        return cmap, norm, self.temperature_ticks

    def colorbar_label(self):
        return "temperatura [°C]"
    
    def friendly_name(self):
        return "temperatura"
    
class Acc_Precip(WRFPlotter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variable_name = "RAINNC"
        self.initial_data = None
        self.precipitation_colors = [
            "#ffffff", "#e3f0ff", "#cce1ff", "#8fbdff", "#529bdd", "#2876b5", "#208e91",
            "#04aa8a", "#2cc469", "#98d344", "#d7e205", "#ffea92", "#ffd03b", "#ff9124",
            "#e55028", "#ce2715", "#ad0800", "#aa3c90", "#cc52c6", "#d87fdd", "#e89ef2",
            "#f2bdff", "#f5d9fc"
        ]

        self.precip_levels = [0.1, 0.5, 1, 2, 5, 10, 15, 20, 30, 40, 50,
                      60, 80, 100, 120, 140, 160, 180, 200, 250, 300]

    def create_source(self, filepath):
        return NetCDFWRFSource(filepath, self.variable_name)

    def configure_colormap(self):
        cmap = ListedColormap(self.precipitation_colors)
        norm = BoundaryNorm(self.precip_levels, ncolors=len(self.precipitation_colors))
        ticks = self.precip_levels
        return cmap, norm, ticks

    def colorbar_label(self):
        return "padavine [mm]"
    
    def friendly_name(self):
        return "padavine"

    def get_variable_folder(self):
        return "accumulated_precipitation"

    def plot_file(self, filepath):
        try:
            source = self.create_source(filepath)
            source.open()
            data = source.get_data()

            if self.initial_data is None:
                self.initial_data = data
                return  # skip first frame (zero accumulation)

            data = data - self.initial_data
            lats, lons = source.get_latlon()
            proj = source.get_projection()

            model_run_local = self.get_model_run_time_from_first_file()
            model_run_str = model_run_local.strftime("%-d. %-m. %Y ob %H:%M")
            dt_local = source.get_valid_time()
            time_str = dt_local.strftime("%Y%m%d_%H%M")
            time_hr = dt_local.strftime("%-d. %-m. %Y ob %H:%M")

            factor = 4.0
            data_zoomed = zoom(to_np(data), factor, order=1)
            lat_zoomed = zoom(to_np(lats), factor, order=1)
            lon_zoomed = zoom(to_np(lons), factor, order=1)

            cmap, norm, ticks = self.configure_colormap()

            fig, ax = plt.subplots(figsize=(12, 12), subplot_kw={'projection': proj})
            fig.set_facecolor('#333333')
            ax.set_extent([self.LON_MIN, self.LON_MAX, self.LAT_MIN, self.LAT_MAX], crs=crs.PlateCarree())

            ax.coastlines(resolution='10m', linewidth=0.4, color='black')
            ax.add_feature(cfeature.BORDERS.with_scale('10m'), linewidth=1.0, edgecolor='black')

            ax.pcolormesh(lon_zoomed, lat_zoomed, data_zoomed, cmap=cmap,
                          norm=norm, transform=crs.PlateCarree(), antialiased=False)

            # Only annotate where value > 0.1 mm
            mask = to_np(data) > 0.9
            if np.any(mask):
                filtered_data = np.where(mask, to_np(data), np.nan)
                self.grid_labeler.annotate(
                    ax=ax,
                    data=filtered_data,  # Only label significant values
                    lats=to_np(lats),
                    lons=to_np(lons),
                    lat_min=self.LAT_MIN,
                    lat_max=self.LAT_MAX,
                    lon_min=self.LON_MIN,
                    lon_max=self.LON_MAX,
                    crs_proj=crs.PlateCarree(),
                    padding=self.region_config["label_padding"],
                    threshold=self.region_config["edge_threshold"]
                )


            sm = ScalarMappable(norm=norm, cmap=cmap)
            sm.set_array([])
            cbar_ax = fig.add_axes(self.cbar_position)
            cbar = plt.colorbar(sm, cax=cbar_ax, orientation='horizontal', ticks=ticks)
            cbar.set_label(self.colorbar_label(), color='white', labelpad=8, weight='bold')
            def format_tick(x):
                if x < 1:
                    return f"{x:.1f}"
                else:
                    return f"{int(x)}"

            cbar.ax.set_xticklabels([format_tick(x) for x in ticks], color='white')

            cbar.outline.set_edgecolor('none')

            logo_resized = self.create_logo()
            if logo_resized is not None:
                fig.figimage(logo_resized, xo=self.logo_position[0], yo=self.logo_position[1], zorder=20)

            ax.text(0.5, 1.01, time_hr, transform=ax.transAxes, fontsize=13, color='white', weight='bold', ha='center')
            ax.text(1.0, 1.01, self.friendly_name(), transform=ax.transAxes, fontsize=13,
                    color='white', weight='bold', ha='right')
            ax.text(0.01, -0.12, f"Zagon modela: {model_run_str}", transform=ax.transAxes,
                    fontsize=10, ha='left', va='top', color='white', weight='bold')
            ax.text(0.99, -0.12, "Vir podatkov: TempoQuest - ICON-D2", transform=ax.transAxes,
                    fontsize=10, ha='right', va='top', color='white', weight='bold')

            output_path = os.path.join(self.output_dir, f"{self.get_variable_folder()}_{time_str}.png")
            plt.savefig(output_path, bbox_inches='tight', dpi=160, pad_inches=0.15)
            plt.close()
            source.close()

        except Exception as e:
            print(f"❌ Failed to process {filepath}: {e}")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate WRF plots (reflectivity, temperature, precipitation)")
    parser.add_argument("--data_dir", required=True, help="Path to WRF output files (e.g., wrfout_d01_*)")
    parser.add_argument("--logo_path", default="logo_512_39.webp", help="Path to logo image (optional)")
    parser.add_argument("--region", default="slovenia", help="Region key (e.g., 'slovenia' or 'slovenia_istria')")
    parser.add_argument("--stride", type=int, default=6, help="Grid label stride")
    parser.add_argument("--type", choices=["mdbz", "temp", "precip"], default="mdbz", help="Type of plot")
    parser.add_argument("--weather_model", required=True, help="Weather model name (e.g., ICON-D2, WRF, ARPEGE)")

    args = parser.parse_args()

    if args.type == "mdbz":
        plotter = Max_Dbz(
            data_dir=args.data_dir,
            logo_path=args.logo_path,
            region=args.region,
            weather_model=args.weather_model
        )
    elif args.type == "temp":
        plotter = Temperature(
            data_dir=args.data_dir,
            logo_path=args.logo_path,
            region=args.region,
            stride=args.stride,
            weather_model=args.weather_model
        )
    elif args.type == "precip":
        plotter = Acc_Precip(
            data_dir=args.data_dir,
            logo_path=args.logo_path,
            region=args.region,
            stride=args.stride,
            weather_model=args.weather_model
        )
    else:
        raise ValueError("Unsupported plot type")

    plotter.run_all()
