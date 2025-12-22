#!/bin/bash
set -e

# Create directory for running acecast in and cd into it
mkdir -p run

echo ">> Downloading run.sh script..."
wget --ftp-user="$FTP_USER" --ftp-password="$FTP_PASS" \
  "ftp://$FTP_HOST$FTP_DIR/run.sh" -O run.sh

chmod +x run.sh

# Define target directory
TARGET_DIR="/app/run"


echo ">> Creating target directory at $TARGET_DIR..."
mkdir -p "$TARGET_DIR"

echo ">> Downloading input folder recursively into $TARGET_DIR..."

wget --ftp-user="$FTP_USER" --ftp-password="$FTP_PASS" \
  -r -nH --cut-dirs=1 --no-parent -P "$TARGET_DIR/" \
  "ftp://$FTP_HOST$FTP_DIR/inputs/"

echo ">> FTP download complete."

# Print full path of where files were downloaded
echo ">> Files downloaded to: $(realpath "$TARGET_DIR")"

# Optional: list downloaded files
echo ">> Listing contents of $TARGET_DIR:"
find "$TARGET_DIR" -type f
