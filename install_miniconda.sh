#!/bin/bash

# Exit on error
set -e

# Variables
MINICONDA_INSTALLER=Miniconda3-latest-Linux-x86_64.sh
MINICONDA_PREFIX="$HOME/miniconda3"
MINICONDA_URL="https://repo.anaconda.com/miniconda/$MINICONDA_INSTALLER"

# Download Miniconda installer
echo "📥 Downloading Miniconda..."
curl -sS -o "$MINICONDA_INSTALLER" "$MINICONDA_URL"

# Run installer silently
echo "📦 Installing Miniconda to $MINICONDA_PREFIX..."
bash "$MINICONDA_INSTALLER" -b -p "$MINICONDA_PREFIX"

# Remove installer
rm "$MINICONDA_INSTALLER"

# Add Conda to current shell
source "$MINICONDA_PREFIX/etc/profile.d/conda.sh"

# Initialize Conda for future shells
conda init bash

# ✅ Accept Terms of Service for required channels
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

# Create environment and clean up
conda env create -f /app/environment.yml && conda clean -a
