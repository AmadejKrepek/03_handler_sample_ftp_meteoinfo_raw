#!/bin/bash

# Exit on error
set -e

# Activate conda environment
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate wrf_icond2

# Run the Python script with /app/run as argument
#python max_dbz_1_0_2_detailed_profi_slo_plus_args.py --data_dir /app/run --output_dir /app/outputs --logo_path /app
#python max_dbz_1_0_2_detailed_profi_slo_plus_meteoinfo_args.py --data_dir /app/run --output_dir /app/outputs --logo_path /app
#python acc_rain_1_0_2_detailed_slo_plus_args.py --data_dir /app/run --output_dir /app/outputs

python max_dbz_1_0_2_detailed_profi_slo_plus_meteoinfo_OOP_flexible_dbz_t2_args.py --type mdbz --region slovenia_centered --data_dir /app/run --logo_path /app/logo_512_39.webp --weather_model wrf
python max_dbz_1_0_2_detailed_profi_slo_plus_meteoinfo_OOP_flexible_dbz_t2_args.py --type temp --region slovenia_centered --data_dir /app/run --logo_path /app/logo_512_39.webp --weather_model wrf
python max_dbz_1_0_2_detailed_profi_slo_plus_meteoinfo_OOP_flexible_dbz_t2_args.py --type precip --region slovenia_centered --data_dir /app/run --logo_path /app/logo_512_39.webp --weather_model wrf