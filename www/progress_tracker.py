#!/usr/bin/env python3
"""
Progress Tracker Service
Receives webhook callbacks from n8n and makes progress available to the frontend.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# In-memory storage for progress updates
# Format: {job_id: {update_data, timestamp}}
progress_store = {}
lock = threading.Lock()

# Cleanup old jobs after 24 hours
CLEANUP_INTERVAL = 3600  # 1 hour
JOB_EXPIRY = 86400  # 24 hours


def cleanup_old_jobs():
    """Remove jobs older than JOB_EXPIRY seconds"""
    while True:
        time.sleep(CLEANUP_INTERVAL)
        with lock:
            now = datetime.now()
            expired_jobs = [
                job_id
                for job_id, data in progress_store.items()
                if (now - data["timestamp"]).total_seconds() > JOB_EXPIRY
            ]
            for job_id in expired_jobs:
                del progress_store[job_id]
                print(f"Cleaned up expired job: {job_id}")


# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_jobs, daemon=True)
cleanup_thread.start()


@app.route("/api/progress-callback", methods=["POST", "OPTIONS"])
def progress_callback():
    """
    Receive progress updates from n8n workflow.

    Expected JSON body:
    {
        "job_id": "exec_12345",
        "status": "processing|complete|error",
        "progress": 50,
        "stage": "transcription",
        "message": "Processing...",
        "eta_seconds": 300,
        "result": {...}
    }
    """
    if request.method == "OPTIONS":
        return "", 204

    try:
        update = request.get_json()

        if not update or "job_id" not in update:
            return jsonify({"error": "Missing job_id"}), 400

        job_id = update["job_id"]

        # Store update with timestamp
        with lock:
            progress_store[job_id] = {"update": update, "timestamp": datetime.now()}

        print(
            f"[{job_id}] Progress update: {update.get('progress', 0)}% - {update.get('message', '')}"
        )

        return jsonify({"received": True, "job_id": job_id}), 200

    except Exception as e:
        print(f"Error handling progress callback: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/progress/<job_id>", methods=["GET"])
def get_progress(job_id):
    """
    Get current progress for a job.
    Frontend polls this endpoint for updates.
    """
    with lock:
        if job_id in progress_store:
            return jsonify(progress_store[job_id]["update"]), 200
        else:
            # Return pending status instead of 404 to handle race condition
            # where frontend polls before first progress update arrives
            return jsonify(
                {
                    "job_id": job_id,
                    "status": "pending",
                    "progress": 0,
                    "stage": "initializing",
                    "message": "Job started, waiting for first update...",
                }
            ), 200


@app.route("/api/progress", methods=["GET"])
def list_jobs():
    """List all active jobs"""
    with lock:
        jobs = {
            job_id: {
                "status": data["update"].get("status"),
                "progress": data["update"].get("progress", 0),
                "last_update": data["timestamp"].isoformat(),
            }
            for job_id, data in progress_store.items()
        }
    return jsonify({"jobs": jobs, "count": len(jobs)}), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "active_jobs": len(progress_store),
            "service": "progress-tracker",
        }
    ), 200


@app.route("/", methods=["GET"])
def index():
    """Service info"""
    return jsonify(
        {
            "service": "Progress Tracker Service",
            "version": "1.0.0",
            "endpoints": {
                "POST /api/progress-callback": "Receive progress updates from n8n",
                "GET /api/progress/<job_id>": "Get progress for specific job",
                "GET /api/progress": "List all active jobs",
                "GET /health": "Health check",
            },
        }
    ), 200


if __name__ == "__main__":
    print("Starting Progress Tracker Service...")
    print("Listening for webhook callbacks from n8n")
    app.run(host="0.0.0.0", port=5555, debug=False)
