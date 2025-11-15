# Webhook Callback Pattern for Long-Running Tasks

## Overview

This pattern enables real-time progress updates for long-running tasks without polling or job queues. The client provides a callback webhook URL, receives an immediate response with a job ID, then gets progress updates posted to their webhook as the task executes.

## Architecture

```
┌─────────┐                    ┌─────────┐                    ┌──────────┐
│ Client  │                    │   n8n   │                    │ WhisperX │
└────┬────┘                    └────┬────┘                    └────┬─────┘
     │                              │                              │
     │ POST /process-video          │                              │
     │ {filepath, callback_url}     │                              │
     ├─────────────────────────────>│                              │
     │                              │                              │
     │ 200 {job_id: "exec_123"}     │                              │
     │<─────────────────────────────┤                              │
     │                              │                              │
     │                              │ POST /transcribe-large       │
     │                              ├─────────────────────────────>│
     │                              │                              │
     │                              │                         [Processing]
     │                              │                              │
     │                              │<─── (logs: segment 10/63)────┤
     │                              │                              │
     │ POST callback_url            │                              │
     │ {progress: 15, segment: ...} │                              │
     │<─────────────────────────────┤                              │
     │                              │                              │
     │                              │<─── (logs: segment 30/63)────┤
     │                              │                              │
     │ POST callback_url            │                              │
     │ {progress: 47, segment: ...} │                              │
     │<─────────────────────────────┤                              │
     │                              │                              │
     │                              │<─── (complete)───────────────┤
     │                              │                              │
     │ POST callback_url            │                              │
     │ {progress: 100, status: ...} │                              │
     │<─────────────────────────────┤                              │
     │                              │                              │
```

## Workflow Implementation

### Step 1: Accept Callback URL

The webhook trigger accepts a `callback_url` parameter:

```json
{
  "filepath": "/nas/videos/my-video.mp4",
  "callback_url": "https://raven.lan/api/progress-callback"
}
```

### Step 2: Respond Immediately with Job ID

```javascript
// n8n Code Node: "Generate Job ID and Respond"
const executionId = $execution.id;
const callbackUrl = $('Process Video Webhook').item.json.body.callback_url;

// Store callback URL for later use
return [{
  json: {
    job_id: executionId,
    callback_url: callbackUrl,
    filepath: $('Process Video Webhook').item.json.body.filepath
  }
}];
```

**Respond to Webhook Node:**
```json
{
  "job_id": "{{ $('Generate Job ID and Respond').item.json.job_id }}",
  "status": "processing",
  "message": "Video transcription started"
}
```

### Step 3: Send Progress Updates

Insert HTTP Request nodes at key points in the workflow:

**Progress Update Node (10% - Starting):**
```json
{
  "method": "POST",
  "url": "={{ $('Generate Job ID and Respond').item.json.callback_url }}",
  "body": {
    "job_id": "={{ $('Generate Job ID and Respond').item.json.job_id }}",
    "status": "processing",
    "progress": 10,
    "stage": "extraction",
    "message": "Extracting audio from video..."
  }
}
```

**Progress Update Node (50% - Transcribing):**
```json
{
  "method": "POST",
  "url": "={{ $('Generate Job ID and Respond').item.json.callback_url }}",
  "body": {
    "job_id": "={{ $('Generate Job ID and Respond').item.json.job_id }}",
    "status": "processing",
    "progress": 50,
    "stage": "transcription",
    "message": "Transcribing audio (this may take several minutes)...",
    "eta_seconds": 300
  }
}
```

**Progress Update Node (90% - Finalizing):**
```json
{
  "method": "POST",
  "url": "={{ $('Generate Job ID and Respond').item.json.callback_url }}",
  "body": {
    "job_id": "={{ $('Generate Job ID and Respond').item.json.job_id }}",
    "status": "processing",
    "progress": 90,
    "stage": "finalization",
    "message": "Saving transcription files..."
  }
}
```

**Completion Callback:**
```json
{
  "method": "POST",
  "url": "={{ $('Generate Job ID and Respond').item.json.callback_url }}",
  "body": {
    "job_id": "={{ $('Generate Job ID and Respond').item.json.job_id }}",
    "status": "complete",
    "progress": 100,
    "stage": "complete",
    "message": "Transcription completed successfully",
    "result": {
      "filename": "={{ $('Process Transcription Data').item.json.filename }}",
      "files": {
        "txt": "/nas/PeggysExtraStorage/videos-to-process/processed/{{ $('Process Transcription Data').item.json.filename }}.txt",
        "srt": "/nas/PeggysExtraStorage/videos-to-process/processed/{{ $('Process Transcription Data').item.json.filename }}.srt",
        "json": "/nas/PeggysExtraStorage/videos-to-process/processed/{{ $('Process Transcription Data').item.json.filename }}.json"
      }
    }
  }
}
```

## Client Implementation

### Frontend: Create Callback Webhook

```javascript
// Add webhook endpoint to receive progress updates
const progressCallbacks = new Map();

app.post('/api/progress-callback', express.json(), (req, res) => {
  const { job_id, status, progress, message, stage, result } = req.body;

  console.log(`[${job_id}] ${stage}: ${progress}% - ${message}`);

  // Find the callback for this job
  const callback = progressCallbacks.get(job_id);
  if (callback) {
    callback({
      job_id,
      status,
      progress,
      message,
      stage,
      result
    });
  }

  // Clean up completed jobs
  if (status === 'complete' || status === 'error') {
    progressCallbacks.delete(job_id);
  }

  res.json({ received: true });
});
```

### Frontend: Submit Job with Callback

```javascript
async function processVideo(filepath, onProgress) {
  // Determine callback URL (must be accessible from n8n)
  const callbackUrl = `https://raven.lan/api/progress-callback`;

  // Submit job
  const response = await fetch('https://n8n.lan/webhook/process-video-file', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filepath,
      callback_url: callbackUrl
    })
  });

  const { job_id } = await response.json();

  // Register callback for progress updates
  progressCallbacks.set(job_id, onProgress);

  return job_id;
}

// Usage
const jobId = await processVideo('/nas/videos/video.mp4', (update) => {
  console.log(`Progress: ${update.progress}% - ${update.message}`);

  // Update UI
  progressBar.style.width = `${update.progress}%`;
  statusText.textContent = update.message;

  if (update.status === 'complete') {
    console.log('Transcription complete!', update.result);
    displayResults(update.result);
  }
});
```

### Example: React Component

```jsx
function VideoTranscription({ filepath }) {
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [stage, setStage] = useState('');
  const [result, setResult] = useState(null);

  const processVideo = async () => {
    const jobId = await processVideo(filepath, (update) => {
      setProgress(update.progress);
      setMessage(update.message);
      setStage(update.stage);

      if (update.status === 'complete') {
        setResult(update.result);
      }
    });
  };

  return (
    <div>
      <button onClick={processVideo}>Start Transcription</button>

      <div className="progress-container">
        <div className="progress-bar" style={{ width: `${progress}%` }} />
        <div className="progress-text">{progress}%</div>
      </div>

      <div className="status">
        <span className="stage">{stage}</span>
        <span className="message">{message}</span>
      </div>

      {result && (
        <div className="results">
          <h3>Transcription Complete!</h3>
          <ul>
            <li><a href={result.files.txt}>Plain Text</a></li>
            <li><a href={result.files.srt}>Subtitles (SRT)</a></li>
            <li><a href={result.files.json}>JSON with Timestamps</a></li>
          </ul>
        </div>
      )}
    </div>
  );
}
```

## Benefits

1. **No Polling**: Client doesn't waste resources checking status
2. **Real-Time**: Updates arrive as soon as they're available
3. **Simple**: No job queue infrastructure needed
4. **Scalable**: Each job is independent
5. **Flexible**: Can send detailed progress information

## Error Handling

**Error Callback:**
```json
{
  "job_id": "exec_123",
  "status": "error",
  "progress": 45,
  "stage": "transcription",
  "message": "Transcription failed: timeout exceeded",
  "error": {
    "code": "TIMEOUT",
    "details": "WhisperX did not respond within 30 minutes"
  }
}
```

**Frontend Error Handling:**
```javascript
progressCallbacks.set(job_id, (update) => {
  if (update.status === 'error') {
    console.error('Job failed:', update.error);
    showErrorNotification(update.message);
    progressCallbacks.delete(job_id);
  }
});
```

## Security Considerations

1. **Validate Callback URLs**: Only allow HTTPS URLs from trusted domains
2. **Timeout Protection**: Set maximum callback retry attempts
3. **Authentication**: Include a secret token in callback requests
4. **Rate Limiting**: Prevent callback spam

**Authenticated Callback:**
```javascript
// n8n: Include auth header
{
  "headers": {
    "Authorization": "Bearer {{ $('Generate Job ID and Respond').item.json.callback_token }}"
  }
}

// Client: Verify token
app.post('/api/progress-callback', (req, res) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!isValidToken(token)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  // ... handle callback
});
```

## Advanced: Dynamic Progress from WhisperX Logs

For more granular progress, we could enhance WhisperX to expose segment progress:

**WhisperX Enhancement (Future):**
```python
# In api_server.py
for i, seg in enumerate(segments):
    progress_percent = int((i / len(segments)) * 80) + 10  # 10-90%

    # Write progress to shared file
    progress_file = SHARED_DIR / f"progress_{job_id}.json"
    progress_file.write_text(json.dumps({
        "segment": i + 1,
        "total_segments": len(segments),
        "progress": progress_percent,
        "current_time": seg.start,
        "duration": duration
    }))

    logger.info(f"Transcribing segment {i+1}/{len(segments)}")
    result = transcribe_audio_segment(...)
```

**n8n: Poll Progress File:**
```javascript
// Code node to read progress
const fs = require('fs');
const jobId = $('Generate Job ID and Respond').item.json.job_id;
const progressFile = `/data/shared/progress_${jobId}.json`;

if (fs.existsSync(progressFile)) {
  const progress = JSON.parse(fs.readFileSync(progressFile, 'utf8'));
  return [{ json: progress }];
}
```

This would allow for segment-by-segment progress updates!
