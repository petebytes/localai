#!/bin/bash

# Test script for Step 3: WAN Portrait Generation via ComfyUI API
# Tests the wan-portrait-gen-single-frame.json workflow

set -e

COMFYUI_URL="http://localhost:18188"
WORKFLOW_FILE="n8n/comfyui/wan-portrait-api-format.json"
TEST_PROMPT="${1:-Professional portrait photograph of a business speaker, studio lighting, high resolution, centered composition, neutral background, photorealistic, detailed facial features, professional attire, confident expression}"

echo "=================================================="
echo "Step 3: WAN Portrait Generation Test"
echo "=================================================="
echo ""
echo "ComfyUI URL: $COMFYUI_URL"
echo "Workflow: $WORKFLOW_FILE"
echo "Prompt: $TEST_PROMPT"
echo ""

# Check if ComfyUI is running
echo "[1/6] Checking ComfyUI availability..."
if ! curl -s -f "$COMFYUI_URL/" > /dev/null; then
    echo "❌ ERROR: ComfyUI is not accessible at $COMFYUI_URL"
    exit 1
fi
echo "✅ ComfyUI is running"
echo ""

# Check if workflow file exists
echo "[2/6] Checking workflow file..."
if [ ! -f "$WORKFLOW_FILE" ]; then
    echo "❌ ERROR: Workflow file not found: $WORKFLOW_FILE"
    exit 1
fi
echo "✅ Workflow file found"
echo ""

# Load workflow and update prompt
echo "[3/6] Preparing workflow with custom prompt..."
WORKFLOW=$(cat "$WORKFLOW_FILE")

# Update the positive prompt in the workflow (node id 6) - API format
WORKFLOW=$(echo "$WORKFLOW" | jq --arg prompt "$TEST_PROMPT" '
    ."6".inputs.text = $prompt
')

# Randomize seed
RANDOM_SEED=$RANDOM$RANDOM
WORKFLOW=$(echo "$WORKFLOW" | jq --arg seed "$RANDOM_SEED" '
    ."3".inputs.seed = ($seed | tonumber)
')

echo "✅ Workflow prepared with seed: $RANDOM_SEED"
echo ""

# Submit prompt to ComfyUI
echo "[4/6] Submitting workflow to ComfyUI..."
PROMPT_PAYLOAD=$(jq -n --argjson workflow "$WORKFLOW" '{prompt: $workflow}')

RESPONSE=$(curl -s -X POST "$COMFYUI_URL/prompt" \
    -H "Content-Type: application/json" \
    -d "$PROMPT_PAYLOAD")

PROMPT_ID=$(echo "$RESPONSE" | jq -r '.prompt_id // empty')

if [ -z "$PROMPT_ID" ]; then
    echo "❌ ERROR: Failed to submit workflow"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "✅ Workflow submitted successfully"
echo "   Prompt ID: $PROMPT_ID"
echo ""

# Poll for completion
echo "[5/6] Waiting for generation to complete..."
echo "   Expected time: 1.5-3 minutes (14B model on RTX 5090)"
echo ""

MAX_POLLS=60  # 5 minutes max (5 second intervals)
POLL_COUNT=0
START_TIME=$(date +%s)

while [ $POLL_COUNT -lt $MAX_POLLS ]; do
    sleep 5
    POLL_COUNT=$((POLL_COUNT + 1))
    ELAPSED=$(($(date +%s) - START_TIME))

    # Check history
    HISTORY=$(curl -s "$COMFYUI_URL/history/$PROMPT_ID")
    STATUS=$(echo "$HISTORY" | jq -r ".[\"$PROMPT_ID\"].status.status_str // \"unknown\"")

    if echo "$HISTORY" | jq -e ".[\"$PROMPT_ID\"].outputs" > /dev/null 2>&1; then
        echo "✅ Generation complete! (${ELAPSED}s)"
        echo ""

        # Extract output image information
        OUTPUT=$(echo "$HISTORY" | jq -r ".[\"$PROMPT_ID\"].outputs")

        # Find the SaveImage node output (node 49)
        IMAGE_INFO=$(echo "$OUTPUT" | jq -r '.["49"].images[0] // empty')

        if [ -z "$IMAGE_INFO" ]; then
            echo "⚠️  Warning: Could not find image in output"
            echo "Full output: $OUTPUT"
        else
            FILENAME=$(echo "$IMAGE_INFO" | jq -r '.filename')
            SUBFOLDER=$(echo "$IMAGE_INFO" | jq -r '.subfolder')
            TYPE=$(echo "$IMAGE_INFO" | jq -r '.type')

            echo "📸 Generated Image:"
            echo "   Filename: $FILENAME"
            echo "   Subfolder: $SUBFOLDER"
            echo "   Type: $TYPE"
            echo ""

            # Construct view URL
            VIEW_URL="$COMFYUI_URL/view?filename=$FILENAME&subfolder=$SUBFOLDER&type=$TYPE"
            echo "   View URL: $VIEW_URL"
            echo ""

            # Try to download the image
            echo "[6/6] Downloading generated image..."
            OUTPUT_FILE="./test-outputs/portrait_${RANDOM_SEED}.png"
            mkdir -p ./test-outputs

            if curl -s -o "$OUTPUT_FILE" "$VIEW_URL"; then
                FILE_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null)
                if [ "$FILE_SIZE" -gt 1000 ]; then
                    echo "✅ Image downloaded successfully"
                    echo "   Location: $OUTPUT_FILE"
                    echo "   Size: $(numfmt --to=iec-i --suffix=B $FILE_SIZE 2>/dev/null || echo ${FILE_SIZE} bytes)"
                    echo ""

                    # If we have 'file' command, show image details
                    if command -v file > /dev/null; then
                        echo "   Details: $(file "$OUTPUT_FILE")"
                        echo ""
                    fi
                else
                    echo "⚠️  Downloaded file is too small ($FILE_SIZE bytes)"
                fi
            else
                echo "⚠️  Failed to download image"
            fi
        fi

        echo "=================================================="
        echo "✅ Step 3 Test Complete!"
        echo "=================================================="
        echo "Generation time: ${ELAPSED}s"
        echo "Prompt ID: $PROMPT_ID"
        echo ""
        exit 0
    fi

    # Show progress
    printf "\r   Polling... %ds elapsed (poll %d/%d)" "$ELAPSED" "$POLL_COUNT" "$MAX_POLLS"
done

echo ""
echo ""
echo "❌ ERROR: Generation timed out after ${ELAPSED}s"
echo "   Prompt ID: $PROMPT_ID"
echo "   Last status: $STATUS"
echo ""
echo "Check ComfyUI UI at $COMFYUI_URL for details"
exit 1
