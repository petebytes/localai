# Custom n8n Dockerfile with ffmpeg
# Based on official n8n image with added multimedia tools

# Use official n8n image as base
# Specifying :latest explicitly for clarity and version tracking
FROM docker.n8n.io/n8nio/n8n:latest

# Switch to root to install packages
USER root

# Install ffmpeg, fonts, and other useful tools
# - ffmpeg: Audio/video processing
# - ffprobe: Media file inspection (part of ffmpeg package)
# - fontconfig: Font configuration library
# - ttf-dejavu: Default sans-serif fallback fonts
# - font-montserrat: Montserrat font family (from Alpine community repo)
# - python3: For ASS subtitle generation script
RUN apk add --no-cache \
    ffmpeg \
    fontconfig \
    ttf-dejavu \
    font-montserrat \
    python3 \
    py3-pip \
    && fc-cache -fv

# Switch back to node user (UID 1000) for security
USER node

# No need to change CMD or ENTRYPOINT - inherited from base image
