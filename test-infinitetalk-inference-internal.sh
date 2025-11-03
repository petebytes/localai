#!/bin/bash
# Test InfiniteTalk API inference from inside the container

set -e

echo "Testing InfiniteTalk API inference..."
echo "======================================"
echo ""

# Create request JSON
cat > /tmp/infinitetalk-request.json <<'EOF'
{
  "audio_path": "/data/shared/n8n/audio-7sec.mp3",
  "image_path": "/data/shared/n8n/peggy-cartoon.png",
  "prompt": "",
  "resolution": "infinitetalk-480",
  "seed": 42,
  "diffusion_steps": 20,
  "text_guide_scale": 5.0,
  "audio_guide_scale": 4.0,
  "motion_frame": 9,
  "use_color_correction": true
}
EOF

echo "Request payload:"
cat /tmp/infinitetalk-request.json | python3 -m json.tool
echo ""
echo ""

echo "1. Checking API health..."
docker exec infinitetalk-api curl -s http://localhost:8200/api/health | python3 -m json.tool
echo ""
echo ""

echo "2. Generating video..."
docker exec infinitetalk-api curl -X POST http://localhost:8200/api/generate-video \
  -H "Content-Type: application/json" \
  -d "$(cat /tmp/infinitetalk-request.json)" \
  -w "\n\nHTTP Status: %{http_code}\n" | tee /tmp/infinitetalk-response.json

echo ""
echo ""
echo "Response:"
cat /tmp/infinitetalk-response.json | python3 -m json.tool

echo ""
echo "======================================"
echo "Test completed!"
