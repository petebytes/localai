#!/usr/bin/env bash
#
# Test Script: Step 4 - InfiniteTalk Video Generation
#
# Tests the infinitetalk-api service for generating talking head videos
# from audio and portrait images.
#
# Usage:
#   bash test-step4-video-generation.sh [audio_path] [image_path] [prompt]
#
# Example:
#   bash test-step4-video-generation.sh \
#     ./shared/audio/voice_cloned.wav \
#     ./shared/images/portrait.png \
#     "A professional speaker presenting content"
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://infinitetalk-api:8200"
TIMEOUT=600  # 10 minutes timeout

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Parse arguments
AUDIO_PATH="${1:-./shared/audio/test_audio.wav}"
IMAGE_PATH="${2:-./shared/images/test_portrait.png}"
PROMPT="${3:-A professional speaker presenting their content in a studio setting with professional lighting}"

# Validate input files exist
if [ ! -f "$AUDIO_PATH" ]; then
    print_error "Audio file not found: $AUDIO_PATH"
    print_info "Please provide an audio file path as the first argument"
    exit 1
fi

if [ ! -f "$IMAGE_PATH" ]; then
    print_error "Image file not found: $IMAGE_PATH"
    print_info "Please provide an image file path as the second argument"
    exit 1
fi

# Convert to absolute paths (needed for Docker volume mounting)
AUDIO_PATH_ABS="$(cd "$(dirname "$AUDIO_PATH")" && pwd)/$(basename "$AUDIO_PATH")"
IMAGE_PATH_ABS="$(cd "$(dirname "$IMAGE_PATH")" && pwd)/$(basename "$IMAGE_PATH")"

# Get container-relative paths (assuming files are in shared volume)
AUDIO_CONTAINER_PATH="/data/shared/$(basename "$(dirname "$AUDIO_PATH")")/$(basename "$AUDIO_PATH")"
IMAGE_CONTAINER_PATH="/data/shared/$(basename "$(dirname "$IMAGE_PATH")")/$(basename "$IMAGE_PATH")"

print_info "=========================================="
print_info "Step 4: InfiniteTalk Video Generation Test"
print_info "==========================================\n"

# Step 1: Check service health
print_info "Step 1: Checking infinitetalk-api service health..."

HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL/api/health" || echo "000")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" != "200" ]; then
    print_error "Service health check failed (HTTP $HTTP_CODE)"
    print_error "Response: $HEALTH_BODY"
    exit 1
fi

print_success "Service is healthy"
echo "$HEALTH_BODY" | jq '.'

# Step 2: Prepare request payload
print_info "\nStep 2: Preparing video generation request..."
print_info "  Audio: $AUDIO_PATH"
print_info "  Image: $IMAGE_PATH"
print_info "  Prompt: $PROMPT"

REQUEST_PAYLOAD=$(cat <<EOF
{
  "audio_path": "$AUDIO_CONTAINER_PATH",
  "image_path": "$IMAGE_CONTAINER_PATH",
  "prompt": "$PROMPT",
  "resolution": "infinitetalk-480",
  "seed": 42,
  "diffusion_steps": 40,
  "text_guide_scale": 5.0,
  "audio_guide_scale": 4.0,
  "motion_frame": 9,
  "use_color_correction": true
}
EOF
)

print_success "Request payload prepared"

# Step 3: Submit generation request
print_info "\nStep 3: Submitting video generation request..."
print_warning "This may take 3-5 minutes..."

START_TIME=$(date +%s)

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "$API_URL/api/generate-video" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_PAYLOAD" \
  --max-time $TIMEOUT \
  || echo "000")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RESPONSE" | head -n-1)

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ "$HTTP_CODE" != "200" ]; then
    print_error "Video generation failed (HTTP $HTTP_CODE)"
    print_error "Response: $RESPONSE_BODY"
    exit 1
fi

print_success "Video generation completed in ${DURATION}s"

# Step 4: Parse response
print_info "\nStep 4: Parsing response..."

VIDEO_PATH=$(echo "$RESPONSE_BODY" | jq -r '.video_path')
DURATION_SEC=$(echo "$RESPONSE_BODY" | jq -r '.duration_seconds')
RESOLUTION=$(echo "$RESPONSE_BODY" | jq -r '.resolution')
FRAME_COUNT=$(echo "$RESPONSE_BODY" | jq -r '.frame_count')

if [ -z "$VIDEO_PATH" ] || [ "$VIDEO_PATH" == "null" ]; then
    print_error "Failed to extract video path from response"
    print_error "Response: $RESPONSE_BODY"
    exit 1
fi

print_success "Response parsed successfully"
echo "$RESPONSE_BODY" | jq '.'

# Step 5: Verify output file
print_info "\nStep 5: Verifying output video..."

# Convert container path to host path
VIDEO_HOST_PATH="./infinitetalk-api-server/output/$(basename "$VIDEO_PATH")"

if [ -f "$VIDEO_HOST_PATH" ]; then
    FILE_SIZE=$(stat -f%z "$VIDEO_HOST_PATH" 2>/dev/null || stat -c%s "$VIDEO_HOST_PATH" 2>/dev/null || echo "0")
    FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))

    print_success "Video file created: $VIDEO_HOST_PATH"
    print_info "  Size: ${FILE_SIZE_MB}MB"
    print_info "  Duration: ${DURATION_SEC}s"
    print_info "  Resolution: $RESOLUTION"
    print_info "  Frames: $FRAME_COUNT"

    # Get video metadata using ffprobe if available
    if command -v ffprobe &> /dev/null; then
        print_info "\nVideo metadata (ffprobe):"
        ffprobe -v quiet -print_format json -show_format -show_streams "$VIDEO_HOST_PATH" | jq '.format | {duration, size, bit_rate, format_name}'
    fi
else
    print_warning "Video file not found at expected host path: $VIDEO_HOST_PATH"
    print_info "Container path: $VIDEO_PATH"
fi

# Summary
print_info "\n=========================================="
print_info "Test Summary"
print_info "==========================================\n"
print_success "Step 4 (InfiniteTalk Video Generation): PASSED"
print_info "  Processing time: ${DURATION}s"
print_info "  Output video: $VIDEO_HOST_PATH"
print_info "  Duration: ${DURATION_SEC}s @ 25fps"
print_info "  Resolution: $RESOLUTION"
print_info "  Total frames: $FRAME_COUNT"
print_info "\nNext steps:"
print_info "  1. View the generated video: $VIDEO_HOST_PATH"
print_info "  2. Verify quality and lip-sync accuracy"
print_info "  3. Integrate with Steps 1-2-3 in n8n workflow"

print_success "\n✓ All tests passed!"
