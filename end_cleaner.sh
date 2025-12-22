#!/bin/bash

# Exit if any command fails
set -e

echo "Deleting all .csv files in the current directory..."
for file in ./*.csv; do
  [[ "$(basename "$file")" == ipto* ]] || rm -f "$file"
done


echo "Deleting 'run' directory if it exists..."
rm -rf ./run

echo "Cleanup complete."