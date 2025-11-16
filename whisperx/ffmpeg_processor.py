"""
FFmpeg Video Processor for WhisperX
Optimized for speech recognition with RTX 5090 hardware acceleration (9th-gen NVENC/NVDEC)
Based on 2025 best practices for audio extraction and enhancement
"""

import subprocess
import os
import logging
from pathlib import Path
from typing import Dict
import json

logger = logging.getLogger(__name__)


class FFmpegProcessor:
    """
    FFmpeg processor optimized for speech recognition.

    Features:
    - Speech-optimized audio extraction (16kHz mono)
    - Hardware acceleration (9th-gen NVENC/NVDEC for RTX 5090)
    - Speech enhancement filters
    - Memory-efficient streaming
    - Metadata extraction
    """

    def __init__(self, use_hw_accel: bool = True, enhance_speech: bool = True):
        """
        Initialize FFmpeg processor.

        Args:
            use_hw_accel: Enable NVIDIA hardware acceleration
            enhance_speech: Apply speech enhancement filters
        """
        self.use_hw_accel = use_hw_accel
        self.enhance_speech = enhance_speech
        self._verify_ffmpeg()

    def _verify_ffmpeg(self):
        """Verify FFmpeg is installed and accessible."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, check=True
            )
            logger.info("FFmpeg verified successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg verification failed: {e}")
            raise RuntimeError("FFmpeg not found or not working")

    def get_video_info(self, video_path: str) -> Dict:
        """
        Extract video metadata using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with video metadata
        """
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            metadata = json.loads(result.stdout)

            # Extract useful info
            format_info = metadata.get("format", {})
            video_stream = next(
                (s for s in metadata.get("streams", []) if s["codec_type"] == "video"),
                {},
            )
            audio_stream = next(
                (s for s in metadata.get("streams", []) if s["codec_type"] == "audio"),
                {},
            )

            return {
                "duration": float(format_info.get("duration", 0)),
                "size_bytes": int(format_info.get("size", 0)),
                "format": format_info.get("format_name", ""),
                "video_codec": video_stream.get("codec_name", ""),
                "video_width": video_stream.get("width", 0),
                "video_height": video_stream.get("height", 0),
                "audio_codec": audio_stream.get("codec_name", ""),
                "audio_sample_rate": int(audio_stream.get("sample_rate", 0)),
                "audio_channels": audio_stream.get("channels", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {}

    def extract_audio_optimized(
        self,
        video_path: str,
        output_path: str,
        sample_rate: int = 16000,
        channels: int = 1,
        codec: str = "pcm_s16le",
    ) -> str:
        """
        Extract audio from video with speech optimization.

        Based on 2025 research best practices:
        - 16kHz sample rate (Whisper's native rate)
        - Mono channel (reduces size, no quality loss for speech)
        - PCM 16-bit for maximum quality
        - Speech enhancement filters applied

        Args:
            video_path: Input video file
            output_path: Output audio file (.wav)
            sample_rate: Audio sample rate (default 16000 Hz)
            channels: Number of channels (1=mono, 2=stereo)
            codec: Audio codec (default pcm_s16le)

        Returns:
            Path to extracted audio file
        """
        logger.info(f"Extracting audio from {video_path}")

        # Build FFmpeg command
        cmd = ["ffmpeg"]

        # Hardware acceleration for decoding (must come BEFORE input file)
        if self.use_hw_accel:
            cmd.extend(["-hwaccel", "cuda"])

        # Add input file
        cmd.extend(["-i", video_path])

        # Audio filters for speech enhancement
        filters = []

        if self.enhance_speech:
            # High-pass filter: remove frequencies below 100Hz (removes rumble)
            filters.append("highpass=f=100")

            # Low-pass filter: remove frequencies above 10kHz (speech is <10kHz)
            filters.append("lowpass=f=10000")

            # Dynamic audio normalization (better than simple volume)
            filters.append("dynaudnorm")

        # Apply filters if any
        if filters:
            cmd.extend(["-af", ",".join(filters)])

        # Audio output settings
        cmd.extend(
            [
                "-vn",  # No video
                "-acodec",
                codec,
                "-ar",
                str(sample_rate),
                "-ac",
                str(channels),
                "-y",  # Overwrite output file
                output_path,
            ]
        )

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Audio extracted successfully to {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg extraction failed: {e.stderr}")
            raise RuntimeError(f"Audio extraction failed: {e.stderr}")

    def detect_silence(
        self,
        audio_path: str,
        min_silence_duration: float = 2.0,
        silence_threshold: str = "-50dB",
    ) -> list:
        """
        Detect silence periods in audio for intelligent segmentation.

        Args:
            audio_path: Path to audio file
            min_silence_duration: Minimum silence duration in seconds
            silence_threshold: Silence threshold (e.g., '-50dB')

        Returns:
            List of silence periods as (start, end) tuples
        """
        cmd = [
            "ffmpeg",
            "-i",
            audio_path,
            "-af",
            f"silencedetect=noise={silence_threshold}:d={min_silence_duration}",
            "-f",
            "null",
            "-",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Parse silence detection output
            silences = []
            lines = result.stderr.split("\n")

            silence_start = None
            for line in lines:
                if "silence_start" in line:
                    parts = line.split("silence_start: ")
                    if len(parts) > 1:
                        silence_start = float(parts[1].strip())
                elif "silence_end" in line and silence_start is not None:
                    parts = line.split("silence_end: ")
                    if len(parts) > 1:
                        silence_end_str = parts[1].split("|")[0].strip()
                        silence_end = float(silence_end_str)
                        silences.append((silence_start, silence_end))
                        silence_start = None

            logger.info(f"Detected {len(silences)} silence periods")
            return silences

        except Exception as e:
            logger.error(f"Silence detection failed: {e}")
            return []

    def segment_video(
        self,
        video_path: str,
        output_dir: str,
        segment_duration: int = 600,
        use_hw_accel: bool = True,
    ) -> list:
        """
        Segment video into smaller chunks using stream copy (fast, no re-encoding).

        Args:
            video_path: Input video file
            output_dir: Directory for output segments
            segment_duration: Segment length in seconds (default 600 = 10 minutes)
            use_hw_accel: Use hardware acceleration

        Returns:
            List of segment file paths
        """
        os.makedirs(output_dir, exist_ok=True)

        base_name = Path(video_path).stem
        output_pattern = os.path.join(output_dir, f"{base_name}_segment_%03d.mp4")

        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-c",
            "copy",  # Stream copy (no re-encoding, very fast)
            "-map",
            "0",
            "-segment_time",
            str(segment_duration),
            "-f",
            "segment",
            "-reset_timestamps",
            "1",
            "-y",
            output_pattern,
        ]

        try:
            logger.info(f"Segmenting video into {segment_duration}s chunks")
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Find all created segments
            segments = sorted(
                [
                    os.path.join(output_dir, f)
                    for f in os.listdir(output_dir)
                    if f.startswith(f"{base_name}_segment_") and f.endswith(".mp4")
                ]
            )

            logger.info(f"Created {len(segments)} video segments")
            return segments

        except subprocess.CalledProcessError as e:
            logger.error(f"Video segmentation failed: {e.stderr}")
            raise RuntimeError(f"Segmentation failed: {e.stderr}")

    def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        font_size: int = 24,
        font_color: str = "white",
        use_hw_accel: bool = True,
    ) -> str:
        """
        Burn subtitles into video using NVENC hardware acceleration.

        Args:
            video_path: Input video file
            subtitle_path: SRT or VTT subtitle file
            output_path: Output video file
            font_size: Subtitle font size
            font_color: Subtitle color
            use_hw_accel: Use NVENC for encoding

        Returns:
            Path to output video
        """
        logger.info(f"Burning subtitles into {video_path}")

        # Escape subtitle path for FFmpeg filter
        subtitle_path_escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")

        cmd = ["ffmpeg"]

        # Hardware decoding (must come BEFORE input file)
        if use_hw_accel and self.use_hw_accel:
            cmd.extend(["-hwaccel", "cuda"])

        # Add input file
        cmd.extend(["-i", video_path])

        # Subtitle filter
        cmd.extend(
            [
                "-vf",
                f"subtitles='{subtitle_path_escaped}':force_style='FontSize={font_size},PrimaryColour={font_color}'",
            ]
        )

        # Hardware encoding with NVENC (RTX 5090's 9th-gen NVENC)
        if use_hw_accel and self.use_hw_accel:
            cmd.extend(
                [
                    "-c:v",
                    "h264_nvenc",
                    "-preset",
                    "p6",  # High quality preset (RTX 5090 9th-gen NVENC)
                    "-cq",
                    "23",  # Constant quality
                    "-b:v",
                    "0",  # Let CQ control bitrate
                ]
            )
        else:
            cmd.extend(["-c:v", "libx264", "-crf", "23"])

        # Copy audio without re-encoding
        cmd.extend(["-c:a", "copy", "-y", output_path])

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Subtitles burned successfully to {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Subtitle burning failed: {e.stderr}")
            raise RuntimeError(f"Failed to burn subtitles: {e.stderr}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    processor = FFmpegProcessor()

    # Example: Get video info
    # info = processor.get_video_info('sample.mp4')
    # print(f"Video duration: {info['duration']}s")

    # Example: Extract audio
    # processor.extract_audio_optimized('sample.mp4', 'output.wav')

    print("FFmpeg processor initialized successfully")
