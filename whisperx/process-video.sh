#!/usr/bin/env bash
set -euo pipefail

# Process video transcription using WhisperX API
# Usage: ./process-video.sh <video_file_path>

readonly WHISPER_URL="https://whisper.lan/transcribe-large"
readonly OUTPUT_DIR="/mnt/raven-nas/videos-to-process/processed"

# Helper function to format time as HH:MM:SS,mmm for SRT
format_srt_time() {
    local seconds="$1"
    local hours minutes secs milliseconds

    hours=$(printf "%.0f" "$(echo "$seconds / 3600" | bc -l)")
    minutes=$(printf "%.0f" "$(echo "($seconds % 3600) / 60" | bc -l)")
    secs=$(printf "%.0f" "$(echo "$seconds % 60" | bc -l)")
    milliseconds=$(printf "%.0f" "$(echo "($seconds - int($seconds)) * 1000" | bc -l)")

    printf "%02d:%02d:%02d,%03d" "$hours" "$minutes" "$secs" "$milliseconds"
}

# Validate input
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <video_file_path>" >&2
    echo "Example: $0 /mnt/raven-nas/videos-to-process/myvideo.mp4" >&2
    exit 1
fi

readonly VIDEO_PATH="$1"

if [[ ! -f "$VIDEO_PATH" ]]; then
    echo "Error: Video file not found: $VIDEO_PATH" >&2
    exit 1
fi

# Extract filename without extension
readonly FILENAME=$(basename "$VIDEO_PATH")
readonly CLEAN_FILENAME=$(echo "${FILENAME%.*}" | tr -cs '[:alnum:]-_' '_')

echo "Processing: $FILENAME"
echo "Output name: $CLEAN_FILENAME"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Upload to WhisperX and get transcription
echo "Uploading to WhisperX API..."
readonly TEMP_JSON=$(mktemp)
trap "rm -f '$TEMP_JSON'" EXIT

if ! curl -k -X POST "$WHISPER_URL" \
    -F "file=@$VIDEO_PATH" \
    -o "$TEMP_JSON" \
    --fail \
    --show-error \
    --progress-bar; then
    echo "Error: WhisperX API request failed" >&2
    exit 1
fi

echo "Transcription complete. Processing output..."

# Save full JSON
readonly JSON_OUTPUT="$OUTPUT_DIR/${CLEAN_FILENAME}.json"
cp "$TEMP_JSON" "$JSON_OUTPUT"
echo "Saved: $JSON_OUTPUT"

# Generate plain text transcript
readonly TXT_OUTPUT="$OUTPUT_DIR/${CLEAN_FILENAME}.txt"
jq -r '.segments[]? | .text' "$TEMP_JSON" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' > "$TXT_OUTPUT"
echo "Saved: $TXT_OUTPUT"

# Generate SRT subtitle file
readonly SRT_OUTPUT="$OUTPUT_DIR/${CLEAN_FILENAME}.srt"
{
    local index=1
    jq -c '.segments[]?' "$TEMP_JSON" | while IFS= read -r segment; do
        local start=$(echo "$segment" | jq -r '.start')
        local end=$(echo "$segment" | jq -r '.end')
        local text=$(echo "$segment" | jq -r '.text' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

        echo "$index"
        echo "$(format_srt_time "$start") --> $(format_srt_time "$end")"
        echo "$text"
        echo ""

        index=$((index + 1))
    done
} > "$SRT_OUTPUT"
echo "Saved: $SRT_OUTPUT"

echo ""
echo "Processing complete!"
echo "Generated files:"
echo "  - $TXT_OUTPUT"
echo "  - $SRT_OUTPUT"
echo "  - $JSON_OUTPUT"
