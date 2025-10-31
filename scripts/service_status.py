#!/usr/bin/env python3
"""
Service Status API
Provides Docker container status, backup information, and health checks.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import subprocess
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
CORS(app)

BACKUP_DIR = '/backup'


def run_docker_command(args):
    """Run a docker CLI command and return the output."""
    try:
        result = subprocess.run(
            ['docker'] + args,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Docker command failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error running docker command: {e}")
        return None


@app.route('/api/containers', methods=['GET'])
def get_containers():
    """
    Get status of all Docker containers.
    Returns container name, status, health, and uptime.
    """
    try:
        # Get container list in JSON format
        output = run_docker_command([
            'ps', '-a',
            '--format', '{"name":"{{.Names}}","status":"{{.Status}}","state":"{{.State}}","image":"{{.Image}}"}'
        ])

        if not output:
            return jsonify({'error': 'Failed to get container list'}), 500

        containers = []
        for line in output.split('\n'):
            if line.strip():
                try:
                    container = json.loads(line)
                    containers.append(container)
                except json.JSONDecodeError:
                    continue

        return jsonify({
            'containers': containers,
            'count': len(containers),
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        print(f"Error getting containers: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/backups', methods=['GET'])
def get_backups():
    """
    List available backups from the backup directory.
    """
    try:
        backup_path = Path(BACKUP_DIR)

        if not backup_path.exists():
            return jsonify({
                'backups': [],
                'count': 0,
                'message': 'Backup directory not found'
            }), 200

        backups = []
        for backup_file in backup_path.glob('backup-*.tar.gz'):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

        # Sort by creation time, newest first
        backups.sort(key=lambda x: x['created'], reverse=True)

        return jsonify({
            'backups': backups,
            'count': len(backups),
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        print(f"Error listing backups: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """
    Health check endpoint.
    """
    try:
        # Check if docker is accessible
        docker_ok = run_docker_command(['version', '--format', '{{.Server.Version}}']) is not None

        return jsonify({
            'status': 'healthy' if docker_ok else 'degraded',
            'docker': 'ok' if docker_ok else 'error',
            'service': 'service-status',
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        print(f"Error in health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/', methods=['GET'])
def index():
    """Service info"""
    return jsonify({
        'service': 'Service Status API',
        'version': '1.0.0',
        'endpoints': {
            'GET /api/containers': 'List all Docker containers with status',
            'GET /api/backups': 'List available backup files',
            'GET /api/health': 'Health check'
        }
    }), 200


if __name__ == '__main__':
    print("Starting Service Status API...")
    print("Providing container status, backups, and health information")
    app.run(host='0.0.0.0', port=80, debug=False)
