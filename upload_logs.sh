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

  # Find latest wrfoutcustom for this domain (FIXED: tail = newest)
  latest_file=$(
    find "$CSV_DIR" -maxdepth 1 -type f -name "wrfoutcustom_${DOM}_????-??-??_??:??:??" \
    | sort \
    | tail -n 1
  )

  if [[ -z "${latest_file:-}" ]]; then
    echo "[WARN] No wrfoutcustom_${DOM}_YYYY-MM-DD_HH:MM:SS found in $CSV_DIR, skipping $DOM"
    continue
  fi

  filename_only=$(basename "$latest_file")
  if [[ "$filename_only" =~ wrfoutcustom_${DOM}_([0-9]{4})-([0-9]{2})-([0-9]{2})_([0-9]{2}):[0-9]{2}:[0-9]{2} ]]; then
    YYYY="${BASH_REMATCH[1]}"
    MM="${BASH_REMATCH[2]}"
    DD="${BASH_REMATCH[3]}"
    HH="${BASH_REMATCH[4]}"
  else
    error_exit "Filename does not match pattern: wrfoutcustom_${DOM}_YYYY-MM-DD_HH:MM:SS"
  fi

  ID="${YYYY}_${MM}_${DD}_${HH}"
  FTP_REMOTE_DIR="/logs/$YYYY/$MM/$DD/$HH/$DOM"   # domain-specific folder

  # --- Upload logs (renamed with _ID) ---
  any_log=0
  for file in "${FILES_TO_UPLOAD[@]}"; do
    full_path="$RUN_DIR/$file"
    if [[ -f "$full_path" ]]; then
      any_log=1
      base=$(basename "$full_path")
      renamed="${base}_${ID}"
      upload_file "$full_path" "$FTP_REMOTE_DIR" "$renamed"
    fi
  done
  if [[ "$any_log" -eq 0 ]]; then
    echo "[WARN] No specified log files found in $RUN_DIR (still uploading wrfout files for $DOM)"
  fi

  # --- Upload latest wrfoutcustom for this domain (keep original name) ---
  upload_file "$latest_file" "$FTP_REMOTE_DIR" "$(basename "$latest_file")"

  # --- OPTIONAL: upload ALL wrfoutcustom for this domain ---
  if [[ "$UPLOAD_ALL_WRFOUTCUSTOM" == "1" ]]; then
    while IFS= read -r f; do
      [[ -f "$f" ]] || continue
      upload_file "$f" "$FTP_REMOTE_DIR" "$(basename "$f")"
    done < <(find "$CSV_DIR" -maxdepth 1 -type f -name "wrfoutcustom_${DOM}_????-??-??_??:??:??" | sort)
  fi

  # --- OPTIONAL: upload regular wrfout for this domain ---
  if [[ "$UPLOAD_WRFOUT" == "1" ]]; then
    while IFS= read -r f; do
      [[ -f "$f" ]] || continue
      upload_file "$f" "$FTP_REMOTE_DIR" "$(basename "$f")"
    done < <(find "$CSV_DIR" -maxdepth 1 -type f -name "wrfout_${DOM}_????-??-??_??:??:??" | sort)
  fi
done
