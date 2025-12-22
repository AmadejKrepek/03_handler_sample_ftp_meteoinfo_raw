#!/bin/bash
set -euo pipefail

WRFOUT_DIR="/app/outputs"
FTP_REMOTE_BASE="/outputs"

: "${FTP_HOST:?Missing FTP_HOST}"
: "${FTP_USER:?Missing FTP_USER}"
: "${FTP_PASS:?Missing FTP_PASS}"

function error_exit {
  echo "[ERROR] $1" >&2
  exit 1
}

# Sanity check
if [ ! -d "$WRFOUT_DIR" ]; then
  error_exit "$WRFOUT_DIR does not exist."
fi

# Function to recursively create FTP directories
create_ftp_dir_recursive() {
  local path="$1"
  local base="ftp://$FTP_HOST"
  local current=""

  IFS='/' read -ra PARTS <<< "$path"
  for part in "${PARTS[@]}"; do
    [[ -z "$part" ]] && continue
    current="$current/$part"
    curl --silent --show-error --user "$FTP_USER:$FTP_PASS" \
      "$base" --quote "MKD $current" >/dev/null 2>&1 || true
  done
}

# First datetime components placeholder
YYYY=""
MM=""
DD=""
HH=""
first_datetime=""

# Find and upload all PNGs
find "$WRFOUT_DIR" -type f -name "*.png" | while read -r local_file; do
  filename=$(basename "$local_file")
  filename_no_ext="${filename%.png}"

  # Extract datetime from end of filename
  datetime_utc=$(echo "$filename_no_ext" | grep -oE "[0-9]{8}_[0-9]{4}$" || true)

  if [[ -z "$datetime_utc" ]]; then
    echo "[WARN] Skipping $filename – no datetime found."
    continue
  fi

  # If this is the first datetime, extract components
  if [[ -z "$first_datetime" ]]; then
    if [[ "$datetime_utc" =~ ^([0-9]{4})([0-9]{2})([0-9]{2})_([0-9]{2}) ]]; then
      YYYY="${BASH_REMATCH[1]}"
      MM="${BASH_REMATCH[2]}"
      DD="${BASH_REMATCH[3]}"
      HH="${BASH_REMATCH[4]}"
      first_datetime="$datetime_utc"
      echo "🔵 First datetime folder: $YYYY/$MM/$DD/$HH"
    else
      echo "[WARN] Invalid datetime format: $datetime_utc"
      continue
    fi
  fi

  # Relative subfolder (after /app/outputs)
  rel_path="${local_file#$WRFOUT_DIR/}"
  remote_subdir=$(dirname "$rel_path")
  ftp_dir="$FTP_REMOTE_BASE/$YYYY/$MM/$DD/$HH/$remote_subdir"
  ftp_url="ftp://$FTP_HOST$ftp_dir"

  echo "🟡 Uploading: $rel_path → $ftp_url/$filename"

  # Recursively create FTP folders
  create_ftp_dir_recursive "$ftp_dir"

  # Upload the file
  curl --silent --show-error --ftp-create-dirs --user "$FTP_USER:$FTP_PASS" \
       -T "$local_file" "$ftp_url/$filename" \
       && echo "✅ Uploaded: $filename" \
       || echo "❌ Failed: $filename"
done
