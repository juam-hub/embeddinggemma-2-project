"""
Video Processing Engine for ChatCasero.
Processes video files by extracting:
1. Audio speech transcription with exact time intervals (what is heard).
2. Keyframes / representative visual frames analyzed with Qwen2.5-VL (what is seen).
"""
from pathlib import Path
import subprocess
from typing import List, Dict, Any, Optional, Callable
from PIL import Image
import imageio_ffmpeg

from core.config import (
    EXTRACTED_FRAMES_DIR,
    VIDEO_FRAME_INTERVAL,
    MAX_VIDEO_FRAMES,
)
from core.media_types import (
    format_timestamp,
    format_time_interval,
    sanitize_filename
)
from core.audio_processor import AudioProcessor
from core.visual_analyzer import VisualAnalyzer


class VideoProcessor:
    def __init__(
        self,
        output_dir: Path = EXTRACTED_FRAMES_DIR,
        frame_interval: float = VIDEO_FRAME_INTERVAL,
        max_frames: int = MAX_VIDEO_FRAMES,
        audio_processor: Optional[AudioProcessor] = None,
        visual_analyzer: Optional[VisualAnalyzer] = None
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.frame_interval = frame_interval
        self.max_frames = max_frames
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.audio_processor = audio_processor or AudioProcessor()
        self.visual_analyzer = visual_analyzer or VisualAnalyzer()

    def get_duration(self, video_path: Path) -> float:
        """Probes video duration in seconds."""
        return self.audio_processor.get_duration(video_path)

    def extract_frame_at_timestamp(
        self,
        video_path: Path,
        timestamp_sec: float,
        output_image_path: Path
    ) -> bool:
        """Extracts a single high-quality frame at the specified timestamp using FFmpeg."""
        try:
            cmd = [
                self.ffmpeg_exe,
                "-y",
                "-ss", str(timestamp_sec),
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",
                str(output_image_path)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and output_image_path.exists():
                return True
        except Exception as e:
            print(f"[VideoProcessor] Error extracting frame at {timestamp_sec}s: {e}")
        return False

    def process_video(
        self,
        video_path: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes complete video ingestion:
        - Probes video duration.
        - Transcribes audio track with timestamps.
        - Extracts representative visual frames with timestamps.
        - Analyzes visual frames with Qwen2.5-VL for complete visual comprehension.
        """
        video_path = Path(video_path)
        doc_name = video_path.name
        safe_name = sanitize_filename(video_path.stem)

        if progress_callback:
            progress_callback(0.05, f"Determinando metadatos y duración del video '{doc_name}'...")

        total_duration = self.get_duration(video_path)
        if total_duration <= 0.0:
            total_duration = 1.0

        # ── 1. Process Audio Track (What is heard) ───────────────────────
        if progress_callback:
            progress_callback(0.1, "Extrayendo y transcribiendo pista de audio del video...")

        def audio_cb(val: float, text: str):
            if progress_callback:
                # Map audio progress into 0.10 -> 0.45 window
                progress_callback(0.1 + 0.35 * val, f"[Audio] {text}")

        audio_res = self.audio_processor.process_audio(
            video_path,
            doc_name=doc_name,
            progress_callback=audio_cb
        )

        audio_chunks = audio_res.get("chunks", [])
        for c in audio_chunks:
            c["source_type"] = "audio_transcript"
            c["media_type"] = "video"

        # ── 2. Select timestamps for Visual Frames (What is seen) ─────────
        interval = self.frame_interval
        num_frames = int(total_duration // interval)
        if num_frames > self.max_frames:
            interval = total_duration / self.max_frames
            num_frames = self.max_frames
        elif num_frames < 2 and total_duration > 2.0:
            interval = total_duration / 2.0
            num_frames = 2
        elif num_frames < 1:
            num_frames = 1
            interval = total_duration

        frame_timestamps = []
        cur_t = min(1.0, total_duration * 0.1)
        while cur_t < total_duration and len(frame_timestamps) < self.max_frames:
            frame_timestamps.append(cur_t)
            cur_t += interval

        if not frame_timestamps:
            frame_timestamps = [0.0]

        # ── 3. Extract & Analyze Visual Frames ───────────────────────────
        visual_elements: List[Dict[str, Any]] = []
        total_f = len(frame_timestamps)

        for idx, t_sec in enumerate(frame_timestamps):
            t_start = t_sec
            t_end = min(total_duration, t_sec + interval)
            time_label = format_time_interval(t_start, t_end)
            elem_id = f"{safe_name}_vf_{int(t_start)}"
            frame_filename = f"{elem_id}.png"
            frame_path = self.output_dir / frame_filename

            if progress_callback:
                pct = 0.45 + 0.50 * ((idx + 1) / total_f)
                progress_callback(
                    pct,
                    f"Analizando fotograma visual [{format_timestamp(t_start)}] ({idx + 1}/{total_f}) con Qwen2.5-VL..."
                )

            extracted = self.extract_frame_at_timestamp(video_path, t_start, frame_path)
            if not extracted:
                continue

            # Read image dimensions
            try:
                with Image.open(frame_path) as im:
                    w, h = im.size
            except Exception:
                w, h = 640, 480

            # Analyze frame with Qwen2.5-VL
            analysis = self.visual_analyzer.analyze_image(frame_path)
            category = analysis.get("categoria", "Fotografía/Ilustración")
            transcription = analysis.get("transcripcion", "")
            description = analysis.get("descripcion_detallada", "")

            visual_elements.append({
                "element_id": elem_id,
                "doc_name": doc_name,
                "page_number": idx + 1,  # Frame index as page equivalent
                "start_time": t_start,
                "end_time": t_end,
                "timestamp_label": time_label,
                "element_type": "video_frame",
                "media_type": "video",
                "image_path": str(frame_path),
                "visual_category": category,
                "transcription": transcription,
                "description": description,
                "width": w,
                "height": h
            })

        return {
            "doc_name": doc_name,
            "media_type": "video",
            "file_path": str(video_path),
            "duration": total_duration,
            "duration_str": format_timestamp(total_duration),
            "audio_chunks": audio_chunks,
            "visual_elements": visual_elements
        }
