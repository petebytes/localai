"""File path validation and utilities."""

import os
from pathlib import Path


def validate_file_exists(file_path: str, file_type: str = "file") -> None:
    """Validate that a file exists and is readable.

    Args:
        file_path: Path to file to validate
        file_type: Description of file type for error messages

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If path is empty or invalid
    """
    if not file_path:
        raise ValueError(f"{file_type} path cannot be empty")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_type} not found: {file_path}")

    if not os.path.isfile(file_path):
        raise ValueError(f"{file_type} path is not a file: {file_path}")

    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"{file_type} is not readable: {file_path}")


def ensure_directory_exists(directory_path: str) -> None:
    """Ensure a directory exists, creating it if necessary.

    Args:
        directory_path: Path to directory

    Raises:
        PermissionError: If directory cannot be created
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def get_file_extension(file_path: str) -> str:
    """Get file extension in lowercase.

    Args:
        file_path: Path to file

    Returns:
        File extension (e.g., '.mp3', '.wav')
    """
    return Path(file_path).suffix.lower()


def is_audio_file(file_path: str) -> bool:
    """Check if file is a supported audio format.

    Args:
        file_path: Path to file

    Returns:
        True if file has audio extension
    """
    audio_extensions = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
    return get_file_extension(file_path) in audio_extensions


def is_image_file(file_path: str) -> bool:
    """Check if file is a supported image format.

    Args:
        file_path: Path to file

    Returns:
        True if file has image extension
    """
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
    return get_file_extension(file_path) in image_extensions


def is_video_file(file_path: str) -> bool:
    """Check if file is a supported video format.

    Args:
        file_path: Path to file

    Returns:
        True if file has video extension
    """
    video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    return get_file_extension(file_path) in video_extensions
