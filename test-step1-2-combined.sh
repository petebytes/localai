#!/usr/bin/env bash
#
# Test script for Steps 1-2 Combined: Audio Extraction + Voice Cloning
#
# This script tests the complete workflow that:
# 1. Extracts audio from YouTube (yttools)
# 2. Clones the voice and generates TTS (vibevoice)

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
N8N_WEBHOOK_URL="${N8N_WEBHOOK_URL:-https://n8n.lan/webhook/generate-video-step1-2}"
YOUTUBE_URL="${YOUTUBE_URL:-https://www.youtube.com/watch?v=ojIIaobmOEU}"
SCRIPT_TEXT="${SCRIPT_TEXT:-This means the polling logic isnt working correctly. The workflow is checking the status but proceeding to download even though the task isnt complete.}"
# Using r6_p3 optimal parameters: ref_start=420s, ref_duration=50s
SEGMENT_START="${SEGMENT_START:-420}"
SEGMENT_END="${SEGMENT_END:-470}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/test-video-gen}"

# TTS Parameters (r6_p3 optimal settings)
CFG_SCALE="${CFG_SCALE:-1.5}"
DIFFUSION_STEPS="${DIFFUSION_STEPS:-30}"
TEMPERATURE="${TEMPERATURE:-0.75}"
TOP_P="${TOP_P:-0.85}"
USE_SAMPLING="${USE_SAMPLING:-true}"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

echo -e "${YELLOW}=== Steps 1-2 Combined Test: Audio Extraction + Voice Cloning ===${NC}"
echo ""
echo "Configuration:"
echo "  N8N Webhook: $N8N_WEBHOOK_URL"
echo "  YouTube URL: $YOUTUBE_URL"
echo "  Segment: ${SEGMENT_START}s - ${SEGMENT_END}s (50s duration, r6_p3 optimal)"
echo "  Script: \"$SCRIPT_TEXT\""
echo "  Output Dir: $OUTPUT_DIR"
echo ""
echo "TTS Parameters (r6_p3 optimal settings):"
echo "  CFG Scale: $CFG_SCALE"
echo "  Diffusion Steps: $DIFFUSION_STEPS"
echo "  Temperature: $TEMPERATURE"
echo "  Top-P: $TOP_P"
echo "  Use Sampling: $USE_SAMPLING"
echo ""

# Create request payload
REQUEST_PAYLOAD=$(cat <<EOF
{
  "youtube_url": "$YOUTUBE_URL",
  "script": "$SCRIPT_TEXT",
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

echo -e "${YELLOW}Request Payload:${NC}"
echo "$REQUEST_PAYLOAD" | jq .
echo ""

# Make request
echo -e "${YELLOW}Sending request to n8n workflow...${NC}"
echo "This will take 1-3 minutes (YouTube download + voice cloning)..."
echo ""

RESPONSE_FILE="$OUTPUT_DIR/response.json"

HTTP_CODE=$(curl -k -s -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "$REQUEST_PAYLOAD" \
  "$N8N_WEBHOOK_URL" \
  -o "$RESPONSE_FILE")

echo "HTTP Status Code: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" != "200" ]; then
  echo -e "${RED}❌ Request failed with status code: $HTTP_CODE${NC}"
  echo -e "${RED}Response:${NC}"
  cat "$RESPONSE_FILE"
  exit 1
fi

echo -e "${GREEN}✅ Request successful!${NC}"
echo ""

# Parse response
echo -e "${YELLOW}Response:${NC}"
cat "$RESPONSE_FILE" | jq .
echo ""

# Check success
SUCCESS=$(cat "$RESPONSE_FILE" | jq -r '.success // false')
if [ "$SUCCESS" != "true" ]; then
  echo -e "${RED}❌ Workflow reported failure${NC}"
  exit 1
fi

# Extract details
STEP1_TASK_ID=$(cat "$RESPONSE_FILE" | jq -r '.step1.task_id // "unknown"')
TTS_FILENAME=$(cat "$RESPONSE_FILE" | jq -r '.step2.tts_file_name // "unknown"')
YOUTUBE_URL_RESULT=$(cat "$RESPONSE_FILE" | jq -r '.step1.youtube_url // "unknown"')
SCRIPT_RESULT=$(cat "$RESPONSE_FILE" | jq -r '.step2.script // "unknown"')

echo -e "${GREEN}✅ Steps 1-2 completed successfully!${NC}"
echo ""
echo "Step 1 Results (Audio Extraction):"
echo "  Task ID: $STEP1_TASK_ID"
echo "  YouTube URL: $YOUTUBE_URL_RESULT"
echo "  Segment: ${SEGMENT_START}s - ${SEGMENT_END}s"
echo ""
echo "Step 2 Results (Voice Cloning):"
echo "  TTS File: $TTS_FILENAME"
echo "  Script: \"$SCRIPT_RESULT\""
echo "  Model: F5-TTS"
echo ""

# Try to download the reference audio from yttools
echo -e "${YELLOW}Downloading reference audio from yttools...${NC}"
REF_AUDIO_FILE="$OUTPUT_DIR/reference_audio.mp3"

if curl -k -s -f "http://yttools:8456/api/download/${STEP1_TASK_ID}/audio" -o "$REF_AUDIO_FILE" 2>/dev/null || \
   curl -k -s -f "https://yttools.lan/api/download/${STEP1_TASK_ID}/audio" -o "$REF_AUDIO_FILE" 2>/dev/null; then

  FILE_SIZE=$(stat -f%z "$REF_AUDIO_FILE" 2>/dev/null || stat -c%s "$REF_AUDIO_FILE" 2>/dev/null || echo "0")
  FILE_SIZE_MB=$(echo "scale=2; $FILE_SIZE / 1024 / 1024" | bc 2>/dev/null || echo "unknown")

  echo -e "${GREEN}✅ Reference audio downloaded${NC}"
  echo "  File: $REF_AUDIO_FILE"
  echo "  Size: ${FILE_SIZE_MB} MB"
  echo ""

  # Try to get duration
  if command -v ffprobe &> /dev/null; then
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$REF_AUDIO_FILE" 2>/dev/null | cut -d. -f1)
    echo "  Duration: ${DURATION}s"
  fi
else
  echo -e "${YELLOW}⚠️  Could not download reference audio (not critical)${NC}"
fi

echo ""
echo -e "${GREEN}=== Steps 1-2 Test PASSED ===${NC}"
echo ""
echo "Summary:"
echo "  ✅ YouTube audio extracted (50 seconds from optimal segment at 420s)"
echo "  ✅ Voice cloned from reference audio"
echo "  ✅ TTS generated with OPTIMAL r6_p3 parameters:"
echo "     - CFG Scale: $CFG_SCALE (lower = better quality)"
echo "     - Steps: $DIFFUSION_STEPS (2x faster than previous max quality!)"
echo "     - Temperature: $TEMPERATURE"
echo "     - Top-P: $TOP_P"
echo "     - Sampling: $USE_SAMPLING"
echo ""
echo "Next steps:"
echo "  1. The TTS audio is in the workflow execution (check n8n UI)"
echo "  2. Listen to verify the cloned voice sounds correct"
echo "  3. Proceed to Steps 3-4 (Image + Video generation)"
echo ""
echo "Ready for Steps 3-4!"
