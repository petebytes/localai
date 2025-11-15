# Video Transcription Progress Tracking Setup

## Overview

The video transcription workflow now supports real-time progress updates via webhook callbacks. This allows users to see the progress of long-running transcription jobs without manually checking.

## Architecture

```
┌──────────┐         ┌─────────┐         ┌──────────────────┐         ┌──────────┐
│ Frontend │ ◄─poll─ │  Nginx  │ ◄─proxy─│ Progress Tracker │ ◄─POST─ │   n8n    │
└──────────┘         └─────────┘         └──────────────────┘         └──────────┘
     │                                            ▲                          │
     │                                            │                          │
     └─POST /process-video-file───────────────────────────────────────────►│
       {filepath, callback_url}                                              │
                                                                             │
                                                         Transcription ────►│
                                                                            ▼
                                                                      WhisperX
```

## Components

### 1. Progress Tracker Service (progress_tracker.py)
- **Purpose**: Receives webhook callbacks from n8n and makes them available to the frontend
- **Port**: 5555
- **Endpoints**:
  - `POST /api/progress-callback` - Receives progress updates from n8n
  - `GET /api/progress/{job_id}` - Returns current progress for a job
  - `GET /api/progress` - Lists all active jobs
  - `GET /health` - Health check

### 2. Updated n8n Workflow
- **File**: `n8n-video-transcription-workflow-fixed.json`
- **Features**:
  - Accepts `callback_url` parameter
  - Responds immediately with `job_id`
  - Sends progress updates at: 10%, 20%, 80%, 85%, 90%, 100%
  - Includes ETA estimates
  - Returns file paths on completion

### 3. Frontend (video-selector.html)
- **Features**:
  - Animated progress bar
  - Real-time stage updates
  - ETA display
  - Results display with download links
  - Polling fallback if webhooks fail

## Installation

### Step 1: Import Updated Workflow

1. Go to https://n8n.lan
2. Click "Workflows" → "Import from File"
3. Select `n8n-video-transcription-workflow-fixed.json`
4. The workflow will be updated with progress tracking

### Step 2: Start Services

```bash
# Stop existing services
docker compose -p localai down

# Start services with progress tracker
docker compose -p localai up -d

# Check progress tracker is running
docker logs progress-tracker

# Should see: "Starting Progress Tracker Service..."
```

### Step 3: Verify Endpoints

```bash
# Test progress tracker health
curl https://raven.lan/api/health

# Expected response:
# {
#   "status": "healthy",
#   "active_jobs": 0,
#   "service": "progress-tracker"
# }

# Test n8n workflow endpoint
curl https://n8n.lan/webhook/list-videos

# Should return list of videos
```

### Step 4: Access Frontend

Open https://raven.lan/video-selector.html

## Usage

### Processing a Video

1. **Select Video**: Choose a video from the dropdown
2. **Click "Process Video"**: Starts transcription
3. **View Progress**: Watch real-time progress updates
4. **Download Results**: Click download links when complete

### Progress Updates

The workflow sends progress updates at these stages:

| Progress | Stage | Message |
|----------|-------|---------|
| 10% | loading | Video file loaded from NAS |
| 20% | transcription | Starting audio transcription (ETA: ~6 minutes) |
| 80% | transcription | Transcription complete, processing results... |
| 85% | finalization | Formatting transcription data... |
| 90% | finalization | Saving transcription files... |
| 100% | complete | Transcription completed successfully |

### Example Progress Update

```json
{
  "job_id": "exec_12345",
  "status": "processing",
  "progress": 20,
  "stage": "transcription",
  "message": "Starting audio transcription (this may take several minutes)...",
  "eta_seconds": 400
}
```

### Completion Response

```json
{
  "job_id": "exec_12345",
  "status": "complete",
  "progress": 100,
  "stage": "complete",
  "message": "Transcription completed successfully",
  "result": {
    "filename": "my_video",
    "files": {
      "txt": "/nas/.../my_video.txt",
      "srt": "/nas/.../my_video.srt",
      "json": "/nas/.../my_video.json"
    }
  }
}
```

## API Reference

### Start Transcription

**Request:**
```bash
curl -X POST https://n8n.lan/webhook/process-video-file \
  -H "Content-Type: application/json" \
  -d '{
    "filepath": "/nas/videos/my-video.mp4",
    "callback_url": "https://raven.lan/api/progress-callback"
  }'
```

**Response:**
```json
{
  "job_id": "exec_12345",
  "status": "processing",
  "message": "Video transcription started"
}
```

### Get Progress

**Request:**
```bash
curl https://raven.lan/api/progress/exec_12345
```

**Response:**
```json
{
  "job_id": "exec_12345",
  "status": "processing",
  "progress": 50,
  "stage": "transcription",
  "message": "Processing audio...",
  "eta_seconds": 200
}
```

### List All Jobs

**Request:**
```bash
curl https://raven.lan/api/progress
```

**Response:**
```json
{
  "jobs": {
    "exec_12345": {
      "status": "processing",
      "progress": 50,
      "last_update": "2025-10-15T14:30:00"
    },
    "exec_67890": {
      "status": "complete",
      "progress": 100,
      "last_update": "2025-10-15T14:25:00"
    }
  },
  "count": 2
}
```

## Troubleshooting

### Progress Not Updating

**Symptom**: Progress bar stays at 0%

**Solutions**:
1. Check progress tracker is running:
   ```bash
   docker logs progress-tracker
   ```

2. Verify nginx can reach progress tracker:
   ```bash
   docker exec nginx curl http://progress-tracker:5555/health
   ```

3. Check browser console for errors:
   ```javascript
   // Should see polling requests
   GET /api/progress/exec_12345
   ```

### Callback URL Not Reachable

**Symptom**: n8n workflow errors on progress callbacks

**Solutions**:
1. Ensure callback URL uses HTTPS:
   ```json
   {"callback_url": "https://raven.lan/api/progress-callback"}
   ```

2. Check nginx proxy configuration:
   ```bash
   docker exec nginx cat /etc/nginx/conf.d/default.conf | grep -A 10 "location /api/"
   ```

3. Test callback endpoint directly:
   ```bash
   curl -X POST https://raven.lan/api/progress-callback \
     -H "Content-Type: application/json" \
     -d '{"job_id":"test","progress":50}'
   ```

### Transcription Timeout

**Symptom**: "timeout of 300000ms exceeded" error

**Solution**: This should be fixed! The workflow now has a 30-minute timeout. If you still see this:

1. Check n8n workflow timeout setting in "Send to WhisperX" node:
   ```json
   {
     "options": {
       "timeout": 1800000
     }
   }
   ```

2. Verify nginx timeout settings in nginx.conf:
   ```nginx
   proxy_read_timeout 3600;
   ```

### Old Jobs Accumulating

**Symptom**: Memory usage growing

**Solution**: Progress tracker automatically cleans up jobs older than 24 hours. To manually clear:

```bash
# Restart progress tracker
docker restart progress-tracker
```

## Monitoring

### View Active Jobs

```bash
curl https://raven.lan/api/progress | jq
```

### Monitor Progress Tracker Logs

```bash
docker logs -f progress-tracker

# Example output:
# [exec_12345] Progress update: 20% - Starting audio transcription...
# [exec_12345] Progress update: 80% - Transcription complete...
# [exec_12345] Progress update: 100% - Transcription completed successfully
```

### Monitor n8n Logs

```bash
docker logs -f n8n | grep "process-video-file"
```

## Configuration

### Adjust Polling Interval

Edit `video-selector.html`:

```javascript
// Change from 2 seconds to 5 seconds
progressPollInterval = setInterval(async () => {
    // ...
}, 5000); // was 2000
```

### Adjust Job Expiry

Edit `progress_tracker.py`:

```python
# Change from 24 hours to 12 hours
JOB_EXPIRY = 43200  # was 86400
```

### Adjust Progress Update Frequency

Edit n8n workflow to add more progress nodes at different stages.

## Advanced: Custom Progress Messages

You can customize progress messages in the n8n workflow. Edit any Progress node:

```json
{
  "jsonBody": {
    "job_id": "{{ $('Initialize Job').item.json.job_id }}",
    "status": "processing",
    "progress": 50,
    "stage": "custom-stage",
    "message": "Your custom message here",
    "eta_seconds": 300
  }
}
```

## Performance

- **Polling overhead**: ~1KB per request, every 2 seconds
- **Memory usage**: ~100KB per active job
- **Cleanup**: Automatic after 24 hours
- **Concurrent jobs**: Unlimited (memory permitting)

## Security

- **HTTPS only**: Callback URLs must use HTTPS
- **No authentication**: Currently open (add auth in production)
- **CORS**: Enabled for raven.lan origin
- **Rate limiting**: None (add nginx rate limiting in production)

## Future Enhancements

1. **WebSocket support**: Real-time updates without polling
2. **Authentication**: Secure progress endpoints
3. **Persistence**: Store progress in Redis/database
4. **WhisperX segment-level progress**: Show "Segment 57/63"
5. **Notifications**: Browser/email notifications on completion

## Related Documentation

- [WEBHOOK_CALLBACK_PATTERN.md](./WEBHOOK_CALLBACK_PATTERN.md) - Detailed webhook pattern guide
- [CLAUDE.md](./CLAUDE.md) - Repository overview
- WhisperX API documentation - See whisperx/api_server.py

## Support

For issues or questions:
1. Check docker logs: `docker logs progress-tracker`
2. Verify n8n workflow execution history
3. Test endpoints manually with curl
4. Review browser console for frontend errors
