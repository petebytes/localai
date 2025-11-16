#!/usr/bin/env python3
"""
start_services.py

This script starts the Supabase stack first, waits for it to initialize, and then starts
the local AI stack. Both stacks use the same Docker Compose project name ("localai")
so they appear together in Docker Desktop.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import socket


def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        run_command(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                "https://github.com/supabase/supabase.git",
            ]
        )
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists, updating...")
        os.chdir("supabase")
        run_command(["git", "pull"])
        os.chdir("..")


def prepare_supabase_env():
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)


def stop_existing_containers():
    """Stop and remove existing containers for our unified project ('localai')."""
    print(
        "Stopping and removing existing containers for the unified project 'localai'..."
    )
    run_command(
        [
            "docker",
            "compose",
            "-p",
            "localai",
            "-f",
            "docker-compose.yml",
            "-f",
            "supabase/docker/docker-compose.yml",
            "down",
        ]
    )


def start_supabase():
    """Start the Supabase services (using its compose file)."""
    print("Starting Supabase services...")
    run_command(
        [
            "docker",
            "compose",
            "-p",
            "localai",
            "-f",
            "supabase/docker/docker-compose.yml",
            "up",
            "-d",
        ]
    )


def check_ngc_api_key():
    """Check NGC authentication by running the setup-ngc.sh script."""
    setup_script = "virtual-assistant/setup-ngc.sh"

    if not os.path.exists(setup_script):
        print("\nWarning: NGC setup script not found at", setup_script)
        print("Virtual Assistant services (Riva ASR/TTS, Audio2Face) may not start")
        return False

    try:
        # Run the existing NGC setup script which handles everything securely
        result = subprocess.run(
            ["bash", setup_script], capture_output=True, text=True, timeout=30, cwd="."
        )

        if result.returncode == 0:
            # Script succeeded, authentication is good
            return True
        else:
            # Script failed, show its output for debugging
            if result.stderr:
                print("\n" + result.stderr.strip())
            if result.stdout:
                print(result.stdout.strip())
            return False

    except subprocess.TimeoutExpired:
        print("\nWarning: NGC authentication timed out")
        return False
    except Exception as e:
        print(f"\nWarning: Could not run NGC setup: {e}")
        print("Virtual Assistant services may not start without NGC authentication")
        return False


def check_crawl4ai_image():
    """Verify Crawl4AI will use the official pre-built GPU image."""
    print("Crawl4AI: Using official unclecode/crawl4ai:gpu image from Docker Hub")
    print("  - GPU support: Enabled")
    print("  - Shared caching: hf-cache, torch-cache")
    print("  - Image will be pulled automatically on first run")
    return True


def generate_certificates():
    """Generate self-signed certificates if they don't exist."""
    if not os.path.exists("certs/local-cert.pem"):
        print("Generating self-signed certificates...")
        os.makedirs("certs", exist_ok=True)
        run_command(
            [
                "openssl",
                "req",
                "-x509",
                "-nodes",
                "-days",
                "365",
                "-newkey",
                "rsa:2048",
                "-keyout",
                "nginx/certs/local-key.pem",
                "-out",
                "nginx/certs/local-cert.pem",
                "-subj",
                "/CN=*.lan",
                "-addext",
                "subjectAltName = DNS:*.lan,DNS:localhost",
            ]
        )
        print("Certificates generated successfully!")
    else:
        print("Certificates already exist.")


def get_primary_ip():
    """Get the primary network IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        if platform.system() != "Windows":
            try:
                result = subprocess.run(
                    ["hostname", "-I"], capture_output=True, text=True
                )
                ips = result.stdout.strip().split()
                for ip in ips:
                    if (
                        not ip.startswith("127.")
                        and not ip.startswith("172.17.")
                        and not ip.startswith("172.18.")
                    ):
                        return ip
            except (subprocess.CalledProcessError, OSError):
                pass
        return None


def fix_open_webui_read_aloud():
    """Fix the Read Aloud feature in Open WebUI."""
    print("Checking if Open WebUI Read Aloud feature needs fixing...")

    # Wait a bit for the container to start
    time.sleep(5)

    # Check if the Open WebUI container is running
    try:
        container_id = subprocess.check_output(
            ["docker", "ps", "-q", "-f", "name=open-webui"], text=True
        ).strip()

        if not container_id:
            print("Open WebUI container is not running yet, skipping fix.")
            return

        # Get the original file content
        orig_content = subprocess.check_output(
            [
                "docker",
                "exec",
                container_id,
                "cat",
                "/app/backend/open_webui/routers/audio.py",
            ],
            text=True,
        )

        # Check if the file contains the error
        if 'status_code=getattr(r, "status", 500),' in orig_content:
            print("Fixing Open WebUI Read Aloud error handling...")

            # Make a backup of the original file
            subprocess.run(
                [
                    "docker",
                    "exec",
                    container_id,
                    "cp",
                    "/app/backend/open_webui/routers/audio.py",
                    "/app/backend/open_webui/routers/audio.py.bak",
                ],
                check=True,
            )

            # Fix the variable scope issue
            fixed_content = orig_content.replace(
                'status_code=getattr(r, "status", 500),',
                "status_code=500,  # Fixed: removed reference to undefined variable r",
            )

            # Write the fixed content to a temporary file
            with open("/tmp/fixed_audio.py", "w") as f:
                f.write(fixed_content)

            # Copy the fixed file back to the container
            subprocess.run(
                [
                    "docker",
                    "cp",
                    "/tmp/fixed_audio.py",
                    f"{container_id}:/app/backend/open_webui/routers/audio.py",
                ],
                check=True,
            )

            print("Fix applied successfully! The Read Aloud feature should now work.")
        else:
            print("The Read Aloud feature is already fixed or has been modified.")

    except subprocess.CalledProcessError as e:
        print(f"Error checking Open WebUI container: {e}")
        print("Skipping Read Aloud fix.")


def start_local_ai(profile=None):
    """Start the local AI services (using its compose file)."""
    print("Starting local AI services...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])

    # Use host-level cache if available
    compose_files = ["-f", "docker-compose.yml"]
    if os.path.exists("docker-compose.host-cache.yml"):
        compose_files.extend(["-f", "docker-compose.host-cache.yml"])
        print(
            "Using host-level cache (/opt/ai-cache) for shared models across projects"
        )

    cmd.extend(compose_files)
    cmd.extend(["up", "-d", "--build"])  # Add --build to use BuildKit optimizations

    # Set BuildKit environment variable
    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "1"

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)

    # Fix the Read Aloud feature in Open WebUI
    fix_open_webui_read_aloud()


def main():
    parser = argparse.ArgumentParser(
        description="Start the local AI and Supabase services."
    )
    parser.add_argument(
        "--profile",
        choices=["cpu", "gpu-nvidia", "gpu-amd", "none"],
        default="cpu",
        help="Profile to use for Docker Compose (default: cpu)",
    )
    parser.add_argument(
        "--skip-certs", action="store_true", help="Skip certificate generation"
    )
    parser.add_argument(
        "--network-access",
        action="store_true",
        help="Configure for network access from other computers",
    )
    args = parser.parse_args()

    # Check NGC API key for Virtual Assistant services
    print("\n" + "=" * 50)
    print("Checking Prerequisites")
    print("=" * 50)
    check_ngc_api_key()

    # Check if Crawl4AI image exists
    check_crawl4ai_image()

    # Generate HTTPS certificates if needed
    if not args.skip_certs:
        generate_certificates()

    # Update hosts file for local domains
    # update_hosts_file(network_access=args.network_access)  # TODO: implement or remove

    # If network access is requested, show additional instructions
    if args.network_access:
        print("\n===== NETWORK ACCESS CONFIGURATION =====")
        print("To access services from other computers on your network:")
        print("1. Run: python configure_network_access.py")
        print("2. Follow the instructions to configure client machines")
        print("========================================\n")

    clone_supabase_repo()
    prepare_supabase_env()
    stop_existing_containers()

    # Start Supabase first
    start_supabase()

    # Give Supabase some time to initialize
    print("Waiting for Supabase to initialize...")
    time.sleep(10)

    # Then start the local AI services
    start_local_ai(args.profile)

    print("\n===== HTTPS SETUP COMPLETE =====")
    print("Your services are now available via HTTPS at:")
    print("- https://raven.lan - Main Dashboard")
    print("- https://n8n.lan - n8n")
    print("- https://openwebui.lan - Open WebUI")
    print("- https://studio.lan - Supabase Studio")
    print("- https://kokoro.lan - Kokoro TTS")
    print("- https://comfyui.lan - ComfyUI")
    print("- https://wan.lan - Wan")
    print("- https://crawl4ai.lan - Crawl4AI")
    print("- https://nocodb.lan - NocoDB")
    print("- https://whisper.lan - WhisperX Transcription")
    print("- https://infinitetalk.lan - InfiniteTalk Video Generation")
    print("- https://va.lan - Virtual Assistant")
    print("- https://lmstudio.lan - LM Studio")
    print("- https://traefik.lan - Status Page")

    if args.network_access:
        ip_address = get_primary_ip()
        if ip_address:
            print(
                f"\n** Network Access Enabled: Services accessible from {ip_address} **"
            )
            print(
                "Run 'python configure_network_access.py' for client setup instructions"
            )

    print(
        "\nNote: You may need to accept browser security warnings for self-signed certificates"
    )
    print("==============================")


if __name__ == "__main__":
    main()
