#!/bin/bash

set -euo pipefail

function error_exit {
  echo "[ERROR] $1" >&2
  exit 1
}

WRFOUT_DIR="/app/outputs/mdbz"
FTP_REMOTE_DIR="/outputs/latest"

: "${FTP_HOST:?Missing FTP_HOST}"
: "${FTP_USER:?Missing FTP_USER}"
: "${FTP_PASS:?Missing FTP_PASS}"

shopt -s nullglob
png_files=("$WRFOUT_DIR"/*.png)
shopt -u nullglob

if [ ${#png_files[@]} -eq 0 ]; then
  error_exit "No PNG files found in $WRFOUT_DIR"
fi

echo "🧹 Cleaning remote folder: $FTP_REMOTE_DIR"
# Remove existing remote 'latest' folder (requires FTP command support)
curl --silent --show-error --user "$FTP_USER:$FTP_PASS" \
  "ftp://$FTP_HOST" --quote "RMD $FTP_REMOTE_DIR" || echo "[INFO] Folder may not exist yet."

# Recreate the remote 'latest' folder
curl --silent --show-error --user "$FTP_USER:$FTP_PASS" \
  --ftp-create-dirs -T /dev/null "ftp://$FTP_HOST$FTP_REMOTE_DIR/.keep"

echo "📤 Uploading PNGs to: ftp://$FTP_HOST$FTP_REMOTE_DIR/"
for file in "${png_files[@]}"; do
  filename=$(basename "$file")
  echo "Uploading $filename..."

  curl --silent --show-error --ftp-create-dirs \
    --user "$FTP_USER:$FTP_PASS" \
    -T "$file" "ftp://$FTP_HOST$FTP_REMOTE_DIR/$filename"

  if [ $? -eq 0 ]; then
    echo "[SUCCESS] Uploaded $filename"
  else
    echo "[FAIL] Failed to upload $filename" >&2
  fi
done
