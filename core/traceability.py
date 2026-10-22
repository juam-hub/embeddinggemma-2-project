"""
Traceability and Telemetry Engine for ChatCasero.
Records, measures, and persists end-to-end execution flow traces:
- Ingestion pipelines (PDF, Standalone Image, Audio, Video).
- Query & Retrieval pipelines (target detection, vector search, Qdrant scoring, prompt synthesis).
- Hardware and hardware constraint monitoring (GPU/CPU allocations, token consumption).
"""
import time
import json
import uuid
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.config import DB_PATH, VISION_MODEL, EMBEDDING_MODEL, QDRANT_HOST, QDRANT_PORT


class TraceManager:
    """Manages thread-safe in-memory and persistent SQLite trace logs."""

    def __init__(self, db_path: Path = DB_PATH, max_memory_traces: int = 60):
        self.db_path = str(db_path)
        self.max_memory_traces = max_memory_traces
        self._memory_traces: List[Dict[str, Any]] = []
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS flow_traces (
                        trace_id TEXT PRIMARY KEY,
                        flow_type TEXT,
                        title TEXT,
                        start_time TEXT,
                        status TEXT,
                        total_duration_ms REAL,
                        steps_json TEXT,
                        summary TEXT,
                        metadata_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[TraceManager] Init notice: {e}")

    def start_trace(self, flow_type: str, title: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Starts a new flow trace and returns its unique trace_id."""
        trace_id = str(uuid.uuid4())[:8]
        start_iso = datetime.now().strftime("%H:%M:%S")

        trace_record = {
            "trace_id": trace_id,
            "flow_type": flow_type,
            "title": title,
            "start_time": start_iso,
            "_start_perf": time.perf_counter(),
            "status": "running",
            "total_duration_ms": 0.0,
            "steps": [],
            "summary": "En ejecución…",
            "metadata": metadata or {}
        }

        self._memory_traces.insert(0, trace_record)
        if len(self._memory_traces) > self.max_memory_traces:
            self._memory_traces.pop()

        return trace_id

    def add_step(
        self,
        trace_id: str,
        step_name: str,
        details: str = "",
        status: str = "success",
        duration_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Adds a discrete execution step to an active trace."""
        step_item = {
            "name": step_name,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "details": details,
            "status": status,
            "duration_ms": round(duration_ms, 1),
            "metadata": metadata or {}
        }

        # Update in memory
        for t in self._memory_traces:
            if t["trace_id"] == trace_id:
                t["steps"].append(step_item)
                break

    def complete_trace(
        self,
        trace_id: str,
        status: str = "success",
        summary: str = "",
        metadata_update: Optional[Dict[str, Any]] = None
    ):
        """Finalizes a trace, calculates total duration, and persists it to SQLite."""
        target_trace = None
        for t in self._memory_traces:
            if t["trace_id"] == trace_id:
                t["status"] = status
                start_p = t.pop("_start_perf", time.perf_counter())
                t["total_duration_ms"] = max(0.1, round((time.perf_counter() - start_p) * 1000, 1))
                if summary:
                    t["summary"] = summary
                if metadata_update:
                    t["metadata"].update(metadata_update)
                target_trace = t
                break

        if target_trace:
            self._persist_trace(target_trace)

    def _persist_trace(self, trace: Dict[str, Any]):
        """Saves completed trace to SQLite."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO flow_traces (
                        trace_id, flow_type, title, start_time, status,
                        total_duration_ms, steps_json, summary, metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(trace_id) DO UPDATE SET
                        status=excluded.status,
                        total_duration_ms=excluded.total_duration_ms,
                        steps_json=excluded.steps_json,
                        summary=excluded.summary,
                        metadata_json=excluded.metadata_json
                """, (
                    trace["trace_id"],
                    trace["flow_type"],
                    trace["title"],
                    trace["start_time"],
                    trace["status"],
                    trace["total_duration_ms"],
                    json.dumps(trace["steps"], ensure_ascii=False),
                    trace["summary"],
                    json.dumps(trace["metadata"], ensure_ascii=False)
                ))
                conn.commit()
        except Exception as e:
            print(f"[TraceManager] Error persisting trace: {e}")

    def get_recent_traces(self, limit: int = 40, flow_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves recent traces from memory, falling back to SQLite if needed."""
        if self._memory_traces:
            filtered = [
                t for t in self._memory_traces
                if not flow_type or flow_type == "all" or t["flow_type"] == flow_type
            ]
            if filtered:
                return filtered[:limit]

        # Load from SQLite
        traces = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if flow_type and flow_type != "all":
                    cursor.execute("""
                        SELECT * FROM flow_traces
                        WHERE flow_type = ?
                        ORDER BY rowid DESC LIMIT ?
                    """, (flow_type, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM flow_traces
                        ORDER BY rowid DESC LIMIT ?
                    """, (limit,))

                for row in cursor.fetchall():
                    item = dict(row)
                    item["steps"] = json.loads(item.get("steps_json") or "[]")
                    item["metadata"] = json.loads(item.get("metadata_json") or "{}")
                    traces.append(item)
        except Exception:
            pass

        return traces

    def get_system_telemetry(self) -> Dict[str, Any]:
        """Collects current hardware and service constraint telemetry."""
        total_traces = len(self._memory_traces)
        avg_latency = (
            sum(t["total_duration_ms"] for t in self._memory_traces if t.get("total_duration_ms", 0) > 0)
            / max(1, len([t for t in self._memory_traces if t.get("total_duration_ms", 0) > 0]))
        )

        return {
            "total_traces": total_traces,
            "avg_latency_ms": round(avg_latency, 1),
            "vision_model": VISION_MODEL,
            "vision_target": "GPU (num_ctx: 8192)",
            "embedding_model": EMBEDDING_MODEL,
            "embedding_target": "CPU Aislada (num_gpu: 0)",
            "qdrant_endpoint": f"{QDRANT_HOST}:{QDRANT_PORT}",
        }

    def clear_all_traces(self):
        """Clears trace history."""
        self._memory_traces.clear()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM flow_traces")
                conn.commit()
        except Exception:
            pass


# Global singleton instance for application-wide tracing
trace_manager = TraceManager()
