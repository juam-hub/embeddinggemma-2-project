"""
Audio Processing Engine for ChatCasero.
Extracts, normalizes, slices, and transcribes audio files into timestamped chunks.
"""
from pathlib import Path
import re
import subprocess
from typing import List, Dict, Any, Optional, Callable
import speech_recognition as sr
import imageio_ffmpeg

from core.config import EXTRACTED_AUDIO_DIR, AUDIO_CHUNK_DURATION
from core.media_types import format_time_interval, format_timestamp, sanitize_filename


class AudioProcessor:
    def __init__(
        self,
        output_dir: Path = EXTRACTED_AUDIO_DIR,
        chunk_duration: float = AUDIO_CHUNK_DURATION,
        language: str = "es-ES"
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_duration = chunk_duration
        self.language = language
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.recognizer = sr.Recognizer()

    def get_duration(self, file_path: Path) -> float:
        """Probes the exact duration of an audio or video file using FFmpeg."""
        try:
            res = subprocess.run(
                [self.ffmpeg_exe, "-i", str(file_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", res.stderr)
            if match:
                h, m, s = match.groups()
                return int(h) * 3600 + int(m) * 60 + float(s)
        except Exception as e:
            print(f"[AudioProcessor] Error probing duration for {file_path}: {e}")
        return 0.0

    def extract_normalized_wav(self, input_path: Path, output_wav: Optional[Path] = None) -> Path:
        """
        Converts any audio or video container to standard 16kHz mono 16-bit PCM WAV.
        This provides maximal compatibility for speech recognition engines.
        """
        input_path = Path(input_path)
        safe_name = sanitize_filename(input_path.stem)
        if output_wav is None:
            output_wav = self.output_dir / f"{safe_name}_normalized.wav"

        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-i", str(input_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(output_wav)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr}")
        return output_wav

    def transcribe_slice(self, wav_path: Path, start_sec: float, duration_sec: float) -> str:
        """Extracts and transcribes a specific audio slice."""
        slice_wav = self.output_dir / f"_slice_{int(start_sec * 1000)}.wav"
        try:
            cmd = [
                self.ffmpeg_exe,
                "-y",
                "-ss", str(start_sec),
                "-t", str(duration_sec),
                "-i", str(wav_path),
                "-acodec", "copy",
                str(slice_wav)
            ]
            subprocess.run(cmd, capture_output=True, check=True)

            with sr.AudioFile(str(slice_wav)) as source:
                audio_data = self.recognizer.record(source)
                try:
                    text = self.recognizer.recognize_google(
                        audio_data, language=self.language
                    )
                    return text.strip()
                except sr.UnknownValueError:
                    # No speech detected in this slice (e.g. silence or music)
                    return ""
                except sr.RequestError as e:
                    # Network issue or rate limit
                    print(f"[AudioProcessor] SpeechRecognition request notice: {e}")
                    return ""
        except Exception as e:
            print(f"[AudioProcessor] Slice transcription error: {e}")
            return ""
        finally:
            if slice_wav.exists():
                try:
                    slice_wav.unlink()
                except Exception:
                    pass

    def process_audio(
        self,
        audio_path: Path,
        doc_name: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Processes an audio file:
        - Extracts 16kHz mono WAV.
        - Calculates total duration.
        - Slices audio into time intervals.
        - Transcribes each interval with exact timestamps.
        - Returns structured metadata and chunks.
        """
        audio_path = Path(audio_path)
        actual_doc_name = doc_name or audio_path.name
        safe_name = sanitize_filename(Path(actual_doc_name).stem)

        if progress_callback:
            progress_callback(0.05, f"Normalizando audio de '{actual_doc_name}'...")

        norm_wav = self.extract_normalized_wav(audio_path)
        total_duration = self.get_duration(norm_wav)
        if total_duration <= 0.0:
            total_duration = self.get_duration(audio_path)

        if total_duration <= 0.0:
            # Fallback minimum 1 second if probe failed
            total_duration = 1.0

        chunks: List[Dict[str, Any]] = []
        cur_start = 0.0
        step = self.chunk_duration
        total_slices = max(1, int((total_duration + step - 1) // step))
        slice_idx = 0

        while cur_start < total_duration:
            cur_end = min(total_duration, cur_start + step)
            duration_slice = cur_end - cur_start
            slice_idx += 1

            if progress_callback:
                pct = 0.1 + 0.8 * (slice_idx / total_slices)
                progress_callback(
                    min(0.95, pct),
                    f"Transcribiendo audio [{format_timestamp(cur_start)} - {format_timestamp(cur_end)}] ({slice_idx}/{total_slices})..."
                )

            text = self.transcribe_slice(norm_wav, cur_start, duration_slice)
            time_interval_str = format_time_interval(cur_start, cur_end)

            # Even if silent, if nothing has been recorded yet or if we have speech, record it
            chunk_content = (
                f"[AUDIO {actual_doc_name} | {time_interval_str}]\n{text}"
                if text
                else f"[AUDIO {actual_doc_name} | {time_interval_str}]\n(Sin locución o sonido ambiente)"
            )

            chunk_id = f"{safe_name}_aud_s{int(cur_start)}"
            chunks.append({
                "chunk_id": chunk_id,
                "doc_name": actual_doc_name,
                "page_number": 1,  # Kept for backward compatibility
                "start_time": cur_start,
                "end_time": cur_end,
                "timestamp_label": time_interval_str,
                "content": chunk_content,
                "raw_text": text,
                "source_type": "audio_transcript",
                "media_type": "audio",
                "audio_path": str(audio_path)
            })

            cur_start += step

        # Compile full transcript
        spoken_texts = [c["raw_text"] for c in chunks if c.get("raw_text")]
        full_transcript = "\n".join(spoken_texts) if spoken_texts else "(Sin locución identificada)"

        return {
            "doc_name": actual_doc_name,
            "media_type": "audio",
            "file_path": str(audio_path),
            "duration": total_duration,
            "duration_str": format_timestamp(total_duration),
            "total_chunks": len(chunks),
            "chunks": chunks,
            "full_transcript": full_transcript
        }
