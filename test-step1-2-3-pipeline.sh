#!/usr/bin/env bash

# Test script for Steps 1-2-3: Full pipeline through portrait generation
# Tests YouTube audio extraction, voice cloning, and portrait image generation

set -euo pipefail

# Configuration
N8N_WEBHOOK_URL="${N8N_WEBHOOK_URL:-https://n8n.lan/webhook/generate-video-step1-2-3}"
TEST_OUTPUT_DIR="${OUTPUT_DIR:-./test-outputs/step123}"

# Default test parameters
YOUTUBE_URL="${1:-https://www.youtube.com/watch?v=ao8f3qyMoLM}"
SCRIPT="${2:-Welcome to our presentation on artificial intelligence and machine learning applications in modern business environments.}"
SEGMENT_START="${3:-40}"
SEGMENT_END="${4:-70}"

# TTS parameters (required by workflow)
CFG_SCALE="${5:-1.5}"
DIFFUSION_STEPS="${6:-30}"
TEMPERATURE="${7:-0.75}"
TOP_P="${8:-0.85}"
USE_SAMPLING="${9:-true}"

echo "=================================================="
echo "Steps 1-2-3 Pipeline Test"
echo "=================================================="
echo ""
echo "Testing complete pipeline:"
echo "  Step 1: YouTube Audio Extraction"
echo "  Step 2: Voice Cloning + TTS"
echo "  Step 3: Portrait Image Generation"
echo ""
echo "Parameters:"
echo "  YouTube URL: $YOUTUBE_URL"
echo "  Script: $SCRIPT"
echo "  Segment: ${SEGMENT_START}s - ${SEGMENT_END}s"
echo "  CFG Scale: $CFG_SCALE"
echo "  Diffusion Steps: $DIFFUSION_STEPS"
echo "  Temperature: $TEMPERATURE"
echo "  Top P: $TOP_P"
echo "  Use Sampling: $USE_SAMPLING"
echo "  Output Dir: $TEST_OUTPUT_DIR"
echo ""
echo "n8n Webhook: $N8N_WEBHOOK_URL"
echo ""

# Create output directory
mkdir -p "$TEST_OUTPUT_DIR"

# Prepare request payload
REQUEST_PAYLOAD=$(cat <<EOF
{
  "youtube_url": "$YOUTUBE_URL",
  "script": "$SCRIPT",
  "segment_start": $SEGMENT_START,
  "segment_end": $SEGMENT_END,
  "cfg_scale": $CFG_SCALE,
  "diffusion_steps": $DIFFUSION_STEPS,
  "temperature": $TEMPERATURE,
  "top_p": $TOP_P,
  "use_sampling": $USE_SAMPLING
}
EOF
)

echo "[1/3] Submitting request to n8n workflow..."
echo "Payload:"
echo "$REQUEST_PAYLOAD" | jq '.'
echo ""

START_TIME=$(date +%s)

# Submit request (with -k to bypass self-signed certificate)
RESPONSE_FILE="$TEST_OUTPUT_DIR/response.json"

HTTP_CODE=$(curl -k -s -w "%{http_code}" \
  -X POST "$N8N_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_PAYLOAD" \
  -o "$RESPONSE_FILE")

# Check HTTP status code
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "201" ]; then
  echo "❌ ERROR: HTTP $HTTP_CODE from n8n"
  echo "Response:"
  cat "$RESPONSE_FILE" | jq . 2>/dev/null || cat "$RESPONSE_FILE"
  exit 1
fi

RESPONSE=$(cat "$RESPONSE_FILE")

echo "✅ Workflow completed successfully!"
echo ""

ELAPSED=$(($(date +%s) - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo "Total execution time: ${MINUTES}m ${SECONDS}s"
echo ""

# Parse response
echo "[2/3] Parsing response..."

# Extract metadata
SUCCESS=$(echo "$RESPONSE" | jq -r '.[0].json.success // false')
MESSAGE=$(echo "$RESPONSE" | jq -r '.[0].json.message // "No message"')

if [ "$SUCCESS" != "true" ]; then
  echo "⚠️  Warning: success flag not set to true"
fi

echo "Message: $MESSAGE"
echo ""

# Step 1 info
echo "Step 1 (YouTube Audio Extraction):"
STEP1_TASK_ID=$(echo "$RESPONSE" | jq -r '.[0].json.step1.task_id // "N/A"')
STEP1_URL=$(echo "$RESPONSE" | jq -r '.[0].json.step1.youtube_url // "N/A"')
echo "  Task ID: $STEP1_TASK_ID"
echo "  Source: $STEP1_URL"
echo ""

# Step 2 info
echo "Step 2 (Voice Cloning + TTS):"
STEP2_SCRIPT=$(echo "$RESPONSE" | jq -r '.[0].json.step2.script // "N/A"')
STEP2_AUDIO_FILE=$(echo "$RESPONSE" | jq -r '.[0].json.step2.audio_file_name // "N/A"')
STEP2_MODEL=$(echo "$RESPONSE" | jq -r '.[0].json.step2.model // "N/A"')
STEP2_DURATION=$(echo "$RESPONSE" | jq -r '.[0].json.step2.duration_seconds // "N/A"')
echo "  Script: $STEP2_SCRIPT"
echo "  Audio file: $STEP2_AUDIO_FILE"
echo "  Model: $STEP2_MODEL"
echo "  Duration: ${STEP2_DURATION}s"
echo ""

# Step 3 info
echo "Step 3 (Portrait Generation):"
STEP3_PROMPT_ID=$(echo "$RESPONSE" | jq -r '.[0].json.step3.prompt_id // "N/A"')
STEP3_IMAGE_FILE=$(echo "$RESPONSE" | jq -r '.[0].json.step3.image_file_name // "N/A"')
STEP3_SEED=$(echo "$RESPONSE" | jq -r '.[0].json.step3.seed // "N/A"')
STEP3_PROMPT=$(echo "$RESPONSE" | jq -r '.[0].json.step3.portrait_prompt // "N/A"')
echo "  Prompt ID: $STEP3_PROMPT_ID"
echo "  Image file: $STEP3_IMAGE_FILE"
echo "  Seed: $STEP3_SEED"
echo "  Prompt: ${STEP3_PROMPT:0:100}..."
echo ""

# Check for binary data
echo "[3/3] Extracting binary data..."

# Check if response has binary data (n8n returns array of items with binary)
AUDIO_BINARY=$(echo "$RESPONSE" | jq -r '.[0].binary.audio.data // empty')
IMAGE_BINARY=$(echo "$RESPONSE" | jq -r '.[0].binary.image.data // empty')

if [ -z "$AUDIO_BINARY" ]; then
  echo "⚠️  Warning: No audio binary data found in response"
else
  echo "✅ Audio data found"
  AUDIO_OUTPUT="$TEST_OUTPUT_DIR/$STEP2_AUDIO_FILE"
  echo "$AUDIO_BINARY" | base64 -d > "$AUDIO_OUTPUT"
  AUDIO_SIZE=$(stat -f%z "$AUDIO_OUTPUT" 2>/dev/null || stat -c%s "$AUDIO_OUTPUT" 2>/dev/null)
  echo "   Saved to: $AUDIO_OUTPUT"
  echo "   Size: $(numfmt --to=iec-i --suffix=B $AUDIO_SIZE 2>/dev/null || echo ${AUDIO_SIZE} bytes)"

  # Get audio duration if ffprobe is available
  if command -v ffprobe > /dev/null; then
    ACTUAL_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$AUDIO_OUTPUT" 2>/dev/null)
    if [ -n "$ACTUAL_DURATION" ]; then
      echo "   Duration: ${ACTUAL_DURATION}s"
    fi
  fi
fi
echo ""

if [ -z "$IMAGE_BINARY" ]; then
  echo "⚠️  Warning: No image binary data found in response"
else
  echo "✅ Portrait image found"
  IMAGE_OUTPUT="$TEST_OUTPUT_DIR/$STEP3_IMAGE_FILE"
  echo "$IMAGE_BINARY" | base64 -d > "$IMAGE_OUTPUT"
  IMAGE_SIZE=$(stat -f%z "$IMAGE_OUTPUT" 2>/dev/null || stat -c%s "$IMAGE_OUTPUT" 2>/dev/null)
  echo "   Saved to: $IMAGE_OUTPUT"
  echo "   Size: $(numfmt --to=iec-i --suffix=B $IMAGE_SIZE 2>/dev/null || echo ${IMAGE_SIZE} bytes)"

  # Get image dimensions if 'file' command is available
  if command -v file > /dev/null; then
    FILE_INFO=$(file "$IMAGE_OUTPUT")
    echo "   Info: $FILE_INFO"
  fi

  # Get image dimensions if 'identify' (ImageMagick) is available
  if command -v identify > /dev/null; then
    DIMENSIONS=$(identify -format "%wx%h" "$IMAGE_OUTPUT" 2>/dev/null)
    if [ -n "$DIMENSIONS" ]; then
      echo "   Dimensions: $DIMENSIONS"
    fi
  fi
fi
echo ""

# Summary
echo "=================================================="
echo "✅ Steps 1-2-3 Pipeline Test Complete!"
echo "=================================================="
echo ""
echo "Summary:"
echo "  Total time: ${MINUTES}m ${SECONDS}s"
echo "  Step 1 task: $STEP1_TASK_ID"
echo "  Step 3 prompt: $STEP3_PROMPT_ID"
echo ""
echo "Output files:"
if [ -n "$AUDIO_BINARY" ]; then
  echo "  Audio: $AUDIO_OUTPUT"
fi
if [ -n "$IMAGE_BINARY" ]; then
  echo "  Image: $IMAGE_OUTPUT"
fi
echo ""
echo "Ready for Step 4 (Video Generation)!"
echo ""

# Save full response for debugging
RESPONSE_FILE="$TEST_OUTPUT_DIR/response_$(date +%Y%m%d_%H%M%S).json"
echo "$RESPONSE" | jq '.' > "$RESPONSE_FILE"
echo "Full response saved to: $RESPONSE_FILE"
echo ""

exit 0
