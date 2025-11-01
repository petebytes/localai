"""Model management for VibeVoice API server."""

import gc
import logging
from pathlib import Path
from typing import Optional, Dict, List
import torch
from transformers import BitsAndBytesConfig

from .models import ModelInfo, AttentionType, QuantizationType

# Import VibeVoice components
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "vvembed"))

from vvembed.modular.modeling_vibevoice_inference import (
    VibeVoiceForConditionalGenerationInference,
)
from vvembed.processor.vibevoice_processor import VibeVoiceProcessor


logger = logging.getLogger(__name__)


class ModelManager:
    """Manages VibeVoice model loading, unloading, and switching."""

    def __init__(self, models_dir: Path):
        """Initialize model manager.

        Args:
            models_dir: Directory containing VibeVoice models
        """
        self.models_dir = Path(models_dir)
        self.current_model: Optional[VibeVoiceForConditionalGenerationInference] = None
        self.current_processor: Optional[VibeVoiceProcessor] = None
        self.current_model_name: Optional[str] = None
        self.current_device: Optional[torch.device] = None

        # Cache of available models
        self._available_models: Optional[List[ModelInfo]] = None

    def get_device(self) -> torch.device:
        """Get the best available device."""
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            return torch.device("cpu")

    def scan_available_models(self) -> List[ModelInfo]:
        """Scan models directory for available models.

        Returns:
            List of available models with metadata
        """
        if not self.models_dir.exists():
            logger.warning(f"Models directory not found: {self.models_dir}")
            return []

        models = []
        seen_names = set()

        # Scan for model directories
        for item in self.models_dir.iterdir():
            if not item.is_dir():
                continue

            model_id = item.name
            config_file = item / "config.json"

            # Check if valid model directory
            if not config_file.exists():
                # Check for HuggingFace cache structure
                snapshots_dir = item / "snapshots"
                if snapshots_dir.exists():
                    # Find the first snapshot
                    for snapshot in snapshots_dir.iterdir():
                        if snapshot.is_dir():
                            config_file = snapshot / "config.json"
                            if config_file.exists():
                                break

            if not config_file.exists():
                continue

            # Determine display name and metadata
            display_name = model_id
            size_gb = None
            quantized = False
            recommended_for = []

            if "1.5B" in model_id or "1-5B" in model_id:
                size_gb = 5.4
                recommended_for = ["Fast generation", "Single speaker"]
            elif "Large" in model_id:
                if "Q8" in model_id:
                    size_gb = 11.6
                    quantized = True
                    recommended_for = [
                        "12GB GPUs",
                        "Multi-speaker",
                        "Production quality",
                    ]
                elif "Q4" in model_id:
                    size_gb = 6.6
                    quantized = True
                    recommended_for = ["8GB GPUs", "Good quality"]
                else:
                    size_gb = 18.7
                    recommended_for = ["Multi-speaker", "Best quality", "20GB+ GPUs"]

            # Avoid duplicates
            if display_name in seen_names:
                continue
            seen_names.add(display_name)

            models.append(
                ModelInfo(
                    model_id=model_id,
                    display_name=display_name,
                    size_gb=size_gb,
                    loaded=(model_id == self.current_model_name),
                    quantized=quantized,
                    recommended_for=recommended_for,
                )
            )

        self._available_models = models
        return models

    def load_model(
        self,
        model_name: str,
        attention_type: AttentionType = AttentionType.AUTO,
        quantize_llm: QuantizationType = QuantizationType.FULL_PRECISION,
        diffusion_steps: int = 20,
    ) -> None:
        """Load a VibeVoice model.

        Args:
            model_name: Name of the model to load
            attention_type: Attention mechanism to use
            quantize_llm: LLM quantization option
            diffusion_steps: Number of diffusion steps

        Raises:
            FileNotFoundError: If model not found
            RuntimeError: If model loading fails
        """
        # Check if already loaded
        if self.current_model is not None and self.current_model_name == model_name:
            logger.info(f"Model {model_name} already loaded")
            return

        # Find model path
        model_path = self.models_dir / model_name
        if not model_path.exists():
            # Check HuggingFace cache structure
            snapshots_dir = model_path / "snapshots"
            if snapshots_dir.exists():
                for snapshot in snapshots_dir.iterdir():
                    if snapshot.is_dir() and (snapshot / "config.json").exists():
                        model_path = snapshot
                        break

        if not (model_path / "config.json").exists():
            raise FileNotFoundError(f"Model not found: {model_name}")

        logger.info(f"Loading model: {model_name} from {model_path}")

        # Free existing model
        if self.current_model is not None:
            self.free_memory()

        # Get device
        device = self.get_device()
        self.current_device = device

        # Configure quantization
        quantization_config = None
        if quantize_llm != QuantizationType.FULL_PRECISION:
            if not torch.cuda.is_available():
                logger.warning(
                    "Quantization requires CUDA. Falling back to full precision."
                )
            else:
                load_in_4bit = quantize_llm == QuantizationType.FOUR_BIT
                load_in_8bit = quantize_llm == QuantizationType.EIGHT_BIT

                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=load_in_4bit,
                    load_in_8bit=load_in_8bit,
                    bnb_4bit_compute_dtype=torch.bfloat16 if load_in_4bit else None,
                    bnb_4bit_quant_type="nf4" if load_in_4bit else None,
                )

        # Load processor
        logger.info("Loading processor...")
        self.current_processor = VibeVoiceProcessor.from_pretrained(str(model_path))

        # Load model
        logger.info("Loading model weights...")
        attn_implementation = (
            attention_type.value if attention_type != AttentionType.AUTO else None
        )

        load_kwargs = {
            "torch_dtype": torch.bfloat16,
            "attn_implementation": attn_implementation,
        }

        if quantization_config:
            load_kwargs["quantization_config"] = quantization_config
            load_kwargs["device_map"] = "auto"
        else:
            load_kwargs["device_map"] = str(device)

        self.current_model = VibeVoiceForConditionalGenerationInference.from_pretrained(
            str(model_path), **load_kwargs
        )

        # Set diffusion steps
        self.current_model.set_ddpm_inference_steps(diffusion_steps)

        self.current_model_name = model_name
        logger.info(f"Model {model_name} loaded successfully on {device}")

    def apply_lora(self, lora_config: Dict) -> None:
        """Apply LoRA adapter to current model.

        Args:
            lora_config: LoRA configuration dictionary

        Raises:
            RuntimeError: If no model is loaded or LoRA application fails
        """
        if self.current_model is None:
            raise RuntimeError("No model loaded")

        from peft import PeftModel

        lora_name = lora_config["lora_name"]
        lora_path = self.models_dir.parent / "loras" / lora_name

        if not lora_path.exists():
            raise FileNotFoundError(f"LoRA not found: {lora_name}")

        logger.info(f"Applying LoRA: {lora_name}")

        # Load and apply LoRA
        # Note: This is a simplified version. Full implementation would handle
        # selective component loading based on enable_* flags
        self.current_model = PeftModel.from_pretrained(
            self.current_model,
            str(lora_path),
            adapter_name=lora_name,
        )

        # Set LoRA strength
        strength = lora_config.get("llm_strength", 1.0)
        self.current_model.set_adapter_scale(lora_name, strength)

    def free_memory(self) -> None:
        """Free GPU/CPU memory by unloading current model."""
        if self.current_model is None:
            logger.info("No model to unload")
            return

        logger.info(f"Freeing memory for model: {self.current_model_name}")

        # Delete model and processor
        del self.current_model
        del self.current_processor
        self.current_model = None
        self.current_processor = None
        self.current_model_name = None

        # Force garbage collection
        gc.collect()

        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Memory freed successfully")

    def get_model_and_processor(self):
        """Get current model and processor.

        Returns:
            Tuple of (model, processor)

        Raises:
            RuntimeError: If no model is loaded
        """
        if self.current_model is None or self.current_processor is None:
            raise RuntimeError("No model loaded. Call load_model() first.")

        return self.current_model, self.current_processor

    def is_model_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self.current_model is not None
