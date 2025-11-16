#!/usr/bin/env python3
"""
Wan 2.2 Workflow Speed Comparison Test
Tests three workflows with identical settings and measures performance
"""

import json
import time
import requests
import sys
from datetime import datetime

# ComfyUI API settings
COMFYUI_URL = "http://localhost:18188"
API_URL = f"{COMFYUI_URL}/api"

# Test configuration
TEST_CONFIG = {
    "resolution": {"width": 640, "height": 640},
    "frames": 49,
    "seed": 12345,  # Fixed seed for consistency
    "prompt": "A serene mountain landscape at sunset, gentle camera pan to the right, warm golden light",
    "negative_prompt": "blurry, low quality, distorted, artifacts, static",
}

# Workflows to test
WORKFLOWS = {
    "5B_Full_Precision": {
        "path": "/mnt/ai-data/code/localai/custom_code/comfyui/workflows/Wan2.2-Image2Video_5b_v2_NoSetGet.json",
        "description": "Wan 2.2 5B FP16 (Full Precision + SageAttention)",
    },
    "14B_GGUF_Lightx2v": {
        "path": "/mnt/ai-data/code/localai/custom_code/comfyui/workflows/wan_2_2_lightx2v.json",
        "description": "Wan 2.2 14B GGUF Q4 + Lightx2v LoRA",
    },
    "14B_GGUF_Olivio": {
        "path": "/mnt/ai-data/code/localai/custom_code/comfyui/workflows/Wan 2.2 Lightx2v Super Fast Olivio.json",
        "description": "Wan 2.2 14B GGUF Q4 + Lightx2v LoRA (Olivio)",
    },
}


class ComfyUITester:
    def __init__(self):
        self.client_id = f"speed_test_{int(time.time())}"
        self.results = []

    def check_comfyui_ready(self):
        """Check if ComfyUI is running and responsive"""
        try:
            response = requests.get(f"{API_URL}/system_stats", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def load_workflow(self, workflow_path):
        """Load and parse workflow JSON"""
        with open(workflow_path, "r") as f:
            return json.load(f)

    def modify_workflow_settings(self, workflow, workflow_name):
        """Modify workflow to use consistent test settings"""
        nodes = workflow.get("nodes", [])

        for node in nodes:
            node_type = node.get("type", "")

            # Set resolution
            if node_type in ["ImageResize+", "WanVideoEmptyEmbeds"]:
                if "widgets_values" in node:
                    for i, val in enumerate(node["widgets_values"]):
                        if i < 2:  # width, height typically first two values
                            node["widgets_values"][i] = (
                                TEST_CONFIG["resolution"]["width"]
                                if i == 0
                                else TEST_CONFIG["resolution"]["height"]
                            )

            # Set frame count
            if node_type == "INTConstant" and node.get("title") == "FRAMES":
                node["widgets_values"] = [TEST_CONFIG["frames"]]
            elif node_type == "PrimitiveInt":
                # Check if it's the frames node
                if any("num_frames" in str(link) for link in node.get("outputs", [])):
                    node["widgets_values"][0] = TEST_CONFIG["frames"]

            # Set seed
            if node_type in ["WanVideoSampler", "KSamplerAdvanced", "PrimitiveNode"]:
                if "widgets_values" in node:
                    for i, val in enumerate(node["widgets_values"]):
                        if isinstance(val, int) and val > 1000000:  # Likely a seed
                            node["widgets_values"][i] = TEST_CONFIG["seed"]
                            if (
                                i + 1 < len(node["widgets_values"])
                                and node["widgets_values"][i + 1] == "randomize"
                            ):
                                node["widgets_values"][i + 1] = "fixed"

            # Set prompts
            if node_type == "WanVideoTextEncode":
                if "widgets_values" in node and len(node["widgets_values"]) >= 2:
                    node["widgets_values"][0] = TEST_CONFIG["prompt"]
                    node["widgets_values"][1] = TEST_CONFIG["negative_prompt"]

            # Set output filename
            if node_type == "VHS_VideoCombine":
                if "widgets_values" in node:
                    if isinstance(node["widgets_values"], dict):
                        node["widgets_values"]["filename_prefix"] = (
                            f"speed_test/{workflow_name}"
                        )
                    else:
                        # Try to find filename_prefix in the list
                        for i, val in enumerate(node["widgets_values"]):
                            if isinstance(val, str) and (
                                "/" in val or "wan" in val.lower()
                            ):
                                node["widgets_values"][i] = (
                                    f"speed_test/{workflow_name}"
                                )
                                break

        return workflow

    def convert_workflow_to_api(self, workflow):
        """Convert ComfyUI workflow format to API format"""
        # Extract nodes from workflow
        nodes = workflow.get("nodes", [])

        # Convert to API format
        api_prompt = {}

        for node in nodes:
            node_id = str(node.get("id"))
            node_type = node.get("type")

            if not node_type:
                continue

            # Build inputs dict
            inputs = {}

            # Add widget values as inputs
            if "widgets_values" in node:
                widget_values = node["widgets_values"]
                # Map widget values to their input names
                node_inputs = node.get("inputs", [])
                for i, input_def in enumerate(node_inputs):
                    input_name = input_def.get("name")
                    if input_name and "widget" in input_def:
                        if isinstance(widget_values, dict):
                            if input_name in widget_values:
                                inputs[input_name] = widget_values[input_name]
                        elif isinstance(widget_values, list) and i < len(widget_values):
                            inputs[input_name] = widget_values[i]

            # Add linked inputs
            for input_def in node.get("inputs", []):
                link_id = input_def.get("link")
                if link_id is not None:
                    # Find the source of this link
                    for link in workflow.get("links", []):
                        if link[0] == link_id:
                            source_node_id = str(link[1])
                            source_output_index = link[2]
                            inputs[input_def["name"]] = [
                                source_node_id,
                                source_output_index,
                            ]
                            break

            api_prompt[node_id] = {"class_type": node_type, "inputs": inputs}

        return api_prompt

    def queue_prompt(self, workflow):
        """Queue a workflow for execution"""
        # Convert workflow to API format
        api_prompt = self.convert_workflow_to_api(workflow)

        payload = {"prompt": api_prompt, "client_id": self.client_id}

        response = requests.post(f"{API_URL}/prompt", json=payload)
        if response.status_code == 200:
            return response.json().get("prompt_id")
        else:
            raise Exception(f"Failed to queue prompt: {response.text}")

    def get_queue_status(self):
        """Get current queue status"""
        response = requests.get(f"{API_URL}/queue")
        return response.json() if response.status_code == 200 else None

    def get_history(self, prompt_id):
        """Get execution history for a prompt"""
        response = requests.get(f"{API_URL}/history/{prompt_id}")
        return response.json() if response.status_code == 200 else None

    def wait_for_completion(self, prompt_id, timeout=1800):
        """Wait for workflow to complete, return execution time"""
        start_time = time.time()
        last_status = None

        print(f"  Waiting for completion (timeout: {timeout}s)...", end="", flush=True)

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout:
                print(f"\n  ⏱️  TIMEOUT after {elapsed:.1f}s")
                return None

            # Check history
            history = self.get_history(prompt_id)
            if history and prompt_id in history:
                prompt_history = history[prompt_id]

                # Check if completed
                if "outputs" in prompt_history:
                    execution_time = time.time() - start_time
                    print(f"\n  ✅ Completed in {execution_time:.1f}s")
                    return execution_time

                # Check for errors
                if "status" in prompt_history:
                    status = prompt_history["status"]
                    if (
                        "status_str" in status
                        and "error" in status["status_str"].lower()
                    ):
                        print(f"\n  ❌ Error: {status}")
                        return None

            # Check queue
            queue_status = self.get_queue_status()
            if queue_status:
                running = queue_status.get("queue_running", [])
                pending = queue_status.get("queue_pending", [])

                # Update progress indicator
                if running and running[0][1] == prompt_id:
                    current_status = "running"
                elif any(p[1] == prompt_id for p in pending):
                    current_status = f"queued (position {[i for i, p in enumerate(pending) if p[1] == prompt_id][0] + 1})"
                else:
                    current_status = "processing"

                if current_status != last_status:
                    print(
                        f"\r  Status: {current_status} ({elapsed:.0f}s)",
                        end="",
                        flush=True,
                    )
                    last_status = current_status

            time.sleep(2)

    def get_vram_usage(self):
        """Get current VRAM usage from nvidia-smi"""
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return int(result.stdout.strip().split("\n")[0])
            return None
        except Exception:
            return None

    def run_test(self, workflow_name, workflow_info):
        """Run a single workflow test"""
        print(f"\n{'=' * 70}")
        print(f"Testing: {workflow_name}")
        print(f"Description: {workflow_info['description']}")
        print(f"{'=' * 70}")

        try:
            # Load workflow
            print("  Loading workflow...")
            workflow = self.load_workflow(workflow_info["path"])

            # Modify settings
            print("  Applying test settings...")
            workflow = self.modify_workflow_settings(workflow, workflow_name)

            # Get baseline VRAM
            vram_before = self.get_vram_usage()
            print(
                f"  VRAM before: {vram_before}MB"
                if vram_before
                else "  VRAM: Unable to measure"
            )

            # Queue workflow
            print("  Queueing workflow...")
            prompt_id = self.queue_prompt(workflow)
            print(f"  Prompt ID: {prompt_id}")

            # Wait for completion and measure time
            execution_time = self.wait_for_completion(prompt_id)

            # Get peak VRAM
            vram_after = self.get_vram_usage()

            if execution_time:
                result = {
                    "workflow": workflow_name,
                    "description": workflow_info["description"],
                    "execution_time": execution_time,
                    "vram_before": vram_before,
                    "vram_after": vram_after,
                    "success": True,
                }
                self.results.append(result)
                print(f"  ✅ SUCCESS - {execution_time:.1f}s")
                if vram_after:
                    print(f"  VRAM after: {vram_after}MB")
                return True
            else:
                result = {
                    "workflow": workflow_name,
                    "description": workflow_info["description"],
                    "success": False,
                    "error": "Timeout or error during execution",
                }
                self.results.append(result)
                return False

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            result = {
                "workflow": workflow_name,
                "description": workflow_info["description"],
                "success": False,
                "error": str(e),
            }
            self.results.append(result)
            return False

    def print_summary(self):
        """Print test summary and comparison"""
        print(f"\n\n{'=' * 70}")
        print("TEST SUMMARY")
        print(f"{'=' * 70}")
        print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Settings:")
        print(
            f"  - Resolution: {TEST_CONFIG['resolution']['width']}x{TEST_CONFIG['resolution']['height']}"
        )
        print(f"  - Frames: {TEST_CONFIG['frames']}")
        print(f"  - Seed: {TEST_CONFIG['seed']}")
        print(f"\n{'=' * 70}")
        print(f"{'Workflow':<25} {'Time (s)':<12} {'Speed':<15} {'VRAM':<10}")
        print(f"{'=' * 70}")

        successful_results = [r for r in self.results if r["success"]]

        if successful_results:
            baseline_time = successful_results[0]["execution_time"]

            for result in self.results:
                if result["success"]:
                    time_str = f"{result['execution_time']:.1f}s"
                    speedup = baseline_time / result["execution_time"]
                    speed_str = f"{speedup:.2f}x" if speedup != 1.0 else "baseline"
                    vram_str = (
                        f"{result['vram_after']}MB"
                        if result.get("vram_after")
                        else "N/A"
                    )
                    print(
                        f"{result['workflow']:<25} {time_str:<12} {speed_str:<15} {vram_str:<10}"
                    )
                else:
                    print(
                        f"{result['workflow']:<25} {'FAILED':<12} {'-':<15} {'-':<10}"
                    )

            print(f"{'=' * 70}")

            # Winner
            fastest = min(successful_results, key=lambda x: x["execution_time"])
            print(f"\n🏆 FASTEST: {fastest['workflow']}")
            print(f"   Time: {fastest['execution_time']:.1f}s")
            if len(successful_results) > 1:
                speedup = baseline_time / fastest["execution_time"]
                print(f"   {speedup:.2f}x faster than baseline")
        else:
            print("No successful test runs")

        # Save results to file
        results_file = f"/mnt/ai-data/code/localai/custom_code/comfyui/speed_test_results_{int(time.time())}.json"
        with open(results_file, "w") as f:
            json.dump(
                {
                    "test_date": datetime.now().isoformat(),
                    "config": TEST_CONFIG,
                    "results": self.results,
                },
                f,
                indent=2,
            )
        print(f"\n📊 Results saved to: {results_file}")


def main():
    print("=" * 70)
    print("WAN 2.2 WORKFLOW SPEED COMPARISON TEST")
    print("=" * 70)

    tester = ComfyUITester()

    # Check if ComfyUI is running
    print("\nChecking ComfyUI status...")
    if not tester.check_comfyui_ready():
        print("❌ ERROR: ComfyUI is not running or not responding")
        print(f"   Make sure ComfyUI is running at {COMFYUI_URL}")
        sys.exit(1)

    print("✅ ComfyUI is ready")

    # Run tests for each workflow
    for workflow_name, workflow_info in WORKFLOWS.items():
        success = tester.run_test(workflow_name, workflow_info)

        # Wait between tests to allow cleanup
        if success:
            print("\n  Waiting 30s before next test...")
            time.sleep(30)

    # Print summary
    tester.print_summary()


if __name__ == "__main__":
    main()
