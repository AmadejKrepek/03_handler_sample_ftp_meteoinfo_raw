#!/bin/bash
set -euo pipefail

function error_exit {
  echo "[ERROR] $1" >&2
  exit 1
}

RUN_DIR="./run"
CSV_DIR="/app/run"

: "${FTP_HOST:?Missing FTP_HOST}"
: "${FTP_USER:?Missing FTP_USER}"
: "${FTP_PASS:?Missing FTP_PASS}"

# Provided by user input (via handler.py)
: "${PROJECT_NAME:?Missing PROJECT_NAME}"
: "${EXPERIMENT_NAME:?Missing EXPERIMENT_NAME}"

# Sanitize to keep folder structure safe (avoid accidental slashes)
PROJECT_NAME_SAFE="${PROJECT_NAME//\//_}"
EXPERIMENT_NAME_SAFE="${EXPERIMENT_NAME//\//_}"

# Execution timestamp folder (when this script was executed)
# Using YYYY_MM_DD_HH_mm_ss (includes hour to prevent collisions).
EXEC_TS="${EXEC_TS:-$(date +"%Y_%m_%d_%H_%M_%S")}"

upload_file() {
  local src="$1"
  local remote_dir="$2"
  local dst="$3"
  echo "Uploading $(basename "$src") as $dst to ftp://$FTP_HOST$remote_dir/"
  curl -T "$src" --ftp-create-dirs --silent --show-error \
    --user "$FTP_USER:$FTP_PASS" \
    "ftp://$FTP_HOST$remote_dir/$dst"
  echo "[SUCCESS] Uploaded $dst"
}

# Upload log files (same list for both domains)
FILES_TO_UPLOAD=(
  "rsl.out.0000"
  "rsl.error.0000"
  "fort.88"
  "namelist.input"
)

# Toggles
UPLOAD_ALL_WRFOUTCUSTOM="${UPLOAD_ALL_WRFOUTCUSTOM:-0}" # 1 = upload all wrfoutcustom_* per domain
UPLOAD_WRFOUT="${UPLOAD_WRFOUT:-0}"                     # 1 = upload wrfout_* per domain

# Domains to process
DOMAINS=("d01" "d02")

for DOM in "${DOMAINS[@]}"; do
  echo "===================="
  echo "[INFO] Processing $DOM"
  echo "===================="

  # --- Check if any wrfoutcustom or wrfout exists for this domain ---
  has_wrfoutcustom=0
  has_wrfout=0

  if find "$CSV_DIR" -maxdepth 1 -type f -name "wrfoutcustom_${DOM}_????-??-??_??:??:??" -print -quit | grep -q .; then
    has_wrfoutcustom=1
  fi

  # IMPORTANT: do NOT use "wrfout*": it would also match wrfoutcustom*
  if find "$CSV_DIR" -maxdepth 1 -type f -name "wrfout_${DOM}_????-??-??_??:??:??" -print -quit | grep -q .; then
    has_wrfout=1
  fi

  if [[ "$has_wrfoutcustom" -eq 0 && "$has_wrfout" -eq 0 ]]; then
    echo "[WARN] No wrfoutcustom_${DOM}_* or wrfout_${DOM}_* found in $CSV_DIR, skipping $DOM (no logs either)"
    continue
  fi

  # --- Pick latest file for time parsing and (optionally) upload ---
  latest_file=""

  if [[ "$has_wrfoutcustom" -eq 1 ]]; then
    latest_file=$(
      find "$CSV_DIR" -maxdepth 1 -type f -name "wrfoutcustom_${DOM}_????-??-??_??:??:??" \
      | sort \
      | tail -n 1
    )
  else
    latest_file=$(
      find "$CSV_DIR" -maxdepth 1 -type f -name "wrfout_${DOM}_????-??-??_??:??:??" \
      | sort \
      | tail -n 1
    )
  fi

  if [[ -z "${latest_file:-}" ]]; then
    echo "[WARN] Unexpected: existence check passed but no latest file found, skipping $DOM"
    continue
  fi

  # --- Extract time from whichever "latest_file" we chose ---
  filename_only=$(basename "$latest_file")
  if [[ "$filename_only" =~ _([0-9]{4})-([0-9]{2})-([0-9]{2})_([0-9]{2}):[0-9]{2}:[0-9]{2}$ ]]; then
    YYYY="${BASH_REMATCH[1]}"
    MM="${BASH_REMATCH[2]}"
    DD="${BASH_REMATCH[3]}"
    HH="${BASH_REMATCH[4]}"
  else
    error_exit "Filename does not match expected timestamp suffix: *_YYYY-MM-DD_HH:MM:SS (got: $filename_only)"
  fi

  ID="${YYYY}_${MM}_${DD}_${HH}"

  # New structure:
  # /logs/<project_name>/<experiment_name>/<exec_ts>/<YYYY>/<MM>/<DD>/<HH>/
  # (NO domain folder; we encode domain into filenames to avoid collisions)
  FTP_REMOTE_DIR="/logs/${PROJECT_NAME_SAFE}/${EXPERIMENT_NAME_SAFE}/${EXEC_TS}/$YYYY/$MM/$DD/$HH"

  # --- Upload logs (renamed with domain + ID) ---
  any_log=0
  for file in "${FILES_TO_UPLOAD[@]}"; do
    full_path="$RUN_DIR/$file"
    if [[ -f "$full_path" ]]; then
      any_log=1
      base=$(basename "$full_path")
      renamed="${base}_${DOM}_${ID}"
      upload_file "$full_path" "$FTP_REMOTE_DIR" "$renamed"
    fi
  done
  if [[ "$any_log" -eq 0 ]]; then
    echo "[WARN] No specified log files found in $RUN_DIR (but wrfout/wrfoutcustom exists for $DOM)"
  fi

  # --- Upload latest wrfoutcustom for this domain (keep original name) ---
  if [[ "$has_wrfoutcustom" -eq 1 ]]; then
    upload_file "$latest_file" "$FTP_REMOTE_DIR" "$(basename "$latest_file")"
  else
    echo "[INFO] No wrfoutcustom for $DOM. Skipping latest wrfoutcustom upload."
  fi

  # --- OPTIONAL: upload ALL wrfoutcustom for this domain ---
  if [[ "$UPLOAD_ALL_WRFOUTCUSTOM" == "1" ]]; then
    if [[ "$has_wrfoutcustom" -eq 1 ]]; then
      while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        upload_file "$f" "$FTP_REMOTE_DIR" "$(basename "$f")"
      done < <(find "$CSV_DIR" -maxdepth 1 -type f -name "wrfoutcustom_${DOM}_????-??-??_??:??:??" | sort)
    else
      echo "[INFO] UPLOAD_ALL_WRFOUTCUSTOM=1 but no wrfoutcustom files exist for $DOM."
    fi
  fi

  # --- OPTIONAL: upload regular wrfout for this domain ---
  if [[ "$UPLOAD_WRFOUT" == "1" ]]; then
    if [[ "$has_wrfout" -eq 1 ]]; then
      while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        upload_file "$f" "$FTP_REMOTE_DIR" "$(basename "$f")"
      done < <(find "$CSV_DIR" -maxdepth 1 -type f -name "wrfout_${DOM}_????-??-??_??:??:??" | sort)
    else
      echo "[INFO] UPLOAD_WRFOUT=1 but no wrfout files exist for $DOM."
    fi
  fi
done
