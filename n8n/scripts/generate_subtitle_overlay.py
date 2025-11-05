#!/usr/bin/env python3
"""
ASS Subtitle Overlay Generator for YouTube Shorts
Generates Advanced SubStation Alpha (ASS) subtitle files with:
- Static "Validating Hook" title (0-5s)
- Word-by-word "Engaging Dialogue" captions with active word highlighting
- Bridge/CTA overlay (last 5-8s)

Based on guidance from video-text.md for trauma-informed content.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional


class ASSSubtitleGenerator:
    """Generates ASS subtitle files with advanced styling for YouTube Shorts."""

    # ASS color format: &HAABBGGRR (hex, reversed RGB)
    COLOR_WHITE = "&H00FFFFFF"
    COLOR_YELLOW = "&H0000FFFF"  # Active word highlight
    COLOR_BLACK = "&H00000000"
    COLOR_SEMI_TRANSPARENT_BLACK = "&H80000000"  # For CTA background

    # Vertical alignment codes (ASS format)
    ALIGN_TOP_CENTER = 8        # Hook title
    ALIGN_BOTTOM_CENTER = 2     # Captions and CTA
    ALIGN_MIDDLE_CENTER = 5     # Fallback

    def __init__(self, play_res_x=1920, play_res_y=1080):
        self.script_info = {
            "Title": "YouTube Short Overlay",
            "ScriptType": "v4.00+",
            "PlayResX": play_res_x,  # Source video resolution (before crop/scale)
            "PlayResY": play_res_y,
            "WrapStyle": 0,
            "ScaledBorderAndShadow": "yes"
        }

    def format_time(self, seconds: float) -> str:
        """Convert seconds to ASS timestamp format (H:MM:SS.CS)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

    def generate_style_section(self) -> str:
        """Generate ASS V4+ Styles section."""
        styles = [
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",

            # Hook style: Bold, large, white text at top
            # MarginV=100 for top alignment (distance from top)
            f"Style: Hook,Montserrat,80,{self.COLOR_WHITE},{self.COLOR_WHITE},{self.COLOR_BLACK},{self.COLOR_SEMI_TRANSPARENT_BLACK},-1,0,0,0,100,100,0,0,1,3,2,{self.ALIGN_TOP_CENTER},50,50,100,1",

            # Caption style: Medium weight, white/yellow for active word
            # MarginV=100 for bottom alignment (distance from bottom)
            f"Style: Caption,Montserrat,60,{self.COLOR_WHITE},{self.COLOR_YELLOW},{self.COLOR_BLACK},{self.COLOR_BLACK},0,0,0,0,100,100,0,0,1,3,2,{self.ALIGN_BOTTOM_CENTER},50,50,100,1",

            # CTA style: Bold, large, white with semi-transparent background
            # MarginV=150 for bottom alignment (slightly higher than captions)
            f"Style: CTA,Montserrat,70,{self.COLOR_WHITE},{self.COLOR_WHITE},{self.COLOR_BLACK},{self.COLOR_SEMI_TRANSPARENT_BLACK},-1,0,0,0,100,100,0,0,1,3,2,{self.ALIGN_BOTTOM_CENTER},50,50,150,1"
        ]
        return "\n".join(styles)

    def generate_validating_hook(self, hook_title: str, duration: float = 5.0) -> List[str]:
        """
        Generate static "Validating Hook" title overlay (0-5s).

        Args:
            hook_title: The hook text (may contain line breaks with \\N)
            duration: How long to display (default 5 seconds)

        Returns:
            List of ASS dialogue lines
        """
        # Replace newlines with ASS line break code (uppercase N)
        # Note: We use raw string to ensure proper escaping when written to file
        formatted_title = hook_title.replace("\n", r"\N")

        start_time = self.format_time(0.0)
        end_time = self.format_time(duration)

        return [
            f"Dialogue: 0,{start_time},{end_time},Hook,,0,0,0,,{formatted_title}"
        ]

    def generate_engaging_dialogue(
        self,
        whisperx_data: List[Dict],
        clip_start: float,
        clip_end: float,
        power_words: List[str]
    ) -> List[str]:
        """
        Generate word-by-word captions with active word highlighting.

        Args:
            whisperx_data: List of segments with word-level timing
            clip_start: Clip start time in seconds
            clip_end: Clip end time in seconds
            power_words: Words to emphasize (ALL CAPS)

        Returns:
            List of ASS dialogue lines
        """
        dialogues = []
        power_words_lower = [w.lower() for w in power_words]

        for segment in whisperx_data:
            segment_start = segment.get("start", 0.0)
            segment_end = segment_start + segment.get("duration", 0.0)

            # Skip segments outside clip range
            if segment_end < clip_start or segment_start > clip_end:
                continue

            words = segment.get("words", [])
            if not words:
                # Fallback: no word-level timing, show whole segment
                adjusted_start = max(0, segment_start - clip_start)
                adjusted_end = min(clip_end - clip_start, segment_end - clip_start)

                text = segment.get("text", "").strip()
                if text:
                    dialogues.append(
                        f"Dialogue: 0,{self.format_time(adjusted_start)},{self.format_time(adjusted_end)},Caption,,0,0,0,,{text}"
                    )
                continue

            # Generate word-by-word highlighting
            for i, word_data in enumerate(words):
                word = word_data.get("word", "").strip()
                word_start = word_data.get("start", segment_start)
                word_end = word_data.get("end", word_start + 0.5)

                # Adjust timestamps relative to clip start
                adjusted_start = word_start - clip_start
                adjusted_end = word_end - clip_start

                # Skip if outside clip range
                if adjusted_end < 0 or adjusted_start > (clip_end - clip_start):
                    continue

                # Build context: previous 2 words + current + next 2 words
                context_words = []
                start_idx = max(0, i - 2)
                end_idx = min(len(words), i + 3)

                for j in range(start_idx, end_idx):
                    ctx_word = words[j].get("word", "").strip()

                    if j == i:
                        # Current word: yellow highlight + bold
                        if ctx_word.lower() in power_words_lower:
                            # Power word: always in caps, yellow
                            context_words.append(f"{{\\c{self.COLOR_YELLOW}}}{{\\b1}}{ctx_word.upper()}{{\\b0}}{{\\c{self.COLOR_WHITE}}}")
                        else:
                            context_words.append(f"{{\\c{self.COLOR_YELLOW}}}{{\\b1}}{ctx_word}{{\\b0}}{{\\c{self.COLOR_WHITE}}}")
                    else:
                        # Inactive word: white
                        if ctx_word.lower() in power_words_lower:
                            context_words.append(ctx_word.upper())
                        else:
                            context_words.append(ctx_word)

                caption_text = " ".join(context_words)

                dialogues.append(
                    f"Dialogue: 0,{self.format_time(adjusted_start)},{self.format_time(adjusted_end)},Caption,,0,0,0,,{caption_text}"
                )

        return dialogues

    def generate_bridge_cta(
        self,
        cta_text: str,
        cta_start: float,
        clip_duration: float
    ) -> List[str]:
        """
        Generate Bridge/CTA overlay for last 5-8 seconds.

        Args:
            cta_text: The CTA promise text (e.g., "Watch the full 20-minute breakdown:")
            cta_start: When CTA should appear (in clip-relative seconds)
            clip_duration: Total clip duration

        Returns:
            List of ASS dialogue lines
        """
        start_time = self.format_time(cta_start)
        end_time = self.format_time(clip_duration)

        return [
            f"Dialogue: 0,{start_time},{end_time},CTA,,0,0,0,,{cta_text}"
        ]

    def generate_ass_file(
        self,
        whisperx_json_path: str,
        clip_start: float,
        clip_end: float,
        hook_title: str,
        power_words: List[str],
        cta_start: float,
        cta_text: str,
        output_path: str
    ) -> None:
        """
        Generate complete ASS subtitle file.

        Args:
            whisperx_json_path: Path to WhisperX JSON with word-level timing
            clip_start: Clip start time in seconds
            clip_end: Clip end time in seconds
            hook_title: Static title for first 5 seconds
            power_words: Words to emphasize
            cta_start: When to show CTA (clip-relative)
            cta_text: CTA promise text
            output_path: Where to save ASS file
        """
        # Load WhisperX data
        with open(whisperx_json_path, 'r', encoding='utf-8') as f:
            whisperx_data = json.load(f)

        clip_duration = clip_end - clip_start

        # Convert CTA start from absolute time to clip-relative time
        cta_start_relative = max(0, cta_start - clip_start)

        # Generate all subtitle elements
        hook_dialogues = self.generate_validating_hook(hook_title)
        caption_dialogues = self.generate_engaging_dialogue(
            whisperx_data,
            clip_start,
            clip_end,
            power_words
        )
        cta_dialogues = self.generate_bridge_cta(cta_text, cta_start_relative, clip_duration)

        # Build complete ASS file
        ass_content = [
            "[Script Info]",
            f"Title: {self.script_info['Title']}",
            f"ScriptType: {self.script_info['ScriptType']}",
            f"PlayResX: {self.script_info['PlayResX']}",
            f"PlayResY: {self.script_info['PlayResY']}",
            f"WrapStyle: {self.script_info['WrapStyle']}",
            f"ScaledBorderAndShadow: {self.script_info['ScaledBorderAndShadow']}",
            "",
            "[V4+ Styles]",
            self.generate_style_section(),
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        # Add all dialogues
        ass_content.extend(hook_dialogues)
        ass_content.extend(caption_dialogues)
        ass_content.extend(cta_dialogues)

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(ass_content))

        print(f"Generated ASS subtitle: {output_path}")
        print(f"  - Hook dialogues: {len(hook_dialogues)}")
        print(f"  - Caption dialogues: {len(caption_dialogues)}")
        print(f"  - CTA dialogues: {len(cta_dialogues)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate ASS subtitle overlays for YouTube Shorts"
    )
    parser.add_argument("--whisperx-json", required=True, help="Path to WhisperX JSON file")
    parser.add_argument("--clip-start", type=float, required=True, help="Clip start time (seconds)")
    parser.add_argument("--clip-end", type=float, required=True, help="Clip end time (seconds)")
    parser.add_argument("--hook-title", required=True, help="Static hook title text")
    parser.add_argument("--power-words", default="", help="Comma-separated power words to emphasize")
    parser.add_argument("--cta-start", type=float, required=True, help="CTA start time (clip-relative seconds)")
    parser.add_argument("--cta-text", required=True, help="CTA promise text")
    parser.add_argument("--output", required=True, help="Output ASS file path")

    args = parser.parse_args()

    # Parse power words
    power_words = [w.strip() for w in args.power_words.split(",") if w.strip()]

    # Generate ASS file
    generator = ASSSubtitleGenerator()
    try:
        generator.generate_ass_file(
            whisperx_json_path=args.whisperx_json,
            clip_start=args.clip_start,
            clip_end=args.clip_end,
            hook_title=args.hook_title,
            power_words=power_words,
            cta_start=args.cta_start,
            cta_text=args.cta_text,
            output_path=args.output
        )
        sys.exit(0)
    except Exception as e:
        print(f"Error generating ASS file: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
