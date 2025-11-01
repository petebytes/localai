"""Core TTS generation logic for VibeVoice."""

import re
import logging
from typing import Optional, List, Tuple, Dict
import torch

from .audio_processing import AudioProcessor
from .model_manager import ModelManager

logger = logging.getLogger(__name__)


class TTSGenerator:
    """Text-to-speech generation using VibeVoice."""

    def __init__(self, model_manager: ModelManager):
        """Initialize TTS generator.

        Args:
            model_manager: Model manager instance
        """
        self.model_manager = model_manager
        self.audio_processor = AudioProcessor()

    def parse_pause_keywords(self, text: str) -> List[Tuple[str, str]]:
        """Parse [pause] and [pause:ms] tags from text.

        Args:
            text: Input text with pause tags

        Returns:
            List of (text_segment, pause_duration_ms) tuples
        """
        # Pattern: [pause] or [pause:1000]
        pause_pattern = r"\[pause(?::(\d+))?\]"

        segments = []
        last_end = 0

        for match in re.finditer(pause_pattern, text):
            # Get text before pause
            text_segment = text[last_end : match.start()].strip()

            # Get pause duration (default 1000ms)
            pause_ms = match.group(1) if match.group(1) else "1000"

            if text_segment:
                segments.append((text_segment, None))

            segments.append(("", pause_ms))
            last_end = match.end()

        # Add remaining text
        remaining = text[last_end:].strip()
        if remaining:
            segments.append((remaining, None))

        # If no pauses found, return full text
        if not segments:
            segments = [(text, None)]

        return segments

    def split_text_into_chunks(self, text: str, max_words: int = 250) -> List[str]:
        """Split text into chunks at sentence boundaries.

        Args:
            text: Input text
            max_words: Maximum words per chunk

        Returns:
            List of text chunks
        """
        # Split by sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = []
        current_word_count = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())

            if current_word_count + sentence_words > max_words and current_chunk:
                # Save current chunk and start new one
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_word_count = sentence_words
            else:
                current_chunk.append(sentence)
                current_word_count += sentence_words

        # Add remaining chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks if chunks else [text]

    def generate_single_speaker(
        self,
        text: str,
        voice_audio: Optional[torch.Tensor] = None,
        seed: int = 42,
        cfg_scale: float = 1.3,
        diffusion_steps: int = 20,
        use_sampling: bool = False,
        temperature: float = 0.95,
        top_p: float = 0.95,
        voice_speed_factor: float = 1.0,
        max_words_per_chunk: int = 250,
    ) -> torch.Tensor:
        """Generate single-speaker TTS.

        Args:
            text: Text to synthesize
            voice_audio: Optional voice sample tensor for cloning
            seed: Random seed
            cfg_scale: Classifier-free guidance scale
            diffusion_steps: Number of diffusion steps
            use_sampling: Use sampling instead of greedy
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            voice_speed_factor: Voice speed adjustment
            max_words_per_chunk: Max words per chunk

        Returns:
            Generated audio tensor
        """
        model, processor = self.model_manager.get_model_and_processor()

        # Set seed
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

        # Parse pauses
        segments = self.parse_pause_keywords(text)

        all_audio_segments = []

        for text_segment, pause_ms in segments:
            if pause_ms:
                # Add silence
                silence = self.audio_processor.create_silence(int(pause_ms))
                all_audio_segments.append(silence)
            else:
                # Generate speech for text segment
                chunks = self.split_text_into_chunks(text_segment, max_words_per_chunk)

                for chunk in chunks:
                    logger.info(f"Generating audio for chunk: {chunk[:50]}...")

                    # Format text for VibeVoice - single speaker uses Speaker 0
                    formatted_text = f"Speaker 0: {chunk}"

                    # Prepare inputs
                    if voice_audio is not None:
                        voice_samples = [voice_audio]
                    else:
                        voice_samples = None

                    inputs = processor(
                        [formatted_text],
                        voice_samples=voice_samples,
                        return_tensors="pt",
                        return_attention_mask=True,
                    )

                    # Move to device (filter out None values)
                    device = self.model_manager.current_device
                    inputs = {
                        k: v.to(device) if v is not None and hasattr(v, "to") else v
                        for k, v in inputs.items()
                    }

                    # Generate
                    generation_kwargs = {
                        "tokenizer": processor.tokenizer,
                        "cfg_scale": cfg_scale,
                        "max_new_tokens": None,
                        "do_sample": use_sampling,
                    }

                    if use_sampling:
                        generation_kwargs["temperature"] = temperature
                        generation_kwargs["top_p"] = top_p

                    with torch.no_grad():
                        output = model.generate(**inputs, **generation_kwargs)

                    # Extract audio
                    audio_tensor = torch.cat(output.speech_outputs, dim=-1)
                    all_audio_segments.append(audio_tensor.cpu())

        # Concatenate all segments
        final_audio = self.audio_processor.concatenate_audio(all_audio_segments)
        return final_audio

    def parse_multi_speaker_text(self, text: str) -> List[Tuple[int, str]]:
        """Parse multi-speaker text with [N]: markers.

        Args:
            text: Multi-speaker text

        Returns:
            List of (speaker_id, text) tuples

        Raises:
            ValueError: If format is invalid
        """
        # Pattern: [1]: Hello, how are you?
        pattern = r"\[(\d)\]:\s*(.*?)(?=\[\d\]:|$)"

        segments = []
        for match in re.finditer(pattern, text, re.DOTALL):
            speaker_id = int(match.group(1))
            speaker_text = match.group(2).strip()

            if speaker_id < 1 or speaker_id > 4:
                raise ValueError(f"Invalid speaker ID: {speaker_id}. Must be 1-4.")

            segments.append((speaker_id, speaker_text))

        if not segments:
            raise ValueError("No valid speaker segments found in text")

        return segments

    def generate_multi_speaker(
        self,
        text: str,
        speaker_voices: Dict[int, Optional[torch.Tensor]],
        seed: int = 42,
        cfg_scale: float = 1.3,
        diffusion_steps: int = 20,
        use_sampling: bool = False,
        temperature: float = 0.95,
        top_p: float = 0.95,
        voice_speed_factor: float = 1.0,
        max_words_per_chunk: int = 250,
    ) -> torch.Tensor:
        """Generate multi-speaker TTS.

        Args:
            text: Multi-speaker text with [N]: markers
            speaker_voices: Dict mapping speaker ID to voice tensor
            seed: Random seed
            cfg_scale: CFG scale
            diffusion_steps: Diffusion steps
            use_sampling: Use sampling
            temperature: Temperature
            top_p: Top-p
            voice_speed_factor: Speed factor
            max_words_per_chunk: Chunk size

        Returns:
            Generated audio tensor
        """
        # Parse speaker segments
        segments = self.parse_multi_speaker_text(text)

        # Generate each segment
        all_audio = []

        for speaker_id, speaker_text in segments:
            logger.info(f"Generating speaker {speaker_id}: {speaker_text[:50]}...")

            voice_audio = speaker_voices.get(speaker_id)

            # Generate for this speaker
            audio = self.generate_single_speaker(
                text=speaker_text,
                voice_audio=voice_audio,
                seed=seed,
                cfg_scale=cfg_scale,
                diffusion_steps=diffusion_steps,
                use_sampling=use_sampling,
                temperature=temperature,
                top_p=top_p,
                voice_speed_factor=voice_speed_factor,
                max_words_per_chunk=max_words_per_chunk,
            )

            all_audio.append(audio)

        # Concatenate all speaker segments
        return self.audio_processor.concatenate_audio(all_audio)

    async def generate_single_speaker_stream(
        self,
        text: str,
        voice_audio: Optional[torch.Tensor] = None,
        **kwargs,
    ):
        """Generate single-speaker TTS with streaming.

        Args:
            text: Text to synthesize
            voice_audio: Optional voice sample
            **kwargs: Additional generation parameters

        Yields:
            Audio chunks as they are generated
        """
        # Parse and chunk text
        segments = self.parse_pause_keywords(text)

        chunk_index = 0

        for text_segment, pause_ms in segments:
            if pause_ms:
                # Yield silence chunk
                silence = self.audio_processor.create_silence(int(pause_ms))
                yield {
                    "chunk_index": chunk_index,
                    "audio": silence,
                    "text_segment": f"[pause:{pause_ms}]",
                    "is_final": False,
                }
                chunk_index += 1
            else:
                # Split into chunks and generate each
                chunks = self.split_text_into_chunks(
                    text_segment, kwargs.get("max_words_per_chunk", 250)
                )

                for i, chunk in enumerate(chunks):
                    # Generate audio for this chunk
                    audio = self.generate_single_speaker(
                        text=chunk,
                        voice_audio=voice_audio,
                        **kwargs,
                    )

                    yield {
                        "chunk_index": chunk_index,
                        "audio": audio,
                        "text_segment": chunk,
                        "is_final": False,
                    }
                    chunk_index += 1

        # Mark final chunk
        yield {
            "chunk_index": chunk_index,
            "audio": None,
            "text_segment": "",
            "is_final": True,
        }
