#!/bin/bash

# Copy HiDream models from host to Docker volume
# This ensures models are persistent and accessible to ComfyUI container

SOURCE="/home/ghar/code/localai/ComfyUI/models"
VOLUME="localai_comfyui-models"
DEST=$(docker volume inspect $VOLUME | python3 -c 'import sys, json; print(json.load(sys.stdin)[0]["Mountpoint"])')

echo "Copying HiDream models to Docker volume..."
echo "Source: $SOURCE"
echo "Destination: $DEST"
echo ""

# Copy with sudo since Docker volumes need elevated permissions
sudo mkdir -p "$DEST/diffusion_models/split_files/diffusion_models"
sudo mkdir -p "$DEST/text_encoders/split_files/text_encoders"
sudo mkdir -p "$DEST/vae/split_files/vae"

echo "Copying diffusion models..."
sudo cp -rv "$SOURCE/diffusion_models/split_files/diffusion_models/"*.safetensors "$DEST/diffusion_models/split_files/diffusion_models/" 2>/dev/null || echo "No diffusion models yet"

echo "Copying text encoders..."
sudo cp -rv "$SOURCE/text_encoders/split_files/text_encoders/"*.safetensors "$DEST/text_encoders/split_files/text_encoders/" 2>/dev/null || echo "No text encoders yet"

echo "Copying VAE..."
sudo cp -rv "$SOURCE/vae/split_files/vae/"*.safetensors "$DEST/vae/split_files/vae/" 2>/dev/null || echo "No VAE yet"

echo ""
echo "Done! Verifying files in Docker volume..."
sudo ls -lh "$DEST/diffusion_models/split_files/diffusion_models/"
sudo ls -lh "$DEST/text_encoders/split_files/text_encoders/"
sudo ls -lh "$DEST/vae/split_files/vae/"

echo ""
echo "✓ Models copied to Docker volume and will persist across container rebuilds"
