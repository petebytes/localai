#!/bin/bash
# Test InfiniteTalk API inference with n8n audio and image files

set -e

API_URL="http://localhost:8200"
AUDIO_FILE="/data/shared/n8n/audio.mp3"
IMAGE_FILE="/data/shared/n8n/peggy-cartoon.png"

echo "Testing InfiniteTalk API inference..."
echo "======================================"
echo ""
echo "Audio file: $AUDIO_FILE"
echo "Image file: $IMAGE_FILE"
echo ""

# Test health endpoint first
echo "1. Checking API health..."
curl -s "$API_URL/api/health" | python3 -m json.tool
echo ""
echo ""

# Generate video with default parameters
echo "2. Generating video..."
echo "Request payload:"
cat <<EOF | tee /tmp/infinitetalk-request.json
{
  "audio_path": "$AUDIO_FILE",
  "image_path": "$IMAGE_FILE",
  "prompt": "",
  "resolution": "infinitetalk-480",
  "seed": 42,
  "diffusion_steps": 40,
  "text_guide_scale": 5.0,
  "audio_guide_scale": 4.0,
  "motion_frame": 9,
  "use_color_correction": true
}
EOF

echo ""
echo ""
echo "Sending request to API..."
curl -X POST "$API_URL/api/generate-video" \
  -H "Content-Type: application/json" \
  -d @/tmp/infinitetalk-request.json \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -o /tmp/infinitetalk-response.json

echo ""
echo "Response:"
cat /tmp/infinitetalk-response.json | python3 -m json.tool

echo ""
echo "======================================"
echo "Test completed!"
