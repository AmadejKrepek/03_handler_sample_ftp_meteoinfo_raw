#!/usr/bin/env bash
set -u -o pipefail

PARALLEL="${PARALLEL:-12}"
TARGET_DIR="/app/run"
RUN_DIR="./run"
CACHE_LIST="${CACHE_LIST:-/tmp/ftp_inputs_urls.cache.txt}"

: "${FTP_HOST:?Missing FTP_HOST}"
: "${FTP_USER:?Missing FTP_USER}"
: "${FTP_PASS:?Missing FTP_PASS}"
: "${FTP_DIR:?Missing FTP_DIR}"

FTP_DIR="/${FTP_DIR#/}"
FTP_DIR="${FTP_DIR%/}"

mkdir -p "$RUN_DIR" "$TARGET_DIR"

echo ">> Downloading run.sh..."
wget --ftp-user="$FTP_USER" --ftp-password="$FTP_PASS" \
  --timeout=30 --read-timeout=30 --tries=10 --waitretry=2 \
  "ftp://$FTP_HOST$FTP_DIR/run.sh" -O run.sh
chmod +x run.sh

BASE_URL="ftp://$FTP_HOST$FTP_DIR/inputs/"

if [[ -s "$CACHE_LIST" ]]; then
  echo ">> Using cached file list: $CACHE_LIST"
else
  echo ">> Building remote file list (spider crawl): $BASE_URL"
  wget --ftp-user="$FTP_USER" --ftp-password="$FTP_PASS" \
    -r -nH --no-parent --spider --level=inf \
    --reject "index.html*" \
    --timeout=30 --read-timeout=30 --tries=10 --waitretry=2 \
    "$BASE_URL" 2>&1 \
  | awk '
    /^\-\-[0-9]{4}\-/ {print $3}
    /^URL:/ {print $2}
  ' \
  | grep -E "^ftp://$FTP_HOST" \
  | grep "/inputs/" \
  | grep -v '/$' \
  | sort -u > "$CACHE_LIST"
fi

COUNT="$(wc -l < "$CACHE_LIST" | tr -d ' ')"
if [[ "${COUNT:-0}" -eq 0 ]]; then
  echo "[ERROR] No files found under $BASE_URL" >&2
  exit 1
fi
echo ">> Found $COUNT files."

download_one() {
  local url="$1"
  local rel="${url#ftp://$FTP_HOST/}"
  rel="${rel#${FTP_DIR#/}/}"
  local out="$TARGET_DIR/$rel"
  mkdir -p "$(dirname "$out")"

  wget --ftp-user="$FTP_USER" --ftp-password="$FTP_PASS" \
    --timeout=30 --read-timeout=30 --tries=10 --waitretry=2 \
    -c -nv -O "$out" "$url"
}
export -f download_one
export FTP_HOST FTP_USER FTP_PASS FTP_DIR TARGET_DIR

echo ">> Downloading in parallel: PARALLEL=$PARALLEL"
FAILS="/tmp/ftp_fails.$$"
: > "$FAILS"

xargs -n 1 -P "$PARALLEL" -I {} bash -lc '
  url="$1"
  if ! download_one "$url"; then
    echo "$url" >> "'"$FAILS"'"
  fi
' _ {} < "$CACHE_LIST"

FAILS_COUNT="$(wc -l < "$FAILS" | tr -d " ")"
if [[ "${FAILS_COUNT:-0}" -gt 0 ]]; then
  echo "[WARN] $FAILS_COUNT downloads failed. See: $FAILS" >&2
else
  rm -f "$FAILS"
fi

echo ">> Done. Files at: $(realpath "$TARGET_DIR")"
