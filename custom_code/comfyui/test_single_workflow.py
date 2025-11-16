#!/usr/bin/env python3
"""
Test a single Wan 2.2 workflow via ComfyUI API
"""

import json
import time
import requests
import sys

COMFYUI_URL = "http://localhost:18188"
API_URL = f"{COMFYUI_URL}/api"


def load_workflow(path):
    """Load workflow JSON"""
    with open(path, "r") as f:
        return json.load(f)


def convert_to_api_format(workflow):
    """Convert ComfyUI UI workflow to API format"""
    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])

    # Create link lookup
    link_map = {}
    for link in links:
        link_id = link[0]
        link_map[link_id] = {
            "source_node": str(link[1]),
            "source_slot": link[2],
            "target_node": str(link[3]),
            "target_slot": link[4],
        }

    api_prompt = {}

    for node in nodes:
        node_id = str(node["id"])
        node_type = node.get("type")

        if not node_type:
            print(f"Warning: Node {node_id} missing type")
            continue

        inputs = {}

        # Process inputs
        for input_def in node.get("inputs", []):
            input_name = input_def.get("name")
            link_id = input_def.get("link")

            if link_id is not None and link_id in link_map:
                # This is a linked input
                link_info = link_map[link_id]
                inputs[input_name] = [
                    link_info["source_node"],
                    link_info["source_slot"],
                ]
            elif "widget" in input_def:
                # This is a widget input - value comes from widgets_values
                pass  # Will be handled below

        # Add widget values
        if "widgets_values" in node:
            widget_values = node["widgets_values"]

            # Map widget values to input names
            widget_inputs = [inp for inp in node.get("inputs", []) if "widget" in inp]

            if isinstance(widget_values, dict):
                # Direct dict mapping
                for key, value in widget_values.items():
                    if key not in inputs:  # Don't override linked inputs
                        inputs[key] = value
            elif isinstance(widget_values, list):
                # List mapping - match by order
                for i, value in enumerate(widget_values):
                    if i < len(widget_inputs):
                        input_name = widget_inputs[i]["name"]
                        if input_name not in inputs:
                            inputs[input_name] = value

        api_prompt[node_id] = {"class_type": node_type, "inputs": inputs}

    return api_prompt


def queue_prompt(api_prompt):
    """Queue prompt and return prompt_id"""
    client_id = f"test_{int(time.time())}"

    payload = {"prompt": api_prompt, "client_id": client_id}

    response = requests.post(f"{API_URL}/prompt", json=payload)

    if response.status_code == 200:
        result = response.json()
        return result.get("prompt_id"), client_id
    else:
        print(f"Error queueing prompt: {response.status_code}")
        print(response.text)
        return None, None


def wait_for_completion(prompt_id, timeout=3600):
    """Wait for prompt to complete"""
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time

        if elapsed > timeout:
            print(f"Timeout after {elapsed:.0f}s")
            return None

        # Check history
        response = requests.get(f"{API_URL}/history/{prompt_id}")
        if response.status_code == 200:
            history = response.json()
            if prompt_id in history:
                prompt_data = history[prompt_id]

                # Check if completed
                if "outputs" in prompt_data:
                    execution_time = time.time() - start_time
                    return execution_time

                # Check for errors
                if "status" in prompt_data:
                    status = prompt_data["status"]
                    if "completed" in status and status["completed"]:
                        execution_time = time.time() - start_time
                        return execution_time

        # Print progress every 10 seconds
        if int(elapsed) % 10 == 0:
            print(f"  Waiting... {elapsed:.0f}s elapsed")

        time.sleep(2)


def test_workflow(workflow_path):
    """Test a single workflow"""
    print(f"\n{'=' * 70}")
    print(f"Testing: {workflow_path}")
    print(f"{'=' * 70}\n")

    # Load workflow
    print("1. Loading workflow...")
    workflow = load_workflow(workflow_path)
    print(f"   Loaded {len(workflow.get('nodes', []))} nodes")

    # Convert to API format
    print("2. Converting to API format...")
    api_prompt = convert_to_api_format(workflow)
    print(f"   Converted to {len(api_prompt)} API nodes")

    # Save API format for debugging
    debug_path = workflow_path.replace(".json", "_api.json")
    with open(debug_path, "w") as f:
        json.dump(api_prompt, f, indent=2)
    print(f"   API format saved to: {debug_path}")

    # Queue prompt
    print("3. Queueing prompt...")
    prompt_id, client_id = queue_prompt(api_prompt)

    if not prompt_id:
        print("   ERROR: Failed to queue prompt")
        return False

    print(f"   Prompt ID: {prompt_id}")
    print(f"   Client ID: {client_id}")

    # Wait for completion
    print("4. Waiting for completion...")
    execution_time = wait_for_completion(prompt_id)

    if execution_time:
        print("\n✅ SUCCESS!")
        print(
            f"   Execution time: {execution_time:.1f}s ({execution_time / 60:.1f} minutes)"
        )
        return True
    else:
        print("\n❌ FAILED or TIMEOUT")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_single_workflow.py <workflow.json>")
        sys.exit(1)

    workflow_path = sys.argv[1]
    success = test_workflow(workflow_path)

    sys.exit(0 if success else 1)
