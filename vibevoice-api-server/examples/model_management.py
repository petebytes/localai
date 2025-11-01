"""Model management example."""

import requests
from typing import List, Dict

API_URL = "http://localhost:8000"


def list_available_models() -> List[Dict]:
    """List all available models.

    Returns:
        List of model information dictionaries
    """
    response = requests.get(f"{API_URL}/api/models")

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return []

    data = response.json()
    models = data["models"]

    print(f"\n{'=' * 70}")
    print(f"Available Models ({len(models)})")
    print(f"{'=' * 70}\n")

    for model in models:
        print(f"Model: {model['display_name']}")
        print(f"  ID: {model['model_id']}")
        print(
            f"  Size: {model['size_gb']:.1f}GB"
            if model["size_gb"]
            else "  Size: Unknown"
        )
        print(f"  Loaded: {'✓ Yes' if model['loaded'] else '✗ No'}")
        print(f"  Quantized: {'Yes' if model['quantized'] else 'No'}")
        if model["recommended_for"]:
            print(f"  Recommended for: {', '.join(model['recommended_for'])}")
        print()

    if data["current_model"]:
        print(f"Currently loaded: {data['current_model']}")
    else:
        print("No model currently loaded")

    return models


def load_model(
    model_name: str,
    attention_type: str = "auto",
    quantize_llm: str = "full precision",
    diffusion_steps: int = 20,
):
    """Load a specific model.

    Args:
        model_name: Name of the model to load
        attention_type: Attention mechanism (auto, eager, sdpa, flash_attention_2, sage)
        quantize_llm: Quantization option (full precision, 4bit, 8bit)
        diffusion_steps: Number of diffusion steps
    """
    print(f"\nLoading model: {model_name}")
    print(f"  Attention: {attention_type}")
    print(f"  Quantization: {quantize_llm}")
    print(f"  Diffusion steps: {diffusion_steps}")

    response = requests.post(
        f"{API_URL}/api/models/{model_name}/load",
        json={
            "attention_type": attention_type,
            "quantize_llm": quantize_llm,
            "diffusion_steps": diffusion_steps,
        },
    )

    if response.status_code != 200:
        print(f"Error loading model: {response.status_code}")
        print(response.json())
        return False

    data = response.json()
    print("✓ Model loaded successfully")
    print(f"  Status: {data['status']}")
    return True


def get_current_model():
    """Get information about the currently loaded model."""
    response = requests.get(f"{API_URL}/api/models/current")

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None

    data = response.json()

    if data["current_model"]:
        print(f"\nCurrent model: {data['current_model']}")
        print(f"Device: {data['device']}")
    else:
        print("\nNo model currently loaded")

    return data


def unload_model(model_name: str):
    """Unload the current model to free memory.

    Args:
        model_name: Name of the model to unload
    """
    print(f"\nUnloading model: {model_name}")

    response = requests.post(f"{API_URL}/api/models/{model_name}/unload")

    if response.status_code != 200:
        print(f"Error unloading model: {response.status_code}")
        print(response.json())
        return False

    print("✓ Model unloaded successfully")
    print("  Memory freed")
    return True


def check_health():
    """Check API server health."""
    response = requests.get(f"{API_URL}/api/health")

    if response.status_code != 200:
        print(f"Server unhealthy: {response.status_code}")
        return False

    data = response.json()

    print("\nServer Health Check:")
    print(f"  Status: {data['status']}")
    print(f"  Model loaded: {'✓ Yes' if data['model_loaded'] else '✗ No'}")
    print(f"  GPU available: {'✓ Yes' if data['gpu_available'] else '✗ No (CPU mode)'}")
    print(f"  API version: {data['version']}")

    return data["status"] == "healthy"


if __name__ == "__main__":
    # Check server health
    check_health()

    # List available models
    models = list_available_models()

    # Get current model
    get_current_model()

    # Load a specific model with optimizations
    if models:
        # Example: Load VibeVoice-1.5B with 8-bit quantization
        load_model(
            model_name="VibeVoice-1.5B",
            attention_type="flash_attention_2",  # Use flash attention if available
            quantize_llm="8bit",  # Use 8-bit quantization to save VRAM
            diffusion_steps=20,
        )

        # Check what's loaded now
        get_current_model()

        # Unload when done (optional)
        # unload_model("VibeVoice-1.5B")
