"""
Unit and integration tests for Traceability and Telemetry Engine.
Verifies trace creation, step logging, latency metrics, and SQLite persistence.
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from core.traceability import TraceManager


class TestTraceability(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test_traces.sqlite"
        self.mgr = TraceManager(db_path=self.db_path, max_memory_traces=20)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_trace_lifecycle(self):
        trace_id = self.mgr.start_trace(
            flow_type="query",
            title="Test RAG Query",
            metadata={"user_query": "¿Qué dice el pliego?", "top_k": 3}
        )
        self.assertIsNotNone(trace_id)
        self.assertEqual(len(trace_id), 8)

        self.mgr.add_step(
            trace_id=trace_id,
            step_name="Identificación de Pliegos",
            details="1 pliego detectado",
            duration_ms=12.5,
            metadata={"docs": ["test.pdf"]}
        )

        self.mgr.add_step(
            trace_id=trace_id,
            step_name="Recuperación Vectorial",
            details="3 fragmentos recuperados",
            duration_ms=45.2
        )

        self.mgr.complete_trace(
            trace_id=trace_id,
            status="success",
            summary="Consulta completada con éxito en 57.7ms"
        )

        traces = self.mgr.get_recent_traces(limit=10)
        self.assertEqual(len(traces), 1)
        t = traces[0]
        self.assertEqual(t["trace_id"], trace_id)
        self.assertEqual(t["flow_type"], "query")
        self.assertEqual(t["status"], "success")
        self.assertGreater(t["total_duration_ms"], 0)
        self.assertEqual(len(t["steps"]), 2)
        self.assertEqual(t["steps"][0]["name"], "Identificación de Pliegos")
        self.assertEqual(t["steps"][0]["duration_ms"], 12.5)
        self.assertEqual(t["steps"][1]["name"], "Recuperación Vectorial")

    def test_trace_filtering_and_telemetry(self):
        # Add an ingestion trace
        t1 = self.mgr.start_trace("ingestion_video", "Ingesta Video 1")
        self.mgr.add_step(t1, "Muestreo de fotogramas", duration_ms=100.0)
        self.mgr.complete_trace(t1, "success", "Video procesado")

        # Add a query trace
        t2 = self.mgr.start_trace("query", "Consulta 1")
        self.mgr.add_step(t2, "Búsqueda Qdrant", duration_ms=20.0)
        self.mgr.complete_trace(t2, "success", "Query OK")

        # Test filtering
        all_traces = self.mgr.get_recent_traces(limit=10, flow_type="all")
        self.assertEqual(len(all_traces), 2)

        query_traces = self.mgr.get_recent_traces(limit=10, flow_type="query")
        self.assertEqual(len(query_traces), 1)
        self.assertEqual(query_traces[0]["trace_id"], t2)

        video_traces = self.mgr.get_recent_traces(limit=10, flow_type="ingestion_video")
        self.assertEqual(len(video_traces), 1)
        self.assertEqual(video_traces[0]["trace_id"], t1)

        # Test telemetry
        telemetry = self.mgr.get_system_telemetry()
        self.assertEqual(telemetry["total_traces"], 2)
        self.assertGreaterEqual(telemetry["avg_latency_ms"], 0)
        self.assertIn("qwen2.5vl:7b", telemetry["vision_model"])
        self.assertIn("embeddinggemma-2", telemetry["embedding_model"])

    def test_sqlite_persistence(self):
        t_id = self.mgr.start_trace("deletion", "Purga de documento")
        self.mgr.add_step(t_id, "Borrado de vectores", details="Completado", duration_ms=15.0)
        self.mgr.complete_trace(t_id, "success", "Purga total")

        # Clear memory traces to force reading from SQLite database
        self.mgr._memory_traces.clear()

        traces_from_db = self.mgr.get_recent_traces(limit=10)
        self.assertEqual(len(traces_from_db), 1)
        self.assertEqual(traces_from_db[0]["trace_id"], t_id)
        self.assertEqual(traces_from_db[0]["flow_type"], "deletion")
        self.assertEqual(len(traces_from_db[0]["steps"]), 1)
        self.assertEqual(traces_from_db[0]["steps"][0]["name"], "Borrado de vectores")


if __name__ == "__main__":
    unittest.main()
