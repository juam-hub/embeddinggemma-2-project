"""
Integration and Unit Tests for Audio and Video Scalable Pipeline in ChatCasero.
"""
import unittest
from pathlib import Path
import subprocess
import imageio_ffmpeg

from core.media_types import (
    get_media_type,
    get_media_icon,
    format_timestamp,
    format_time_interval,
    parse_timestamp,
    is_audio_file,
    is_video_file,
)
from core.audio_processor import AudioProcessor
from core.video_processor import VideoProcessor
from core.stats_manager import StatsManager
from core.vector_store import VectorStore
from core.config import DATA_DIR


class TestMediaPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        cls.test_wav = DATA_DIR / "_test_sample.wav"
        cls.test_mp4 = DATA_DIR / "_test_sample.mp4"

        # Generate synthetic 3-second test audio
        subprocess.run([
            cls.ffmpeg, "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-ar", "16000", "-ac", "1",
            str(cls.test_wav)
        ], capture_output=True, check=True)

        # Generate synthetic 3-second test video with video frames and audio sine wave
        subprocess.run([
            cls.ffmpeg, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-c:v", "libx264", "-c:a", "aac",
            str(cls.test_mp4)
        ], capture_output=True, check=True)

    @classmethod
    def tearDownClass(cls):
        for p in [cls.test_wav, cls.test_mp4]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass

    def test_media_types_utilities(self):
        self.assertEqual(get_media_type("cancion.mp3"), "audio")
        self.assertEqual(get_media_type("grabacion.wav"), "audio")
        self.assertEqual(get_media_type("clase.m4a"), "audio")
        self.assertEqual(get_media_type("video.mp4"), "video")
        self.assertEqual(get_media_type("pelicula.mkv"), "video")
        self.assertEqual(get_media_type("clip.mov"), "video")
        self.assertEqual(get_media_type("documento.pdf"), "pdf")
        self.assertEqual(get_media_type("pliego.png"), "image")

        self.assertTrue(is_audio_file("nota.wav"))
        self.assertTrue(is_video_file("demo.webm"))

        self.assertEqual(get_media_icon("audio"), "🎵")
        self.assertEqual(get_media_icon("video"), "🎬")
        self.assertEqual(get_media_icon("pdf"), "📄")

        self.assertEqual(format_timestamp(45.0), "00:45")
        self.assertEqual(format_timestamp(75.0), "01:15")
        self.assertEqual(format_timestamp(3665.0), "01:01:05")

        self.assertEqual(format_time_interval(15.0, 30.0), "00:15 - 00:30")
        self.assertEqual(parse_timestamp("01:15"), 75.0)

    def test_audio_processor(self):
        ap = AudioProcessor(chunk_duration=2.0)
        dur = ap.get_duration(self.test_wav)
        self.assertAlmostEqual(dur, 3.0, delta=0.5)

        res = ap.process_audio(self.test_wav)
        self.assertEqual(res["media_type"], "audio")
        self.assertGreaterEqual(len(res["chunks"]), 1)
        chunk0 = res["chunks"][0]
        self.assertIn("start_time", chunk0)
        self.assertIn("end_time", chunk0)
        self.assertIn("timestamp_label", chunk0)
        self.assertEqual(chunk0["source_type"], "audio_transcript")

    def test_video_processor(self):
        vp = VideoProcessor(frame_interval=1.5, max_frames=4)
        dur = vp.get_duration(self.test_mp4)
        self.assertAlmostEqual(dur, 3.0, delta=0.5)

        res = vp.process_video(self.test_mp4)
        self.assertEqual(res["media_type"], "video")
        self.assertGreaterEqual(len(res["audio_chunks"]), 1)
        self.assertGreaterEqual(len(res["visual_elements"]), 1)

        elem0 = res["visual_elements"][0]
        self.assertIn("timestamp_label", elem0)
        self.assertIn("image_path", elem0)
        self.assertTrue(Path(elem0["image_path"]).exists())

    def test_stats_manager_multimedia(self):
        sm = StatsManager(DATA_DIR / "test_stats.sqlite")
        sm.register_document(
            doc_name="conferencia.mp3",
            file_path=str(self.test_wav),
            total_pages=1,
            media_type="audio",
            duration=3.0,
            duration_str="00:03"
        )
        sm.add_media_segment(
            doc_name="conferencia.mp3",
            chunk_id="conf_s0",
            start_time=0.0,
            end_time=3.0,
            timestamp_label="00:00 - 00:03",
            content="Audio sintetizado de prueba",
            raw_text="Audio sintetizado de prueba",
            source_type="audio_transcript"
        )

        stats = sm.get_document_stats("conferencia.mp3")
        self.assertIsNotNone(stats)
        self.assertEqual(stats["media_type"], "audio")
        self.assertEqual(len(stats["segments"]), 1)
        self.assertEqual(stats["segments"][0]["timestamp_label"], "00:00 - 00:03")

        sheet = sm.format_stats_sheet("conferencia.mp3")
        self.assertIn("ESPÉCIMEN DE AUDIO", sheet)
        self.assertIn("00:00 - 00:03", sheet)

        # Test deletion
        sm.delete_document("conferencia.mp3")
        self.assertIsNone(sm.get_document_stats("conferencia.mp3"))

    def test_vector_store_timestamps(self):
        vs = VectorStore()
        test_chunk = {
            "chunk_id": "test_time_chunk_999",
            "doc_name": "podcast.mp3",
            "page_number": 1,
            "start_time": 10.0,
            "end_time": 25.0,
            "timestamp_label": "00:10 - 00:25",
            "content": "Discusión sobre energía fotovoltaica en sistemas solares",
            "source_type": "audio_transcript",
            "media_type": "audio"
        }
        vs.upsert_text_chunks([test_chunk])

        results = vs.search("energía fotovoltaica", doc_name="podcast.mp3", limit=1)
        self.assertGreaterEqual(len(results), 1)
        hit = results[0]
        self.assertEqual(hit["timestamp_label"], "00:10 - 00:25")
        self.assertEqual(hit["media_type"], "audio")
        self.assertEqual(hit["start_time"], 10.0)

        vs.delete_document_points("podcast.mp3")


if __name__ == "__main__":
    unittest.main()
