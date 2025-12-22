#!/bin/bash
set -euo pipefail

# Faster FTP recursive download using wget + xargs parallelism (Option B)
# - Lists all files under ftp://$FTP_HOST$FTP_DIR/inputs/
# - Downloads them in parallel (-P PARALLEL)
# - Preserves directory structure under /app/run (like wget -r --cut-dirs=1)
#
# Requires: wget, awk, grep, sed, xargs, mkdir

RUN_DIR="./run"
TARGET_DIR="/app/run"
PARALLEL="${PARALLEL:-8}"   # set PARALLEL=12 etc.

: "${FTP_HOST:?Missing FTP_HOST}"
: "${FTP_USER:?Missing FTP_USER}"
: "${FTP_PASS:?Missing FTP_PASS}"
: "${FTP_DIR:?Missing FTP_DIR}"

mkdir -p "$RUN_DIR"
mkdir -p "$TARGET_DIR"

echo ">> Downloading run.sh..."
wget --ftp-user="$FTP_USER" --ftp-password="$FTP_PASS" \
  "ftp://$FTP_HOST$FTP_DIR/run.sh" -O "$RUN_DIR/run.sh"
chmod +x "$RUN_DIR/run.sh"

BASE_URL="ftp://$FTP_HOST$FTP_DIR/inputs/"
LIST_FILE="/tmp/ftp_inputs_urls.txt"

echo ">> Building remote file list (spider crawl): $BASE_URL"
# --spider prints "URL: ..." and also prints "--YYYY-MM-DD ...--  ftp://..."
# We extract ftp:// links that contain /inputs/ and drop directories.
wget --ftp-user="$FTP_USER" --ftp-password="$FTP_PASS" \
  -r -nH --no-parent --spider \
  --level=inf \
  --reject "index.html*" \
  "$BASE_URL" 2>&1 \
| awk '
  # most common format: --2025-..--  ftp://... 
  /^\-\-[0-9]{4}\-/ {print $3}
  # sometimes: URL: ftp://...
  /^URL:/ {print $2}
' \
| grep -E "^ftp://$FTP_HOST" \
| grep "/inputs/" \
| grep -v '/$' \
| sort -u > "$LIST_FILE"

COUNT=$(wc -l < "$LIST_FILE" | tr -d ' ')
if [[ "$COUNT" -eq 0 ]]; then
  echo "[ERROR] No files found under $BASE_URL" >&2
  exit 1
fi
echo ">> Found $COUNT files."

# Function to download one URL and preserve folder structure beneath $TARGET_DIR
download_one() {
  local url="$1"

  # Create local path by stripping "ftp://HOST" then stripping the leading FTP_DIR (cut-dirs=1 equivalent)
  # Example:
  # url: ftp://HOST/somebase/inputs/a/b/file.dat
  # local_rel: inputs/a/b/file.dat   (because cut-dirs=1 removes "somebase")
  local rel="${url#ftp://$FTP_HOST/}"     # remove host
  rel="${rel#${FTP_DIR#/}/}"             # remove FTP_DIR (without leading slash)

  local out="$TARGET_DIR/$rel"
  local outdir
  outdir="$(dirname "$out")"
  mkdir -p "$outdir"

  # Resume (-c), quieter output (-nv)
  wget --ftp-user="$FTP_USER" --ftp-password="$FTP_PASS" \
    -c -nv \
    -O "$out" \
    "$url"
}

export -f download_one
export FTP_HOST FTP_USER FTP_PASS FTP_DIR TARGET_DIR

echo ">> Downloading in parallel (PARALLEL=$PARALLEL)..."
# xargs runs download_one for each URL
cat "$LIST_FILE" | xargs -n 1 -P "$PARALLEL" -I {} bash -lc 'download_one "$@"' _ {}

echo ">> FTP download complete."
echo ">> Files downloaded to: $(realpath "$TARGET_DIR")"
echo ">> Listing contents of $TARGET_DIR:"
find "$TARGET_DIR" -type f
