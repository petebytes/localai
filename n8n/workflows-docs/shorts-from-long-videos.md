# YouTube Shorts Generation Workflow - Technical Documentation

## Overview

This n8n workflow automates the process of converting long-form YouTube videos into multiple short-form vertical video clips (YouTube Shorts) optimized for mental health and trauma recovery content. It uses AI to identify high-impact moments, extracts clips, adds dynamic subtitles with word-level highlighting, and outputs ready-to-publish vertical videos.

**Target Channel:** Peggy Oliveira, MSW - Trauma recovery and mental health education
**Brand Voice:** Compassionate, Validating, Authoritative, Healing-Focused

## Architecture

The workflow consists of 6 main stages:

1. **Input & Download Stage** - Receives YouTube URL, downloads video/audio
2. **Transcription Stage** - Generates accurate timestamps via WhisperX
3. **AI Analysis Stage** - Identifies 5-7 high-impact clips using Claude Sonnet 4.5
4. **Clip Extraction Stage** - Extracts individual video segments
5. **Subtitle Generation Stage** - Creates sentence-aware word-by-word captions
6. **Final Assembly Stage** - Applies subtitles and outputs finished shorts

---

## Detailed Stage Breakdown

### Stage 1: Input & Download (Nodes 1-15)

**Entry Point:** `YouTube Download Webhook` (POST endpoint)

#### Input Parameters
```json
{
  "youtube_url": "https://youtube.com/watch?v=...",  // Required
  "segment_start": 120,                               // Optional: start time in seconds
  "segment_end": 300                                  // Optional: end time in seconds
}
```

#### Process Flow

1. **`Validate Input`** (Code Node)
   - Validates YouTube URL format
   - Ensures segment_end > segment_start if provided
   - Returns error if validation fails

2. **`Submit to yttools`** (HTTP Request)
   - Sends download request to yttools service at `http://yttools:8456/api/download`
   - Requests both video (mp4) and audio (wav)
   - Enables WhisperX transcription
   - Timeout: 60 seconds
   - Returns `task_id` for polling

3. **`Extract Task ID`** (Code Node)
   - Extracts task_id from yttools response
   - Initializes polling counter (max 120 polls = ~6 minutes)

4. **Polling Loop** (`Wait 3s` → `Check Status` → `Check Completion`)
   - Polls yttools every 3 seconds
   - Checks for completion/failure status
   - Throws error on timeout or failure
   - Loops back if still processing

5. **Download Assets** (Parallel Downloads when complete)
   - `Download WhisperX JSON` - Full transcription with word-level timestamps
   - `Download Segment SRT` - Sentence-level subtitles
   - `Download Video` - MP4 file
   - `Download Audio` - WAV file (not used in current flow)

6. **File Processing**
   - `Extract WhisperX JSON Content` → `Parse WhisperX JSON` → `Write WhisperX JSON to Temp`
   - `Extract SRT Content` → `Write SRT to Temp`
   - `Write Video to Temp` (at `/tmp/video_{task_id}.mp4`)

**Key Files Generated:**
- `/tmp/video_{task_id}.mp4` - Original video
- `/tmp/video_{task_id}.srt` - Segment-level SRT
- `/tmp/whisperx_{task_id}.json` - Word-level transcription data

---

### Stage 2: AI Clip Identification (Nodes 16-20)

**AI Model:** Claude Sonnet 4.5 (via Anthropic API)

#### Process Flow

1. **`Stage 1: Clip Identification`** (AI Agent Node)

   **System Prompt Strategy:**
   - Positioned as "Specialist Short-Form Video Producer"
   - Analyzes SRT subtitle file to identify 5-7 powerful clips (15-60 seconds each)
   - Brand-specific criteria:
     - **Aha! Moments:** Clear psychological term definitions
     - **Validating Statements:** Direct empathy ("It was not your fault")
     - **Relatable Questions:** Powerful hooks ("Do you ever find yourself...?")
     - **Perspective Shifts:** Reframing negative beliefs
   - Avoids academic content, dependent context, listicle formats

2. **`Stage 1: Output Parser`** (Structured Output Parser)

   **JSON Schema Enforced:**
   ```json
   {
     "clips": [
       {
         "clip_number": 1,
         "title_hook": "Why You're Not Broken",
         "clip_type": "Perspective Shift",
         "timestamp_start": "00:02:15,340",
         "timestamp_end": "00:02:48,120",
         "full_text": "Complete word-for-word transcript...",
         "directors_note": "Powerful reframe explaining trauma response"
       }
     ],
     "analysis_summary": "Overall video content summary"
   }
   ```

3. **`Check If Clips Found`** (If Node)
   - **True Path:** Proceeds to clip extraction
   - **False Path:** `Format No Clips Response` → Returns analysis explaining why no clips found

4. **`Parse AI Clips`** (Code Node)
   - Converts AI output to internal format
   - Adds synthetic text_styling fields for subtitles:
     - `hook_title_overlay` - Title broken into lines
     - `power_words` - Extracted emotional keywords
     - `cta_start_timestamp` - When to show CTA (last 8 seconds)
     - `cta_promise_text` - "Watch the full video:"
   - Sanitizes titles for filenames
   - Calculates duration from timestamps

**Output Structure:**
```javascript
{
  clips: [
    {
      index: 1,
      title: "Why You're Not Broken",
      title_sanitized: "why_youre_not_broken",
      type: "Perspective Shift",
      type_sanitized: "perspective_shift",
      start_timestamp: "00:02:15,340",
      end_timestamp: "00:02:48,120",
      start_seconds: 135.34,
      end_seconds: 168.12,
      duration: 32.78,
      text: "Full transcript...",
      notes: "Director's note...",
      text_styling: { /* styling config */ }
    }
  ],
  total_clips: 5,
  task_id: "abc123",
  youtube_url: "https://..."
}
```

---

### Stage 3: Preparation & Directory Setup (Nodes 21-26)

1. **`Merge Temp File Results`** (Merge Node)
   - Combines outputs from WhisperX JSON, SRT, Video file writes, and AI clips
   - Uses "combine by position" mode with 4 inputs

2. **`Extract Clips Data`** (Code Node)
   - Extracts clips array from merged data
   - Preserves task_id and youtube_url

3. **`Add Temp Paths to Data`** (Code Node)
   - Adds file path references:
     - `video_path`: `/tmp/video_{task_id}.mp4`
     - `srt_path`: `/tmp/video_{task_id}.srt`

4. **Directory Creation** (Sequential)
   - `Create Output Directory`: `mkdir -p /mnt/raven-nas/videos-to-process/processed/shorts`
   - `Create Scratch Directory`: `mkdir -p /mnt/raven-nas/videos-to-process/scratch`

5. **`Wait for Directory Creation`** (Code Node)
   - Ensures directories exist before proceeding

6. **`Split Out Clips`** (Split Out Node)
   - Splits clips array into individual items
   - Each clip now processes independently in parallel

---

### Stage 4: Clip Extraction (Nodes 27-29) - Per Clip

**Filename Pattern:** `{videoId}_clip_{index}__{type}.mp4`

1. **`Prepare ffmpeg Command`** (Code Node per clip)

   Generates two key paths:
   - `output_path_nosubs`: `/nas/.../scratch/{base_filename}_nosubs.mp4` (intermediate)
   - `output_path_final`: `/nas/.../processed/shorts/{base_filename}.mp4` (final output)

   **FFmpeg Command Generated:**
   ```bash
   ffmpeg -y -i "/tmp/video_{task_id}.mp4" \
       -ss {start_seconds} \
       -to {end_seconds} \
       -vf "crop=ih*9/16:ih" \
       -c:v libx264 -crf 23 -preset fast \
       -c:a aac -b:a 128k \
       -movflags +faststart \
       "/nas/.../scratch/{filename}_nosubs.mp4"
   ```

   **Key Transformations:**
   - `-ss` / `-to`: Extract time segment
   - `-vf "crop=ih*9/16:ih"`: Crop to 9:16 vertical format (1080x1920)
   - `-c:v libx264 -crf 23`: H.264 encoding, quality 23
   - `-preset fast`: Balance speed/compression
   - `-c:a aac -b:a 128k`: AAC audio at 128kbps
   - `-movflags +faststart`: Web-optimized (metadata at front)

2. **`Extract Video Clip`** (Execute Command)
   - Runs the ffmpeg command
   - Creates clip WITHOUT subtitles (subtitles added later)

3. **`Read Clip Video File`** (Read Binary File)
   - Loads the extracted clip into n8n binary data
   - Prepares for transcription

---

### Stage 5: Per-Clip Transcription & Subtitle Generation (Nodes 30-33)

**Critical Design:** Each SHORT clip is re-transcribed independently for precise word-level timing

1. **`Transcribe Short Video with WhisperX`** (HTTP Request)

   **Endpoint:** `http://whisperx:8000/transcribe`

   **Parameters:**
   - `file`: Binary video data
   - `model`: "base" (WhisperX model)
   - `enable_diarization`: false
   - Timeout: 120 seconds

   **Why Re-transcribe?**
   - Original transcription has timestamps relative to full video
   - Clip timestamps start at 00:00:00
   - WhisperX provides word-level timing for each clip independently

2. **`Parse WhisperX Clip Response`** (Code Node)

   **Extracts:**
   - `whisperx_segments`: Array of segments with word-level timing
   - `whisperx_srt`: Standard SRT format
   - `whisperx_segments_srt`: Segment-aware SRT
   - `whisperx_txt`: Plain text transcript
   - `clip_language`: Detected language
   - `num_segments`: Segment count

3. **`Generate Sentence-Aware ASS Subtitles`** (Code Node) 🎨

   **This is the magic node** - Creates dynamic karaoke-style subtitles

   **Configuration Constants:**
   ```javascript
   const CONFIG = {
     wordsToShow: 3,                    // Show 3 words at a time
     fontSize: 80,                       // Base font size
     highlightFontSize: 100,             // Highlighted word (25% larger)
     fontColor: 'FFFFFF',                // White
     highlightColor: '00FFFF',           // Cyan
     outlineColor: '000000',             // Black outline
     outline: 8,                         // Outline thickness
     alignment: 2,                       // Bottom center
     marginV: 300,                       // 300px from bottom
     videoWidth: 1080,                   // 9:16 format
     videoHeight: 1920,
     maxGapTimeMs: 2000,                 // Fill gaps < 2s

     // Hook title (opening overlay)
     hookTitleFontSize: 120,
     hookTitleColor: 'FFFF00',           // Yellow
     hookTitleDuration: 2.0,             // Show for 2 seconds
     hookTitleAlignment: 5,              // Center screen

     // CTA (ending overlay)
     ctaFontSize: 90,
     ctaColor: 'FF00FF',                 // Magenta
     ctaDuration: 8.0,                   // Last 8 seconds
     ctaAlignment: 8                     // Top center
   };
   ```

   **Subtitle Generation Algorithm:**

   a) **Extract all words** from WhisperX segments
   b) **Create sentence-aware groups:**
      - Groups end at periods OR after `wordsToShow` words
      - Maintains semantic coherence
   c) **Generate dialogue line per word:**
      - Each word gets its own timing
      - Text shows current 3-word group with current word highlighted
      - Example: `Hello {\\fs100\\c&H00FFFF&}world{\\r} today`
   d) **Fill timing gaps:**
      - If gap < 2 seconds between words in same group, extend duration
      - Prevents flicker
   e) **Add hook title overlay** (Layer 1):
      - Shows at start for 2 seconds
      - Uses `hook_title_overlay` from AI analysis
   f) **Add CTA overlay** (Layer 2):
      - Shows for last 8 seconds
      - "Watch the full video:" text

   **ASS File Structure:**
   ```
   [Script Info]
   Title: Sentence-Aware Fixed Position Subtitles with Hook and CTA
   PlayResX: 1080
   PlayResY: 1920

   [V4+ Styles]
   Style: Default,Arial,80,&HFFFFFF,...
   Style: HookTitle,Arial,120,&HFFFF00,...
   Style: CTA,Arial,90,&HFF00FF,...

   [Events]
   Dialogue: 1,0:00:00.00,0:00:02.00,HookTitle,,0,0,0,,Why You're\NNot Broken\n
   Dialogue: 0,0:00:00.00,0:00:00.45,Default,,0,0,0,,{\fs100\c&H00FFFF&}You{\r} are not
   Dialogue: 0,0:00:00.45,0:00:00.82,Default,,0,0,0,,You {\fs100\c&H00FFFF&}are{\r} not
   ...
   Dialogue: 2,0:00:24.00,0:00:32.00,CTA,,0,0,0,,Watch the full video\n
   ```

4. **`Write ASS File to Scratch`** (Write Binary File)
   - Saves ASS file to `/nas/.../scratch/subtitle_clip_{task_id}_{index}.ass`

---

### Stage 6: Final Assembly (Nodes 34-38) - Per Clip

1. **`Build Final ffmpeg Command`** (Code Node)

   **FFmpeg Command Generated:**
   ```bash
   ffmpeg -y -i "/nas/.../scratch/{filename}_nosubs.mp4" \
       -vf "ass='/nas/.../scratch/subtitle_clip_{task_id}_{index}.ass'" \
       -c:v libx264 -crf 23 -preset fast \
       -c:a copy \
       -movflags +faststart \
       "/nas/.../processed/shorts/{filename}.mp4"
   ```

   **Key Points:**
   - Takes the no-subs video as input
   - Burns in ASS subtitles via `-vf "ass='...'"`
   - Re-encodes video with subtitles baked in
   - Copies audio stream (no re-encoding)

2. **`Apply Subtitles to Video`** (Execute Command)
   - Runs the final ffmpeg command
   - Creates finished short video

3. **`Verify Clip Created`** (Code Node)
   - Checks ffmpeg exit code
   - Returns success/failure status per clip
   - Includes file paths and metadata

4. **`Aggregate Clip Results`** (Code Node)
   - Waits for ALL clips to complete
   - Collects success/failure counts
   - Compiles list of output files

5. **`Format Success Response`** (Code Node)

   **Final Response Structure:**
   ```json
   {
     "status": "success",
     "clips_found": true,
     "clips_extracted": 5,
     "total_clips_attempted": 5,
     "analysis": "{AI output JSON}",
     "extracted_shorts": [
       {
         "index": 1,
         "title": "Why You're Not Broken",
         "path_nosubs": "/nas/.../scratch/video_clip_01_perspective_shift_nosubs.mp4",
         "path_final": "/nas/.../processed/shorts/video_clip_01_perspective_shift.mp4",
         "duration": 32.78
       }
     ],
     "storage_path_final": "/nas/.../processed/shorts",
     "storage_path_nosubs": "/nas/.../scratch",
     "message": "Successfully extracted 5 short video clips with sentence-aware subtitles",
     "errors": []
   }
   ```

6. **`Respond to Webhook1`** (Respond to Webhook)
   - Returns final JSON response to caller
   - Completes the workflow

---

## Technical Specifications

### Video Output Specs
- **Format:** MP4 (H.264 + AAC)
- **Resolution:** 1080x1920 (9:16 vertical)
- **Video Codec:** libx264, CRF 23, preset fast
- **Audio Codec:** AAC, 128 kbps
- **Optimization:** faststart flag for web streaming

### Subtitle Styling Specs
- **Font:** Arial
- **Base Size:** 80px
- **Highlight Size:** 100px (25% larger)
- **Colors:**
  - Base text: White (#FFFFFF)
  - Highlight: Cyan (#00FFFF)
  - Hook title: Yellow (#FFFF00)
  - CTA: Magenta (#FF00FF)
- **Outline:** 8px black border for readability
- **Position:** 300px from bottom, center-aligned
- **Behavior:** 3-word groups, word-by-word highlighting

### Performance Characteristics
- **Parallel Processing:** Each clip processes independently
- **Timeouts:**
  - yttools download: 60s
  - yttools polling: 120 polls × 3s = 6 minutes max
  - File downloads: 30s each
  - WhisperX transcription: 120s per clip
- **Storage:**
  - Scratch directory: Intermediate files (nosubs videos, ASS files)
  - Final directory: Published shorts

---

## Dependencies

### External Services
1. **yttools** (`http://yttools:8456`)
   - YouTube download service
   - WhisperX integration
   - Video/audio extraction

2. **WhisperX** (`http://whisperx:8000`)
   - Word-level speech transcription
   - Diarization support (not used)
   - Multiple model options

3. **Anthropic API**
   - Claude Sonnet 4.5 model
   - Structured output generation
   - Content analysis

### System Tools
- **ffmpeg:** Video processing, cropping, subtitle burning
- **Node.js:** n8n runtime
- **File system:** NAS storage at `/mnt/raven-nas/`

---

## Error Handling

### Validation Errors
- Missing YouTube URL → Returns error immediately
- Invalid URL format → Returns error immediately
- Invalid time segments → Returns error immediately

### Processing Errors
- yttools timeout (6 min) → Throws error
- yttools task failure → Throws error with details
- No clips found → Returns structured "no clips" response
- ffmpeg failure → Tracked per clip, reported in errors array

### Partial Success
- If 3/5 clips succeed, returns success with:
  - `successful_clips: 3`
  - `failed_clips: 2`
  - `errors: [{clip details}]`

---

## Usage Example

### Input
```bash
curl -X POST http://n8n-host/webhook/ca6bda83-afc4-4845-9b0f-834adfbe7b95 \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=ao8f3qyMoLM"
  }'
```

### Output
```json
{
  "status": "success",
  "clips_found": true,
  "clips_extracted": 5,
  "total_clips_attempted": 5,
  "extracted_shorts": [
    {
      "index": 1,
      "title": "Understanding Emotional Flashbacks",
      "path_final": "/mnt/raven-nas/videos-to-process/processed/shorts/dQw4w9WgXcQ_clip_01_aha_moment.mp4",
      "duration": 28.5
    },
    {
      "index": 2,
      "title": "It's Not Your Fault",
      "path_final": "/mnt/raven-nas/videos-to-process/processed/shorts/dQw4w9WgXcQ_clip_02_validating_statement.mp4",
      "duration": 22.3
    }
  ],
  "message": "Successfully extracted 5 short video clips with sentence-aware subtitles"
}
```

---

## Key Design Decisions

### 1. Two-Pass Transcription
**Decision:** Re-transcribe each extracted clip
**Rationale:**
- Original timestamps relative to full video
- Clips need timestamps starting at 00:00:00
- WhisperX provides precise word-level timing
- Enables accurate subtitle synchronization

### 2. Sentence-Aware Grouping
**Decision:** Group words by sentences, not fixed count
**Rationale:**
- Maintains semantic coherence
- Prevents awkward mid-sentence breaks
- More natural reading experience
- Better comprehension for viewers

### 3. Two-File Output Strategy
**Decision:** Save both nosubs and final versions
**Rationale:**
- Debugging: Can verify extraction before subtitles
- Flexibility: Can regenerate subtitles without re-extracting
- Quality control: Separate subtitle styling iterations
- Storage trade-off accepted for workflow resilience

### 4. ASS vs SRT Format
**Decision:** Use ASS (Advanced SubStation Alpha)
**Rationale:**
- Precise styling control (fonts, colors, sizes)
- Multiple style layers (hook, captions, CTA)
- Word-level highlighting effects
- Position control (fixed bottom placement)
- SRT format too limited for karaoke effect

### 5. AI-Driven Clip Selection
**Decision:** Claude Sonnet 4.5 with structured output
**Rationale:**
- Human-quality editorial judgment
- Brand voice consistency
- Context-aware selection (not just keyword matching)
- Structured output ensures parseable results
- Reduces manual curation time from hours to seconds

### 6. Parallel Clip Processing
**Decision:** Process all clips simultaneously
**Rationale:**
- Maximizes throughput
- Independent clips don't need serialization
- n8n handles concurrency automatically
- Total time = slowest clip (not sum of all)

---

## Monitoring & Maintenance

### Key Metrics to Track
- Average clips per video (target: 5-7)
- Clip success rate (target: >95%)
- Processing time per clip
- yttools download success rate
- WhisperX transcription accuracy

### Common Maintenance Tasks
1. **Update subtitle styling:** Modify CONFIG object in node 32
2. **Adjust AI criteria:** Update prompt in node 23
3. **Change video format:** Modify ffmpeg commands in nodes 28, 35
4. **Update storage paths:** Change in nodes 25, 26

### Logs to Monitor
- yttools API errors
- WhisperX transcription failures
- ffmpeg encoding errors
- Low clip count warnings (<3 clips)

---

## Future Enhancements

### Potential Improvements
1. **Stage 2: Visual Analysis**
   - Analyze facial expressions for emotional peaks
   - Detect on-screen text overlays
   - Identify B-roll vs talking head segments

2. **Stage 2.5: Clip Refinement**
   - A/B test different hooks for same clip
   - Generate multiple CTA variations
   - Optimize clip duration based on engagement data

3. **Background Music**
   - Add healing/meditation background audio
   - Dynamic mixing based on voice presence
   - Brand-consistent sonic identity

4. **Thumbnail Generation**
   - Extract key frame from clip
   - Add title overlay
   - Export as JPEG for upload

5. **Direct YouTube Upload**
   - YouTube Data API integration
   - Scheduled publishing
   - Metadata optimization (title, description, tags)

6. **Analytics Integration**
   - Track which clip types perform best
   - A/B test subtitle styles
   - Optimize AI prompt based on engagement

---

## Troubleshooting Guide

### Workflow Fails at yttools Download
- Check yttools service health
- Verify YouTube URL is accessible (not geo-blocked, not removed)
- Check network connectivity to YouTube
- Verify disk space on yttools server

### No Clips Found
- Review AI analysis in response
- Video may not contain suitable teaching content
- Try different segment of video
- Adjust AI prompt criteria if consistently failing

### Subtitle Timing Off
- Verify WhisperX transcription quality
- Check clip audio clarity (background noise?)
- Adjust `maxGapTimeMs` in CONFIG if flicker occurs
- Verify video frame rate matches expected (30fps)

### FFmpeg Errors
- Check ASS file syntax (malformed can crash ffmpeg)
- Verify input video is valid (not corrupted)
- Check disk space on output directory
- Review ffmpeg stderr in error response

---

## Conclusion

This workflow represents a sophisticated AI-powered video production pipeline that combines:
- **Content Intelligence:** AI editorial judgment for clip selection
- **Technical Precision:** Word-level transcription and subtitle synchronization
- **Brand Consistency:** Automated styling aligned with channel identity
- **Production Scale:** Parallel processing for rapid turnaround

**Key Achievement:** Transforms a 60-minute video into 5-7 polished, vertical, subtitled short videos in under 10 minutes, with zero manual editing required.

**Success Criteria:**
- ✅ Clips are self-contained and emotionally impactful
- ✅ Subtitles are readable and synchronized
- ✅ Visual format optimized for mobile (9:16)
- ✅ Brand voice maintained throughout
- ✅ Output ready for immediate publishing
