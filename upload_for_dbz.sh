#!/bin/bash

set -euo pipefail

function error_exit {
  echo "[ERROR] $1" >&2
  exit 1
}

WRFOUT_DIR="/app/outputs"
FTP_REMOTE_BASE="/outputs"

: "${FTP_HOST:?Missing FTP_HOST}"
: "${FTP_USER:?Missing FTP_USER}"
: "${FTP_PASS:?Missing FTP_PASS}"

shopt -s nullglob
png_files=("$WRFOUT_DIR"/*.png)
shopt -u nullglob

if [ ${#png_files[@]} -eq 0 ]; then
  error_exit "No PNG files found in $WRFOUT_DIR"
fi

# Find the oldest file by modification time
first_file="${png_files[0]}"
for file in "${png_files[@]}"; do
  [[ "$file" -ot "$first_file" ]] && first_file="$file"
done

# Extract UTC timestamp from filename (e.g., max_dbz_20250730_0200.png → 20250730_0200)
basename_file=$(basename "$first_file")
datetime_utc="${basename_file#max_dbz_}"
datetime_utc="${datetime_utc%.png}"

# Split into components
if [[ "$datetime_utc" =~ ^([0-9]{4})([0-9]{2})([0-9]{2})_([0-9]{2}) ]]; then
  YYYY="${BASH_REMATCH[1]}"
  MM="${BASH_REMATCH[2]}"
  DD="${BASH_REMATCH[3]}"
  HH="${BASH_REMATCH[4]}"
else
  error_exit "Filename does not match expected pattern: max_dbz_YYYYMMDD_HHMM.png"
fi

# Final FTP path: /outputs/YYYY/MM/DD/HH
FTP_REMOTE_DIR="$FTP_REMOTE_BASE/$YYYY/$MM/$DD/$HH"

echo "🕒 Oldest file: $first_file"
echo "📁 Uploading to: ftp://$FTP_HOST$FTP_REMOTE_DIR/"

# Upload each PNG file to the structured path
for file in "${png_files[@]}"; do
  filename=$(basename "$file")
  echo "Uploading $filename..."

  curl -T "$file" --ftp-create-dirs --silent --show-error \
    --user "$FTP_USER:$FTP_PASS" \
    "ftp://$FTP_HOST$FTP_REMOTE_DIR/$filename"

  if [ $? -eq 0 ]; then
    echo "[SUCCESS] Uploaded $filename"
  else
    echo "[FAIL] Failed to upload $filename" >&2
  fi
done
