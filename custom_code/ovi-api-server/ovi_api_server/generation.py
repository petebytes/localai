"""Video generation logic for Ovi API - wraps OviFusionEngine."""

import logging
import os
import sys
from datetime import datetime
from typing import Dict, Optional, Tuple

import torch

# Add Ovi directory to Python path
OVI_DIR = os.environ.get("OVI_DIR", "/workspace/ovi")
sys.path.insert(0, OVI_DIR)

from ovi.ovi_fusion_engine import DEFAULT_CONFIG, OviFusionEngine  # noqa: E402
from ovi.utils.io_utils import save_video  # noqa: E402
from ovi.utils.processing_utils import clean_text, scale_hw_to_area_divisible  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Quality presets matching Ovi Gradio app
QUALITY_PRESETS = {
    "youtube-shorts-high": {
        "height": 1080,
        "width": 1920,
        "steps": 70,
        "video_guidance": 8.0,
        "audio_guidance": 7.0,
        "shift": 5.0,
        "solver": "unipc",
        "slg_layer": 11,
    },
    "youtube-shorts-balanced": {
        "height": 1080,
        "width": 1920,
        "steps": 50,
        "video_guidance": 7.0,
        "audio_guidance": 6.5,
        "shift": 5.0,
        "solver": "unipc",
        "slg_layer": 11,
    },
    "youtube-shorts-fast": {
        "height": 1080,
        "width": 1920,
        "steps": 40,
        "video_guidance": 7.0,
        "audio_guidance": 6.0,
        "shift": 5.0,
        "solver": "unipc",
        "slg_layer": 11,
    },
    "square": {
        "height": 960,
        "width": 960,
        "steps": 60,
        "video_guidance": 7.5,
        "audio_guidance": 6.5,
        "shift": 5.0,
        "solver": "unipc",
        "slg_layer": 11,
    },
    "widescreen": {
        "height": 720,
        "width": 1280,
        "steps": 60,
        "video_guidance": 7.5,
        "audio_guidance": 6.5,
        "shift": 5.0,
        "solver": "unipc",
        "slg_layer": 11,
    },
}


class VideoGenerator:
    """Wraps OviFusionEngine for API use with lazy model loading."""

    def __init__(
        self, cpu_offload: bool = True, fp8: bool = False, qint8: bool = False
    ):
        """Initialize video generator with configuration.

        Args:
            cpu_offload: Enable CPU offload to reduce VRAM usage
            fp8: Enable FP8 quantization (requires specific model)
            qint8: Enable QINT8 quantization (no additional models needed)
        """
        self.ovi_engine: Optional[OviFusionEngine] = None
        self.is_loading = False
        self.cpu_offload = cpu_offload
        self.fp8 = fp8
        self.qint8 = qint8

        # Configure model settings
        DEFAULT_CONFIG["cpu_offload"] = cpu_offload
        DEFAULT_CONFIG["mode"] = "t2v"
        DEFAULT_CONFIG["fp8"] = fp8
        DEFAULT_CONFIG["qint8"] = qint8

        logger.info(
            f"VideoGenerator initialized: cpu_offload={cpu_offload}, fp8={fp8}, qint8={qint8}"
        )
        logger.info("Model will be loaded on first inference request")

    def initialize_model(self):
        """Load OviFusionEngine on first use (lazy loading, takes 2-3 minutes)."""
        if self.ovi_engine is not None:
            return  # Already loaded

        if self.is_loading:
            logger.info("Model is currently loading, please wait...")
            return  # Loading in progress

        self.is_loading = True
        logger.info("Loading OviFusionEngine (this may take 2-3 minutes)...")

        try:
            self.ovi_engine = OviFusionEngine()
            logger.info("OviFusionEngine loaded successfully!")
        except Exception as e:
            logger.error(f"Failed to load OviFusionEngine: {e}", exc_info=True)
            self.is_loading = False
            raise

        self.is_loading = False

    def apply_preset(self, preset: str, params: Dict) -> Dict:
        """Apply quality preset to parameters.

        Args:
            preset: Preset name (e.g., 'youtube-shorts-high')
            params: Current parameters dictionary

        Returns:
            Updated parameters dictionary
        """
        if preset not in QUALITY_PRESETS:
            logger.warning(f"Unknown preset: {preset}, using custom parameters")
            return params

        preset_config = QUALITY_PRESETS[preset]
        logger.info(f"Applying preset: {preset}")

        # Override parameters with preset values
        params.update(
            {
                "video_height": preset_config["height"],
                "video_width": preset_config["width"],
                "sample_steps": preset_config["steps"],
                "video_guidance_scale": preset_config["video_guidance"],
                "audio_guidance_scale": preset_config["audio_guidance"],
                "shift": preset_config["shift"],
                "solver_name": preset_config["solver"],
                "slg_layer": preset_config["slg_layer"],
            }
        )

        return params

    def generate(
        self,
        text_prompt: str,
        image_path: Optional[str] = None,
        mode: str = "t2v",
        video_height: int = 1080,
        video_width: int = 1920,
        video_seed: int = 100,
        solver_name: str = "unipc",
        sample_steps: int = 70,
        shift: float = 5.0,
        video_guidance_scale: float = 8.0,
        audio_guidance_scale: float = 7.0,
        slg_layer: int = 11,
        video_negative_prompt: str = "jitter, bad hands, blur, distortion",
        audio_negative_prompt: str = "robotic, muffled, echo, distorted",
        preset: Optional[str] = None,
        output_dir: str = "/output",
    ) -> Tuple[str, Dict]:
        """Generate video with audio from text prompt (and optional image).

        Args:
            text_prompt: Text description. Use <S>speech<E> for dialogue
            image_path: Optional image path for I2V mode
            mode: Generation mode ('t2v' or 'i2v')
            video_height: Video height in pixels
            video_width: Video width in pixels
            video_seed: Random seed for reproducibility
            solver_name: Diffusion solver ('unipc', 'euler', 'dpm++')
            sample_steps: Number of sampling steps (20-100)
            shift: Flow shift parameter (0.0-20.0)
            video_guidance_scale: Video CFG scale (0.0-10.0)
            audio_guidance_scale: Audio CFG scale (0.0-10.0)
            slg_layer: Skip-layer guidance layer (-1 to disable)
            video_negative_prompt: Negative prompt for video
            audio_negative_prompt: Negative prompt for audio
            preset: Optional quality preset name
            output_dir: Directory to save output video

        Returns:
            Tuple of (video_path, metadata_dict)
        """
        # Initialize model on first use
        self.initialize_model()

        # Safety check
        if self.ovi_engine is None:
            raise RuntimeError(
                "OviFusionEngine failed to initialize. Check logs for errors."
            )

        # Apply preset if provided
        if preset:
            params = {
                "video_height": video_height,
                "video_width": video_width,
                "sample_steps": sample_steps,
                "video_guidance_scale": video_guidance_scale,
                "audio_guidance_scale": audio_guidance_scale,
                "shift": shift,
                "solver_name": solver_name,
                "slg_layer": slg_layer,
            }
            params = self.apply_preset(preset, params)
            video_height = params["video_height"]
            video_width = params["video_width"]
            sample_steps = params["sample_steps"]
            video_guidance_scale = params["video_guidance_scale"]
            audio_guidance_scale = params["audio_guidance_scale"]
            shift = params["shift"]
            solver_name = params["solver_name"]
            slg_layer = params["slg_layer"]

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Validate image path for I2V mode
        if mode == "i2v":
            if not image_path:
                raise ValueError("image_path is required for Image-to-Video mode")
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")

        # Clean and validate text prompt
        text_prompt = clean_text(text_prompt)
        logger.info(f"Generating {mode.upper()} video: {text_prompt[:100]}...")
        logger.info(
            f"Resolution: {video_width}x{video_height}, Steps: {sample_steps}, Seed: {video_seed}"
        )

        # Scale dimensions to valid area
        video_height, video_width = scale_hw_to_area_divisible(
            video_height, video_width, area=1024 * 1024
        )
        logger.info(f"Adjusted resolution: {video_width}x{video_height}")

        # Generate video + audio
        try:
            generated_video, generated_audio, _ = self.ovi_engine.generate(
                text_prompt=text_prompt,
                image_path=image_path if mode == "i2v" else None,
                video_frame_height_width=[video_height, video_width],
                seed=video_seed,
                solver_name=solver_name,
                sample_steps=sample_steps,
                shift=shift,
                video_guidance_scale=video_guidance_scale,
                audio_guidance_scale=audio_guidance_scale,
                slg_layer=slg_layer,
                video_negative_prompt=video_negative_prompt,
                audio_negative_prompt=audio_negative_prompt,
            )
        except Exception as e:
            logger.error(f"Video generation failed: {e}", exc_info=True)
            raise RuntimeError(f"OviFusionEngine generation failed: {str(e)}")

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = text_prompt.replace(" ", "_").replace("/", "_")[:30]
        output_filename = f"ovi_{mode}_{safe_prompt}_{timestamp}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        # Save video with audio
        logger.info(f"Saving video to: {output_path}")
        save_video(
            output_path, generated_video, generated_audio, fps=24, sample_rate=16000
        )

        # Calculate metadata
        # generated_video shape is (C, F, H, W) for 4D or (B, C, F, H, W) for 5D
        if len(generated_video.shape) == 5:
            frame_count = generated_video.shape[2]  # Frames are in dimension 2
        else:
            frame_count = generated_video.shape[1]  # Frames are in dimension 1
        duration_seconds = frame_count / 24.0  # 24 FPS
        has_audio = generated_audio is not None

        metadata = {
            "seed": str(video_seed),
            "steps": str(sample_steps),
            "solver": solver_name,
            "video_guidance": str(video_guidance_scale),
            "audio_guidance": str(audio_guidance_scale),
            "shift": str(shift),
            "slg_layer": str(slg_layer),
            "mode": mode,
            "preset": preset if preset else "custom",
            "timestamp": timestamp,
        }

        # Free GPU memory for next request
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info(
            f"Video generation completed: {frame_count} frames, {duration_seconds:.2f}s"
        )

        return output_path, {
            "duration_seconds": duration_seconds,
            "frame_count": frame_count,
            "resolution": f"{video_width}x{video_height}",
            "has_audio": has_audio,
            "metadata": metadata,
        }
