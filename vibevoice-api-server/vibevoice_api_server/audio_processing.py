"""Audio processing utilities for VibeVoice API."""

import base64
import io
import logging
from typing import Tuple
import numpy as np
import torch
import librosa
import soundfile as sf
from pydub import AudioSegment

from .models import OutputFormat

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Audio processing utilities."""

    TARGET_SAMPLE_RATE = 24000  # VibeVoice requires 24kHz

    @staticmethod
    def decode_base64_audio(
        audio_base64: str,
    ) -> Tuple[np.ndarray, int]:
        """Decode base64 encoded audio to numpy array.

        Args:
            audio_base64: Base64 encoded audio data

        Returns:
            Tuple of (audio_array, sample_rate)

        Raises:
            ValueError: If audio cannot be decoded
        """
        try:
            # Decode base64
            audio_bytes = base64.b64decode(audio_base64)

            # Load with soundfile
            audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))

            return audio_data, sample_rate

        except Exception as e:
            logger.error(f"Failed to decode audio: {e}")
            raise ValueError(f"Invalid audio data: {e}")

    @staticmethod
    def resample_audio(
        audio: np.ndarray,
        orig_sr: int,
        target_sr: int = TARGET_SAMPLE_RATE,
    ) -> np.ndarray:
        """Resample audio to target sample rate.

        Args:
            audio: Audio array
            orig_sr: Original sample rate
            target_sr: Target sample rate

        Returns:
            Resampled audio array
        """
        if orig_sr == target_sr:
            return audio

        logger.info(f"Resampling from {orig_sr}Hz to {target_sr}Hz")
        return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)

    @staticmethod
    def normalize_audio(audio: np.ndarray) -> np.ndarray:
        """Normalize audio to [-1, 1] range.

        Args:
            audio: Audio array

        Returns:
            Normalized audio array
        """
        max_val = np.abs(audio).max()
        if max_val > 0:
            return audio / max_val
        return audio

    @staticmethod
    def adjust_voice_speed(
        audio: np.ndarray,
        sample_rate: int,
        speed_factor: float,
    ) -> np.ndarray:
        """Adjust voice speed using time stretching.

        Args:
            audio: Audio array
            sample_rate: Sample rate
            speed_factor: Speed adjustment (0.8-1.2)

        Returns:
            Speed-adjusted audio array
        """
        if abs(speed_factor - 1.0) < 0.01:
            return audio

        logger.info(f"Adjusting speed by factor: {speed_factor}")
        return librosa.effects.time_stretch(audio, rate=speed_factor)

    @staticmethod
    def trim_silence(
        audio: np.ndarray,
        sample_rate: int,
        top_db: int = 40,
    ) -> np.ndarray:
        """Trim silence from beginning and end of audio.

        Args:
            audio: Audio array
            sample_rate: Sample rate
            top_db: Threshold in dB below reference to consider as silence

        Returns:
            Trimmed audio array
        """
        trimmed_audio, _ = librosa.effects.trim(
            audio, top_db=top_db, frame_length=2048, hop_length=512
        )
        logger.info(
            f"Trimmed audio from {len(audio) / sample_rate:.2f}s to {len(trimmed_audio) / sample_rate:.2f}s"
        )
        return trimmed_audio

    @staticmethod
    def prepare_voice_sample(
        audio_base64: str,
        speed_factor: float = 1.0,
    ) -> Tuple[torch.Tensor, int]:
        """Prepare voice sample for VibeVoice processing.

        Args:
            audio_base64: Base64 encoded audio
            speed_factor: Speed adjustment factor

        Returns:
            Tuple of (audio_tensor, sample_rate)
        """
        # Decode audio
        audio, orig_sr = AudioProcessor.decode_base64_audio(audio_base64)

        # Ensure mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Resample to 24kHz
        audio = AudioProcessor.resample_audio(
            audio, orig_sr, AudioProcessor.TARGET_SAMPLE_RATE
        )

        # Apply speed adjustment
        if abs(speed_factor - 1.0) >= 0.01:
            audio = AudioProcessor.adjust_voice_speed(
                audio, AudioProcessor.TARGET_SAMPLE_RATE, speed_factor
            )

        # Normalize
        audio = AudioProcessor.normalize_audio(audio)

        # Convert to tensor
        audio_tensor = torch.from_numpy(audio).float()

        return audio_tensor, AudioProcessor.TARGET_SAMPLE_RATE

    @staticmethod
    def tensor_to_base64(
        audio_tensor: torch.Tensor,
        sample_rate: int,
        output_format: OutputFormat = OutputFormat.WAV,
    ) -> str:
        """Convert audio tensor to base64 encoded audio.

        Args:
            audio_tensor: Audio tensor
            sample_rate: Sample rate
            output_format: Output audio format

        Returns:
            Base64 encoded audio
        """
        # Convert to numpy (convert bfloat16 to float32 first if needed)
        if audio_tensor.device != torch.device("cpu"):
            audio_tensor = audio_tensor.cpu()
        if audio_tensor.dtype == torch.bfloat16:
            audio_tensor = audio_tensor.to(torch.float32)
        audio_np = audio_tensor.numpy()

        # Ensure audio is 1D (flatten if needed)
        if audio_np.ndim > 1:
            audio_np = audio_np.flatten()

        # Normalize to prevent clipping
        max_val = np.abs(audio_np).max()
        if max_val > 1.0:
            audio_np = audio_np / max_val

        # Convert to bytes
        buffer = io.BytesIO()
        buffer.name = "audio.wav"  # Required for soundfile to detect format

        if output_format == OutputFormat.WAV:
            sf.write(buffer, audio_np, sample_rate, format="WAV", subtype="PCM_16")
        else:
            # Use pydub for MP3/OGG conversion
            # First write to WAV
            wav_buffer = io.BytesIO()
            wav_buffer.name = "temp.wav"  # Required for soundfile
            sf.write(wav_buffer, audio_np, sample_rate, format="WAV", subtype="PCM_16")
            wav_buffer.seek(0)

            # Convert to target format
            audio_segment = AudioSegment.from_wav(wav_buffer)

            if output_format == OutputFormat.MP3:
                audio_segment.export(buffer, format="mp3", bitrate="192k")
            elif output_format == OutputFormat.OGG:
                audio_segment.export(buffer, format="ogg", codec="libvorbis")

        # Encode to base64
        buffer.seek(0)
        audio_bytes = buffer.read()
        return base64.b64encode(audio_bytes).decode("utf-8")

    @staticmethod
    def create_silence(
        duration_ms: int,
        sample_rate: int = TARGET_SAMPLE_RATE,
    ) -> torch.Tensor:
        """Create silence tensor.

        Args:
            duration_ms: Duration in milliseconds
            sample_rate: Sample rate

        Returns:
            Silence audio tensor
        """
        num_samples = int((duration_ms / 1000.0) * sample_rate)
        return torch.zeros(num_samples)

    @staticmethod
    def concatenate_audio(
        audio_segments: list[torch.Tensor],
    ) -> torch.Tensor:
        """Concatenate multiple audio segments.

        Args:
            audio_segments: List of audio tensors

        Returns:
            Concatenated audio tensor
        """
        return torch.cat(audio_segments, dim=-1)

    @staticmethod
    def get_duration(audio_tensor: torch.Tensor, sample_rate: int) -> float:
        """Get audio duration in seconds.

        Args:
            audio_tensor: Audio tensor
            sample_rate: Sample rate

        Returns:
            Duration in seconds
        """
        return audio_tensor.shape[-1] / sample_rate
