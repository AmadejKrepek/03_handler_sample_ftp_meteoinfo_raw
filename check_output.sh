#!/bin/bash
set -e

echo ">> Checking output directory after simulation..."

# Define the expected output directory and file
RUN_DIR="run"
OUTPUT_FILE="$RUN_DIR/rsl.out.0000"

# Check if run directory exists
if [ -d "$RUN_DIR" ]; then
    echo "✅ Directory '$RUN_DIR' exists."
else
    echo "❌ Directory '$RUN_DIR' does not exist!"
    exit 1
fi

# Check if the output file exists
if [ -f "$OUTPUT_FILE" ]; then
    echo "✅ Output file '$OUTPUT_FILE' exists."
    echo "------ Contents of $OUTPUT_FILE (first 100 lines) ------"
    head -n 100 "$OUTPUT_FILE"
else
    echo "❌ Output file '$OUTPUT_FILE' does not exist!"
    exit 1
fi
