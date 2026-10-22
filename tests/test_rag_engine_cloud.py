import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from core.rag_engine import RAGEngine
from core.traceability import TraceManager


class TestRAGEngineCloudSwitch(unittest.TestCase):
    def setUp(self):
        self.mock_vector_store = MagicMock()
        self.mock_vector_store.search.return_value = [
            {
                "doc_name": "manual.pdf",
                "page_number": 2,
                "content": "Este es un fragmento de prueba sobre energía solar.",
                "source_type": "text",
                "media_type": "pdf",
                "element_id": "txt_1",
            }
        ]
        self.mock_stats_manager = MagicMock()
        self.mock_stats_manager.get_document_stats.return_value = {}
        self.mock_stats_manager.format_stats_sheet.return_value = "FICHA TÉCNICA:\nTotal: 1 doc"

        self.mock_trace_manager = MagicMock(spec=TraceManager)
        self.mock_trace_manager.start_trace.return_value = "tr_123"

        self.rag = RAGEngine(
            vector_store=self.mock_vector_store,
            stats_manager=self.mock_stats_manager,
            trace_manager=self.mock_trace_manager,
        )

    def test_query_cloud_missing_api_key(self):
        stream_gen, citations = self.rag.query(
            doc_names=["manual.pdf"],
            user_query="¿De qué trata?",
            llm_mode="cloud",
            cloud_config={"provider": "groq", "api_key": ""},
        )
        chunks = list(stream_gen)
        full_text = "".join(chunks)
        self.assertIn("Modo Nube activado", full_text)
        self.assertIn("API Key", full_text)
        self.assertEqual(len(citations), 1)

    @patch("core.rag_engine.stream_cloud_chat")
    def test_query_cloud_with_api_key(self, mock_stream):
        mock_stream.return_value = iter(["Respuesta ", "desde ", "la nube."])

        stream_gen, citations = self.rag.query(
            doc_names=["manual.pdf"],
            user_query="¿De qué trata?",
            llm_mode="cloud",
            cloud_config={"provider": "groq", "api_key": "gsk_test_key", "model": "llama-3.3-70b-versatile"},
        )
        chunks = list(stream_gen)
        self.assertEqual(chunks, ["Respuesta ", "desde ", "la nube."])
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["doc_name"], "manual.pdf")
        self.mock_trace_manager.complete_trace.assert_called()

    def test_query_local_mode(self):
        mock_chunk = MagicMock()
        mock_chunk.message.content = "Respuesta local."
        self.rag.ollama_client = MagicMock()
        self.rag.ollama_client.chat.return_value = [mock_chunk]

        stream_gen, citations = self.rag.query(
            doc_names=["manual.pdf"],
            user_query="¿De qué trata?",
            llm_mode="local",
        )
        chunks = list(stream_gen)
        self.assertEqual(chunks, ["Respuesta local."])
        self.assertEqual(len(citations), 1)


if __name__ == "__main__":
    unittest.main()
