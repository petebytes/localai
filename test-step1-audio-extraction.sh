#!/usr/bin/env bash
#
# Test script for Step 1: YouTube Audio Extraction
#
# This script tests the n8n workflow that extracts audio from YouTube videos
# using the yttools service.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
N8N_WEBHOOK_URL="${N8N_WEBHOOK_URL:-https://n8n.lan/webhook/extract-youtube-audio}"
YOUTUBE_URL="${YOUTUBE_URL:-https://www.youtube.com/watch?v=ao8f3qyMoLM}"
SEGMENT_START="${SEGMENT_START:-40}"
SEGMENT_END="${SEGMENT_END:-70}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/test-audio}"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

echo -e "${YELLOW}=== Step 1: YouTube Audio Extraction Test ===${NC}"
echo ""
echo "Configuration:"
echo "  N8N Webhook: $N8N_WEBHOOK_URL"
echo "  YouTube URL: $YOUTUBE_URL"
echo "  Segment: ${SEGMENT_START}s - ${SEGMENT_END}s (${SEGMENT_END}-${SEGMENT_START} = $((SEGMENT_END - SEGMENT_START))s)"
echo "  Output Dir: $OUTPUT_DIR"
echo ""

# Create request payload
REQUEST_PAYLOAD=$(cat <<EOF
{
  "youtube_url": "$YOUTUBE_URL",
  "segment_start": $SEGMENT_START,
  "segment_end": $SEGMENT_END
}
EOF
)

echo -e "${YELLOW}Request Payload:${NC}"
echo "$REQUEST_PAYLOAD" | jq .
echo ""

# Make request
echo -e "${YELLOW}Sending request to n8n workflow...${NC}"
RESPONSE_FILE="$OUTPUT_DIR/response.json"
AUDIO_FILE="$OUTPUT_DIR/extracted_audio.mp3"

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

# Check if response indicates success
SUCCESS=$(cat "$RESPONSE_FILE" | jq -r '.success // false')
if [ "$SUCCESS" != "true" ]; then
  echo -e "${RED}❌ Workflow reported failure${NC}"
  exit 1
fi

# Extract task info
TASK_ID=$(cat "$RESPONSE_FILE" | jq -r '.task_id // "unknown"')
FILE_NAME=$(cat "$RESPONSE_FILE" | jq -r '.file_name // "unknown"')
DURATION=$(cat "$RESPONSE_FILE" | jq -r '.duration_seconds // 0')

echo -e "${GREEN}✅ Audio extracted successfully!${NC}"
echo ""
echo "Details:"
echo "  Task ID: $TASK_ID"
echo "  File Name: $FILE_NAME"
echo "  Duration: ${DURATION}s"
echo "  Segment: ${SEGMENT_START}s - ${SEGMENT_END}s"
echo ""

# Verify duration
EXPECTED_DURATION=$((SEGMENT_END - SEGMENT_START))
if [ "$DURATION" -eq "$EXPECTED_DURATION" ]; then
  echo -e "${GREEN}✅ Duration matches expected: ${DURATION}s${NC}"
else
  echo -e "${YELLOW}⚠️  Duration mismatch: expected ${EXPECTED_DURATION}s, got ${DURATION}s${NC}"
fi
echo ""

# Check if we can download the audio file from yttools directly
echo -e "${YELLOW}Attempting to download audio file from yttools...${NC}"
YTTOOLS_DOWNLOAD_URL="https://yttools.lan/api/download/${TASK_ID}/audio"

if curl -k -s -f "$YTTOOLS_DOWNLOAD_URL" -o "$AUDIO_FILE"; then
  echo -e "${GREEN}✅ Audio file downloaded successfully!${NC}"

  # Check file size
  FILE_SIZE=$(stat -f%z "$AUDIO_FILE" 2>/dev/null || stat -c%s "$AUDIO_FILE" 2>/dev/null || echo "0")
  FILE_SIZE_MB=$(echo "scale=2; $FILE_SIZE / 1024 / 1024" | bc 2>/dev/null || echo "unknown")

  echo "  File: $AUDIO_FILE"
  echo "  Size: ${FILE_SIZE_MB} MB"

  # Try to get audio duration using ffprobe if available
  if command -v ffprobe &> /dev/null; then
    ACTUAL_DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$AUDIO_FILE" 2>/dev/null | cut -d. -f1)
    echo "  Actual Duration (ffprobe): ${ACTUAL_DURATION}s"

    if [ "$ACTUAL_DURATION" -eq "$EXPECTED_DURATION" ] || [ "$ACTUAL_DURATION" -eq "$((EXPECTED_DURATION + 1))" ] || [ "$ACTUAL_DURATION" -eq "$((EXPECTED_DURATION - 1))" ]; then
      echo -e "${GREEN}✅ Audio duration verified!${NC}"
    else
      echo -e "${YELLOW}⚠️  Audio duration mismatch: expected ~${EXPECTED_DURATION}s, got ${ACTUAL_DURATION}s${NC}"
    fi
  else
    echo -e "${YELLOW}⚠️  ffprobe not found, cannot verify audio duration${NC}"
    echo "  Install ffmpeg to enable duration verification"
  fi

  echo ""
  echo -e "${GREEN}=== Step 1 Test PASSED ===${NC}"
  echo ""
  echo "Next steps:"
  echo "  1. Listen to the audio file: $AUDIO_FILE"
  echo "  2. Verify it contains the correct segment (40-70s)"
  echo "  3. If everything looks good, proceed to Step 2 (Voice Cloning)"

else
  echo -e "${RED}❌ Failed to download audio file${NC}"
  exit 1
fi
