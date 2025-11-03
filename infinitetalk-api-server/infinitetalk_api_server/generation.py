"""Video generation logic extracted from InfiniteTalk app.py."""

import logging
import os
from datetime import datetime

import librosa
import pyloudnorm as pyln
import soundfile as sf
import torch
from einops import rearrange
from transformers import Wav2Vec2FeatureExtractor

import wan
from src.audio_analysis.wav2vec2 import Wav2Vec2Model
from wan.utils.multitalk_utils import save_video_ffmpeg

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def custom_init(device, wav2vec_dir):
    """Initialize Wav2Vec2 audio encoder.

    Args:
        device: Device to load models on ('cpu' or 'cuda')
        wav2vec_dir: Path to Wav2Vec2 model directory

    Returns:
        Tuple of (feature_extractor, encoder_model)
    """
    feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(wav2vec_dir)
    model = Wav2Vec2Model.from_pretrained(wav2vec_dir)
    model.feature_extractor._freeze_parameters()
    model = model.to(device)
    model = model.eval()
    return feature_extractor, model


def loudness_norm(audio, sr, target_lufs=-23):
    """Normalize audio loudness to target LUFS.

    Args:
        audio: Audio array
        sr: Sample rate
        target_lufs: Target loudness in LUFS (default: -23)

    Returns:
        Normalized audio array
    """
    meter = pyln.Meter(sr)
    loudness = meter.integrated_loudness(audio)
    normalized_audio = pyln.normalize.loudness(audio, loudness, target_lufs)
    return normalized_audio


def get_embedding(audio, feature_extractor, model, video_length):
    """Extract Wav2Vec2 embeddings from audio at 25fps.

    Args:
        audio: Audio array (16kHz)
        feature_extractor: Wav2Vec2 feature extractor
        model: Wav2Vec2 model
        video_length: Target video length in frames (at 25fps)

    Returns:
        Audio embeddings tensor
    """
    with torch.inference_mode():
        inputs = feature_extractor(
            audio,
            sampling_rate=16000,
            return_tensors="pt",
            padding=True,
        )
        embeddings = model(
            inputs.input_values.to(model.device),
            seq_len=int(video_length),
            return_dict=True,
            output_hidden_states=True,
        )

    audio_emb = torch.stack(embeddings.hidden_states[1:], dim=1).squeeze(0)
    audio_emb = rearrange(audio_emb, "b s d -> s b d")
    audio_emb = audio_emb.cpu().detach()
    return audio_emb


def audio_prepare_single(audio_path, sample_rate=16000):
    """Load and normalize audio from file.

    Args:
        audio_path: Path to audio file (WAV, MP3, OGG, etc.)
        sample_rate: Target sample rate (default: 16000)

    Returns:
        Normalized audio array
    """
    human_speech_array, sr = librosa.load(audio_path, sr=sample_rate)
    human_speech_array = loudness_norm(human_speech_array, sr)
    return human_speech_array


class VideoGenerator:
    """Wraps InfiniteTalk pipeline for API use."""

    def __init__(self, args):
        """Initialize video generator with configuration.

        Args:
            args: Namespace with model paths and generation parameters
        """
        self.args = args
        self.wav2vec_feature_extractor = None
        self.audio_encoder = None
        self.wan_i2v = None
        self.is_loading = False
        self.device = 0 if torch.cuda.is_available() else "cpu"
        self.rank = 0

    def initialize_models(self):
        """Initialize models on first use (lazy loading, takes 2-3 minutes)."""
        if self.wan_i2v is not None:
            return  # Already loaded

        if self.is_loading:
            logger.info("Models are currently loading, please wait...")
            return  # Loading in progress

        self.is_loading = True
        logger.info("Loading models on first use (this may take 2-3 minutes)...")

        # Load audio encoder
        logger.info("Loading Wav2Vec2 audio encoder...")
        extractor, encoder = custom_init("cpu", self.args.wav2vec_dir)
        self.wav2vec_feature_extractor = extractor
        self.audio_encoder = encoder
        logger.info("Audio encoder loaded successfully")

        # Load video generation pipeline
        logger.info("Creating InfiniteTalk pipeline...")
        from wan.configs import WAN_CONFIGS

        cfg = WAN_CONFIGS[self.args.task]

        self.wan_i2v = wan.InfiniteTalkPipeline(
            config=cfg,
            checkpoint_dir=self.args.ckpt_dir,
            quant_dir=self.args.quant_dir,
            device_id=self.device,
            rank=self.rank,
            t5_fsdp=False,
            dit_fsdp=False,
            use_usp=False,
            t5_cpu=False,
            lora_dir=self.args.lora_dir,
            lora_scales=self.args.lora_scale,
            quant=self.args.quant,
            dit_path=None,
            infinitetalk_dir=self.args.infinitetalk_dir,
        )

        # Enable VRAM management if configured
        if self.args.num_persistent_param_in_dit is not None:
            logger.info(
                f"Enabling VRAM management (num_persistent_param={self.args.num_persistent_param_in_dit})..."
            )
            self.wan_i2v.vram_management = True
            self.wan_i2v.enable_vram_management(
                num_persistent_param_in_dit=self.args.num_persistent_param_in_dit
            )

        self.is_loading = False
        logger.info("Models loaded successfully!")

    def generate(
        self,
        audio_path: str,
        image_path: str,
        prompt: str = "",
        resolution: str = "infinitetalk-480",
        seed: int = 42,
        diffusion_steps: int = 40,
        text_guide_scale: float = 5.0,
        audio_guide_scale: float = 4.0,
        motion_frame: int = 9,
        use_color_correction: bool = True,
        output_dir: str = "/output",
    ):
        """Generate talking head video from audio and image.

        Args:
            audio_path: Path to audio file
            image_path: Path to image or video file
            prompt: Text description of the scene
            resolution: Output resolution ('infinitetalk-480' or 'infinitetalk-720')
            seed: Random seed for reproducibility
            diffusion_steps: Number of sampling steps (40 for quality)
            text_guide_scale: Text CFG scale
            audio_guide_scale: Audio CFG scale
            motion_frame: Overlap frames for streaming mode
            use_color_correction: Apply color drift correction
            output_dir: Directory to save output video

        Returns:
            Tuple of (video_path, metadata_dict)
        """
        # Initialize models on first use
        self.initialize_models()

        # Safety check
        if self.wan_i2v is None or self.audio_encoder is None:
            raise RuntimeError("Models failed to initialize. Check logs for errors.")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Validate input files
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Prepare audio directory for embeddings
        audio_save_dir = os.path.join(output_dir, "audio_embeddings")
        os.makedirs(audio_save_dir, exist_ok=True)

        # Process audio - single person mode
        logger.info(f"Processing audio: {audio_path}")
        human_speech = audio_prepare_single(audio_path)

        # Calculate video length in frames (audio at 16kHz, video at 25fps)
        audio_duration_sec = len(human_speech) / 16000
        video_length = int(audio_duration_sec * 25)  # 25 fps
        logger.info(
            f"Audio duration: {audio_duration_sec:.2f}s, target video length: {video_length} frames"
        )

        audio_embedding = get_embedding(
            human_speech,
            self.wav2vec_feature_extractor,
            self.audio_encoder,
            video_length,
        )

        # Save embedding and audio
        emb_path = os.path.join(audio_save_dir, "1.pt")
        sum_audio = os.path.join(audio_save_dir, "sum.wav")
        sf.write(sum_audio, human_speech, 16000)
        torch.save(audio_embedding, emb_path)

        # Prepare input data structure
        input_data = {
            "prompt": prompt,
            "cond_video": image_path,
            "cond_audio": {"person1": emb_path},
            "video_audio": sum_audio,
        }

        # Generate video
        logger.info("Generating video (this may take 3-5 minutes)...")
        video = self.wan_i2v.generate_infinitetalk(
            input_data,
            size_buckget=resolution,
            motion_frame=motion_frame,
            frame_num=self.args.frame_num,
            shift=self.args.sample_shift,
            sampling_steps=diffusion_steps,
            text_guide_scale=text_guide_scale,
            audio_guide_scale=audio_guide_scale,
            seed=seed,
            n_prompt="",
            offload_model=False,
            max_frames_num=self.args.frame_num if self.args.mode == "clip" else 1000,
            color_correction_strength=1.0 if use_color_correction else 0.0,
            extra_args=self.args,
        )

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = prompt.replace(" ", "_").replace("/", "_")[:30]
        output_filename = f"infinitetalk_{resolution}_{safe_prompt}_{timestamp}"
        output_path = os.path.join(output_dir, output_filename)

        # Save video with audio track
        logger.info(f"Saving video to {output_path}.mp4")
        save_video_ffmpeg(video, output_path, [sum_audio], high_quality_save=False)

        final_video_path = output_path + ".mp4"

        # Calculate metadata
        frame_count = video.shape[0]
        duration_seconds = frame_count / 25.0  # 25fps

        # Get resolution from video tensor (B, H, W, C)
        video_height = video.shape[1]
        video_width = video.shape[2]
        resolution_str = f"{video_width}x{video_height}"

        metadata = {
            "seed": str(seed),
            "diffusion_steps": str(diffusion_steps),
            "text_guide_scale": str(text_guide_scale),
            "audio_guide_scale": str(audio_guide_scale),
            "resolution_bucket": resolution,
            "actual_resolution": resolution_str,
            "motion_frame": str(motion_frame),
            "color_correction": str(use_color_correction),
            "timestamp": timestamp,
        }

        # Free GPU memory for next service
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Video generation completed successfully!")

        return final_video_path, {
            "duration_seconds": duration_seconds,
            "frame_count": frame_count,
            "resolution": resolution_str,
            "metadata": metadata,
        }
