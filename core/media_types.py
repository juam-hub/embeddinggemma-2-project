"""
Media Types and Timestamp Utilities for ChatCasero.
Centralizes format detection, extensions, and time interval formatting.
"""
from pathlib import Path
import re
from typing import Union

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
PDF_EXTENSIONS = {".pdf"}

ALL_SUPPORTED_EXTENSIONS = (
    PDF_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS
)


def get_media_type(filename_or_path: Union[str, Path]) -> str:
    """Returns one of: 'pdf', 'image', 'audio', 'video', or 'unknown'."""
    suffix = Path(filename_or_path).suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return "pdf"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


def is_audio_file(filename_or_path: Union[str, Path]) -> bool:
    return Path(filename_or_path).suffix.lower() in AUDIO_EXTENSIONS


def is_video_file(filename_or_path: Union[str, Path]) -> bool:
    return Path(filename_or_path).suffix.lower() in VIDEO_EXTENSIONS


def is_image_file(filename_or_path: Union[str, Path]) -> bool:
    return Path(filename_or_path).suffix.lower() in IMAGE_EXTENSIONS


def is_pdf_file(filename_or_path: Union[str, Path]) -> bool:
    return Path(filename_or_path).suffix.lower() in PDF_EXTENSIONS


def get_media_icon(media_type_or_filename: Union[str, Path]) -> str:
    """Returns an illustrative emoji for the media type."""
    m_type = (
        media_type_or_filename
        if media_type_or_filename in {"pdf", "image", "audio", "video"}
        else get_media_type(media_type_or_filename)
    )
    if m_type == "audio":
        return "🎵"
    if m_type == "video":
        return "🎬"
    if m_type == "image":
        return "🖼️"
    return "📄"


def format_timestamp(seconds: float) -> str:
    """Formats float seconds into MM:SS or HH:MM:SS format."""
    total_sec = max(0, int(round(seconds)))
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_time_interval(start_sec: float, end_sec: float) -> str:
    """Formats a time interval e.g. '01:15 - 01:30'."""
    return f"{format_timestamp(start_sec)} - {format_timestamp(end_sec)}"


def parse_timestamp(timestamp_str: str) -> float:
    """Parses 'MM:SS' or 'HH:MM:SS' into float seconds."""
    parts = timestamp_str.strip().split(":")
    try:
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        if len(parts) == 1 and parts[0]:
            return float(parts[0])
    except Exception:
        pass
    return 0.0


def sanitize_filename(name: str) -> str:
    """Removes special characters to produce a filesystem-safe identifier."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
