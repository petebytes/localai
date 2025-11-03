#!/usr/bin/env bash
#
# Test Video 5 (Winner) with Parameter Variations
# 50 samples: varying reference duration (20-60s) and VibeVoice parameters
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
N8N_WEBHOOK_URL="${N8N_WEBHOOK_URL:-https://n8n.lan/webhook/generate-video-step1-2}"
SCRIPT_TEXT="${SCRIPT_TEXT:-This is a test of voice cloning quality using different reference audio samples from Peggy Oliveira videos.}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/video5-optimization}"
RESULTS_FILE="$OUTPUT_DIR/results.csv"

mkdir -p "$OUTPUT_DIR"

# Winner video
VIDEO_URL="https://www.youtube.com/watch?v=ojIIaobmOEU"

# 10 different reference audio segments (20-60 seconds)
# Format: start_time:duration
declare -A REFERENCE_SEGMENTS=(
    [0]="60:20"      # 1 min, 20s
    [1]="120:25"     # 2 min, 25s
    [2]="180:30"     # 3 min, 30s
    [3]="240:35"     # 4 min, 35s
    [4]="300:40"     # 5 min, 40s (includes the winning segment)
    [5]="360:45"     # 6 min, 45s
    [6]="420:50"     # 7 min, 50s
    [7]="480:55"     # 8 min, 55s
    [8]="540:60"     # 9 min, 60s
    [9]="90:30"      # 1.5 min, 30s (different position)
)

# 5 different parameter combinations
# Format: "cfg_scale,diffusion_steps,temperature,top_p,use_sampling"
declare -A PARAM_SETS=(
    [0]="2.0,50,0.85,0.95,true"     # Current (high quality)
    [1]="1.8,40,0.80,0.90,true"     # Slightly lower
    [2]="2.0,60,0.90,0.95,true"     # Higher diffusion
    [3]="1.5,30,0.75,0.85,true"     # Faster/lower quality
    [4]="2.0,50,0.85,0.95,false"    # No sampling
)

echo -e "${YELLOW}=== Video 5 Optimization Test ===${NC}"
echo ""
echo "Testing winner video with parameter variations"
echo "10 reference segments × 5 parameter sets = 50 samples"
echo "Reference durations: 20-60 seconds"
echo "Output: $OUTPUT_DIR"
echo ""

echo "sample_id,ref_start,ref_duration,cfg_scale,diffusion_steps,temperature,top_p,use_sampling,success,error_message,output_file,timestamp" > "$RESULTS_FILE"

total_tests=0
successful_tests=0
failed_tests=0

for ref_idx in {0..9}; do
    segment="${REFERENCE_SEGMENTS[$ref_idx]}"
    segment_start=$(echo "$segment" | cut -d: -f1)
    segment_duration=$(echo "$segment" | cut -d: -f2)
    segment_end=$((segment_start + segment_duration))

    echo -e "${BLUE}=== Reference Segment $((ref_idx + 1))/10: ${segment_start}s-${segment_end}s (${segment_duration}s) ===${NC}"

    for param_idx in {0..4}; do
        params="${PARAM_SETS[$param_idx]}"
        IFS=',' read -r cfg_scale diffusion_steps temperature top_p use_sampling <<< "$params"

        sample_id="r${ref_idx}_p${param_idx}"
        total_tests=$((total_tests + 1))

        echo -e "${YELLOW}  Sample ${sample_id}: cfg=${cfg_scale}, steps=${diffusion_steps}, temp=${temperature}${NC}"

        request_payload=$(cat <<EOF
{
  "youtube_url": "$VIDEO_URL",
  "script": "$SCRIPT_TEXT",
  "segment_start": $segment_start,
  "segment_end": $segment_end,
  "cfg_scale": $cfg_scale,
  "diffusion_steps": $diffusion_steps,
  "temperature": $temperature,
  "top_p": $top_p,
  "use_sampling": $use_sampling
}
EOF
)

        response_file="$OUTPUT_DIR/${sample_id}_response.json"
        audio_file="$OUTPUT_DIR/${sample_id}_cloned.mp3"

        http_code=$(curl -k -s -w "%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "$request_payload" \
            "$N8N_WEBHOOK_URL" \
            -o "$response_file" \
            --max-time 300 2>&1 || echo "000")

        timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

        if [ "$http_code" = "200" ]; then
            if file "$response_file" | grep -q "JSON"; then
                success=$(cat "$response_file" | jq -r '.success // false' 2>/dev/null || echo "false")
                if [ "$success" = "true" ]; then
                    echo -e "    ${GREEN}✓ Success${NC}"
                    successful_tests=$((successful_tests + 1))
                    echo "$sample_id,$segment_start,$segment_duration,$cfg_scale,$diffusion_steps,$temperature,$top_p,$use_sampling,true,,$audio_file,$timestamp" >> "$RESULTS_FILE"
                else
                    error_msg=$(cat "$response_file" | jq -r '.error // .message // "Unknown error"' 2>/dev/null || echo "Unknown error")
                    echo -e "    ${RED}✗ Error: $error_msg${NC}"
                    failed_tests=$((failed_tests + 1))
                    echo "$sample_id,$segment_start,$segment_duration,$cfg_scale,$diffusion_steps,$temperature,$top_p,$use_sampling,false,\"$error_msg\",,$timestamp" >> "$RESULTS_FILE"
                fi
            else
                mv "$response_file" "$audio_file"
                file_size=$(stat -c%s "$audio_file" 2>/dev/null || stat -f%z "$audio_file" 2>/dev/null || echo "0")
                file_size_kb=$((file_size / 1024))
                echo -e "    ${GREEN}✓ Success (${file_size_kb} KB)${NC}"
                successful_tests=$((successful_tests + 1))
                echo "$sample_id,$segment_start,$segment_duration,$cfg_scale,$diffusion_steps,$temperature,$top_p,$use_sampling,true,,$audio_file,$timestamp" >> "$RESULTS_FILE"
            fi
        else
            echo -e "    ${RED}✗ HTTP $http_code${NC}"
            failed_tests=$((failed_tests + 1))
            echo "$sample_id,$segment_start,$segment_duration,$cfg_scale,$diffusion_steps,$temperature,$top_p,$use_sampling,false,\"HTTP $http_code\",,$timestamp" >> "$RESULTS_FILE"
        fi

        sleep 2
    done
    echo ""
done

echo -e "${GREEN}=== Test Complete ===${NC}"
echo ""
echo "Total tests: $total_tests"
echo "Successful: $successful_tests"
echo "Failed: $failed_tests"
echo "Success rate: $(echo "scale=1; $successful_tests * 100 / $total_tests" | bc 2>/dev/null || echo "N/A")%"
echo ""
echo "Results saved to: $RESULTS_FILE"
echo "Audio files in: $OUTPUT_DIR"
echo ""
echo "Next: Generate comparison page with:"
echo "  python3 /home/ghar/code/localai/generate-video5-comparison.py"
