#!/bin/bash

# Exit if any command fails
set -e

echo "Deleting all .csv files except those starting with 'ipto'..."
for file in ./*.csv; do
  [[ "$(basename "$file")" == ipto* ]] || rm -f "$file"
done


echo "Deleting contents of 'run' directory except system.log..."
if [ -d "./run" ]; then
  find ./run -mindepth 1 ! -name 'system.log' -exec rm -rf {} +
fi

echo "Deleting contents of 'run' directory except system.log..."
if [ -d "./outputs" ]; then
  find ./outputs -mindepth 1 ! -name 'system.log' -exec rm -rf {} +
fi

echo "Cleanup complete."
