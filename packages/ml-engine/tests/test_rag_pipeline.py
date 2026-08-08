import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from training.rag_pipeline import (
    Document,
    DocumentChunk,
    DocumentProcessor,
    EmbeddingService,
    RAGConfig,
    RAGPipeline,
    TextChunker,
    VectorStore,
)


class TestDocumentChunk:
    def test_creation(self):
        chunk = DocumentChunk(
            chunk_id="c1",
            document_id="d1",
            content="hello",
            metadata={"k": "v"},
        )
        assert chunk.chunk_id == "c1"
        assert chunk.document_id == "d1"
        assert chunk.content == "hello"
        assert chunk.chunk_index == 0

    def test_defaults(self):
        chunk = DocumentChunk(chunk_id="c", document_id="d", content="", metadata={})
        assert chunk.embedding is None
        assert chunk.start_char == 0
        assert chunk.end_char == 0
        assert chunk.token_count == 0


class TestDocument:
    def test_creation(self):
        doc = Document(
            document_id="d1",
            filename="test.txt",
            content_type="text/plain",
            file_size=100,
            status="processing",
        )
        assert doc.document_id == "d1"
        assert doc.chunk_count == 0
        assert doc.indexed_at is None

    def test_to_dict_roundtrip(self):
        doc = Document(
            document_id="d1",
            filename="test.txt",
            content_type="text/plain",
            file_size=100,
            status="indexed",
            chunk_count=5,
        )
        d = doc.to_dict()
        restored = Document.from_dict(d)
        assert restored.document_id == "d1"
        assert restored.chunk_count == 5
        assert restored.status == "indexed"


class TestRAGConfig:
    def test_defaults(self):
        config = RAGConfig()
        assert config.embedding_model == "BAAI/bge-large-en-v1.5"
        assert config.qdrant_url == "http://localhost:6333"
        assert config.chunk_size == 512
        assert config.chunk_overlap == 64
        assert config.min_score == 0.3
        assert config.use_hybrid_search is True

    def test_custom(self):
        config = RAGConfig(chunk_size=256, chunk_overlap=32, min_score=0.5)
        assert config.chunk_size == 256
        assert config.min_score == 0.5

    def test_storage_path_from_env(self, monkeypatch):
        monkeypatch.setenv("RAG_STORAGE_PATH", "/data/rag")
        config = RAGConfig()
        assert config.storage_path == "/data/rag"
        monkeypatch.delenv("RAG_STORAGE_PATH")
        assert RAGConfig().storage_path == "./rag_storage"

    def test_qdrant_url_from_env(self, monkeypatch):
        monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
        assert RAGConfig().qdrant_url == "http://qdrant:6333"
        monkeypatch.delenv("QDRANT_URL")


class TestTextChunker:
    def test_chunk_text(self):
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "This is sentence one. " * 30
        chunks = chunker.chunk_text(text, {"document_id": "test"})
        assert len(chunks) > 0
        assert all(c.content.strip() for c in chunks)
        assert all(c.document_id == "test" for c in chunks)

    def test_chunk_overlap(self):
        chunker = TextChunker(chunk_size=20, chunk_overlap=5)
        text = "Alpha bravo charlie delta echo foxtrot golf hotel india juliet. " * 10
        chunks = chunker.chunk_text(text)
        assert len(chunks) >= 2

    def test_empty_text(self):
        chunker = TextChunker()
        chunks = chunker.chunk_text("")
        assert chunks == []

    def test_short_text_single_chunk(self):
        chunker = TextChunker(chunk_size=1000)
        chunks = chunker.chunk_text("Short text.")
        assert len(chunks) == 1
        assert chunks[0].content == "Short text."

    def test_chunk_indices(self):
        chunker = TextChunker(chunk_size=30, chunk_overlap=5)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        chunks = chunker.chunk_text(text)
        for i, c in enumerate(chunks):
            assert c.chunk_index == i

    def test_chunk_markdown(self):
        chunker = TextChunker(chunk_size=100)
        md = "# Title\n\nSome content here.\n\n## Section\n\nMore content."
        chunks = chunker.chunk_markdown(md)
        assert len(chunks) >= 1

    def test_estimate_tokens(self):
        chunker = TextChunker()
        assert chunker._estimate_tokens("1234") == 1
        assert chunker._estimate_tokens("12345678") == 2


class TestDocumentProcessor:
    def test_process_txt(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world test content")
        processor = DocumentProcessor()
        text = processor.process(str(f), "text/plain")
        assert "Hello world" in text

    def test_process_csv(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("name,age\nAlice,30\nBob,25")
        processor = DocumentProcessor()
        text = processor.process(str(f), "text/csv")
        assert "Alice" in text
        assert "Bob" in text

    def test_process_markdown(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Title\nContent here")
        processor = DocumentProcessor()
        text = processor.process(str(f), "text/markdown")
        assert "# Title" in text

    def test_process_unsupported_type_fallback(self, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_text("fallback content")
        processor = DocumentProcessor()
        text = processor.process(str(f), "application/unknown")
        assert "fallback content" in text

    def test_supported_types(self):
        processor = DocumentProcessor()
        types = processor.get_supported_types()
        assert "text/plain" in types
        assert "text/csv" in types
        assert "application/pdf" in types

    def test_image_types_registered_for_ocr(self):
        processor = DocumentProcessor()
        for t in ("image/png", "png", "image/jpeg", "jpg", "image/webp", "image/tiff"):
            assert t in processor._type_map
        assert processor._type_map["image/png"] == processor.process_image
        assert processor._type_map["jpg"] == processor.process_image

    def test_process_image_without_ocr_deps_raises(self, tmp_path):
        f = tmp_path / "scan.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        processor = DocumentProcessor()
        with patch("training.rag_pipeline.pytesseract", None, create=True), \
             patch("builtins.__import__", side_effect=ImportError("no OCR libs")):
            with pytest.raises(RuntimeError) as exc_info:
                processor.process(str(f), "image/png")
            assert "pytesseract" in str(exc_info.value)

    def test_process_image_text_fallback(self, tmp_path, monkeypatch):
        # A text file mislabeled as an image should still be readable via the
        # txt fallback when OCR fails at runtime (image open / OCR error).
        import sys

        f = tmp_path / "notes.png"
        f.write_text("plain text inside a fake image")
        processor = DocumentProcessor()

        # Simulate an OCR runtime failure (not an import failure) so the
        # fallback path is exercised.
        class _FakeImage:
            @classmethod
            def open(cls, *args, **kwargs):
                raise Exception("not a real image")

        class _FakeTesseract:
            @staticmethod
            def image_to_string(*args, **kwargs):
                return ""

        monkeypatch.setitem(sys.modules, "pytesseract", _FakeTesseract)
        monkeypatch.setitem(sys.modules, "PIL", type("PIL", (), {"Image": _FakeImage}))
        text = processor.process(str(f), "image/png")
        assert "plain text" in text


class TestEmbeddingService:
    def test_init(self):
        service = EmbeddingService()
        assert service._dimension == 0
        assert service._model is None

    def test_load_model_fallback(self):
        with patch("training.rag_pipeline.ST_AVAILABLE", False):
            service = EmbeddingService()
            service._load_model()
            assert service._dimension > 0

    def test_embed_texts(self):
        with patch("training.rag_pipeline.ST_AVAILABLE", False):
            service = EmbeddingService()
            embeddings = service.embed_texts(["hello", "world"], batch_size=2)
            assert len(embeddings) == 2
            assert len(embeddings[0]) == service._dimension

    def test_embed_query(self):
        with patch("training.rag_pipeline.ST_AVAILABLE", False):
            service = EmbeddingService()
            emb = service.embed_query("test query")
            assert isinstance(emb, list)
            assert len(emb) == service._dimension

    def test_get_dimension(self):
        with patch("training.rag_pipeline.ST_AVAILABLE", False):
            service = EmbeddingService()
            dim = service.get_dimension()
            assert dim > 0

    def test_compute_similarity_identical(self):
        vec = [1.0, 0.0, 0.0]
        sim = EmbeddingService.compute_similarity(vec, vec)
        assert abs(sim - 1.0) < 1e-6

    def test_compute_similarity_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        sim = EmbeddingService.compute_similarity(a, b)
        assert abs(sim) < 1e-6

    def test_compute_similarity_zero_vector(self):
        sim = EmbeddingService.compute_similarity([0, 0], [1, 1])
        assert sim == 0.0


class TestVectorStore:
    def test_init_memory_fallback(self, tmp_path):
        config = RAGConfig(qdrant_url="http://nonexistent:6333", storage_path=str(tmp_path / "rag"))
        store = VectorStore(config)
        store._ensure_collection()
        assert store._client is None

    def test_upsert_and_search(self, tmp_path):
        config = RAGConfig(qdrant_url="http://nonexistent:6333", min_score=0.0, storage_path=str(tmp_path / "rag"))
        store = VectorStore(config)
        import random
        random.seed(42)
        chunks = [
            DocumentChunk(
                chunk_id=f"c{i}",
                document_id="d1",
                content=f"chunk {i} content",
                metadata={},
                embedding=[random.random() for _ in range(10)],
            )
            for i in range(5)
        ]
        count = store.upsert_chunks(chunks)
        assert count == 5

        query_emb = chunks[0].embedding[:]
        results = store.search(query_emb, top_k=3)
        assert len(results) >= 1
        assert results[0]["chunk_id"] == "c0"

    def test_delete_document(self, tmp_path):
        config = RAGConfig(qdrant_url="http://nonexistent:6333", min_score=0.0, storage_path=str(tmp_path / "rag"))
        store = VectorStore(config)
        import random
        random.seed(1)
        chunks = [
            DocumentChunk(
                chunk_id=f"c{i}",
                document_id="del_doc",
                content=f"text {i}",
                metadata={},
                embedding=[random.random() for _ in range(10)],
            )
            for i in range(3)
        ]
        store.upsert_chunks(chunks)
        deleted = store.delete_document("del_doc")
        assert deleted == 3

    def test_count_chunks(self, tmp_path):
        config = RAGConfig(qdrant_url="http://nonexistent:6333", storage_path=str(tmp_path / "rag"))
        store = VectorStore(config)
        assert store.count_chunks() == 0

    def test_get_collection_stats(self, tmp_path):
        config = RAGConfig(qdrant_url="http://nonexistent:6333", storage_path=str(tmp_path / "rag"))
        store = VectorStore(config)
        stats = store.get_collection_stats()
        assert stats["backend"] == "in-memory"
        assert stats["points_count"] == 0

    def test_hybrid_search(self, tmp_path):
        config = RAGConfig(qdrant_url="http://nonexistent:6333", min_score=0.0, storage_path=str(tmp_path / "rag"))
        store = VectorStore(config)
        import random
        random.seed(7)
        chunks = [
            DocumentChunk(
                chunk_id="c1",
                document_id="d1",
                content="machine learning is great",
                metadata={},
                embedding=[random.random() for _ in range(10)],
            ),
            DocumentChunk(
                chunk_id="c2",
                document_id="d2",
                content="cooking recipes for dinner",
                metadata={},
                embedding=[random.random() for _ in range(10)],
            ),
        ]
        store.upsert_chunks(chunks)
        results = store.hybrid_search("machine learning", chunks[0].embedding, top_k=2)
        assert len(results) >= 1


class TestRAGPipeline:
    @pytest.fixture
    def pipeline(self, tmp_path):
        config = RAGConfig(
            storage_path=str(tmp_path / "rag"),
            qdrant_url="http://nonexistent:6333",
            min_score=0.0,
        )
        with patch("training.rag_pipeline.ST_AVAILABLE", False):
            yield RAGPipeline(config)

    def test_ingest_text(self, pipeline):
        doc = pipeline.ingest_text("This is test content about machine learning", "test")
        assert doc.document_id
        assert doc.status == "indexed"
        assert doc.chunk_count >= 1
        assert doc.total_tokens >= 1

    def test_ingest_text_dedup(self, pipeline):
        d1 = pipeline.ingest_text("Unique text here", "s1")
        d2 = pipeline.ingest_text("Unique text here", "s2")
        assert d1.document_id == d2.document_id

    def test_search(self, pipeline):
        pipeline.ingest_text("Machine learning is a subset of AI that learns from data", "ml-doc")
        results = pipeline.search("What is machine learning?")
        assert isinstance(results, list)

    def test_build_context(self, pipeline):
        pipeline.ingest_text("The sky is blue and the grass is green", "color-doc")
        context = pipeline.build_context("What color is the sky?")
        assert isinstance(context, str)

    def test_build_context_empty(self, pipeline):
        context = pipeline.build_context("nonexistent topic xyz")
        assert "No relevant context found" in context

    def test_build_prompt(self, pipeline):
        prompt = pipeline.build_prompt("Hello", "Context about AI", "You are helpful")
        assert "Hello" in prompt
        assert "Context about AI" in prompt
        assert "You are helpful" in prompt

    def test_build_prompt_default_system(self, pipeline):
        prompt = pipeline.build_prompt("Q", "C")
        assert "helpful assistant" in prompt

    def test_delete_document(self, pipeline):
        doc = pipeline.ingest_text("Test content for deletion", "test-del")
        result = pipeline.delete_document(doc.document_id)
        assert result is True
        assert pipeline.get_document(doc.document_id) is None

    def test_delete_nonexistent(self, pipeline):
        result = pipeline.delete_document("nonexistent-id")
        assert result is False

    def test_list_documents(self, pipeline):
        pipeline.ingest_text("Doc 1 content", "d1")
        pipeline.ingest_text("Doc 2 content", "d2")
        docs, total = pipeline.list_documents()
        assert total == 2

    def test_list_documents_pagination(self, pipeline):
        for i in range(5):
            pipeline.ingest_text(f"Document {i} with unique content here", f"doc_{i}")
        docs, total = pipeline.list_documents(page=1, page_size=2)
        assert total == 5
        assert len(docs) == 2

    def test_stats(self, pipeline):
        pipeline.ingest_text("Some content for stats", "stats-doc")
        stats = pipeline.get_stats()
        assert "total_documents" in stats
        assert "indexed_documents" in stats
        assert "total_chunks" in stats
        assert "total_tokens" in stats
        assert "embedding_model" in stats
        assert stats["total_documents"] == 1

    def test_get_document(self, pipeline):
        doc = pipeline.ingest_text("Retrieve me", "get-doc")
        found = pipeline.get_document(doc.document_id)
        assert found is not None
        assert found.filename == "get-doc"

    def test_get_document_not_found(self, pipeline):
        assert pipeline.get_document("nope") is None

    def test_ingest_file(self, tmp_path, pipeline):
        f = tmp_path / "test.txt"
        f.write_text("File content for ingestion test")
        doc = pipeline.ingest_document(str(f), "test.txt", "text/plain")
        assert doc.status == "indexed"

    def test_ingest_file_dedup_by_hash(self, tmp_path, pipeline):
        f = tmp_path / "dup.txt"
        f.write_text("Duplicate content")
        d1 = pipeline.ingest_document(str(f), "dup.txt", "text/plain")
        d2 = pipeline.ingest_document(str(f), "dup_copy.txt", "text/plain")
        assert d1.document_id == d2.document_id

    def test_process_document_text(self, pipeline):
        doc = pipeline.process_document(
            document_id="celery-doc-1",
            filename="inline.txt",
            file_type="txt",
            text="Asynchronous document processing with real chunking and embedding work",
        )
        assert doc.document_id == "celery-doc-1"
        assert doc.status == "indexed"
        assert doc.chunk_count >= 1
        assert pipeline.get_document("celery-doc-1") is not None

    def test_process_document_file(self, tmp_path, pipeline):
        f = tmp_path / "celery.txt"
        f.write_text("File-based document processing test content")
        doc = pipeline.process_document(
            document_id="celery-doc-2",
            filename="celery.txt",
            file_type="txt",
            storage_path=str(f),
        )
        assert doc.status == "indexed"
        assert doc.chunk_count >= 1

    def test_process_document_missing_path_raises(self, pipeline):
        with pytest.raises(FileNotFoundError):
            pipeline.process_document(
                document_id="celery-doc-3",
                filename="missing.pdf",
                file_type="pdf",
                storage_path="/nonexistent/file.pdf",
            )

    def test_process_document_replaces_prior(self, pipeline):
        d1 = pipeline.process_document(
            document_id="celery-doc-4",
            filename="v1.txt",
            file_type="txt",
            text="First version content here",
        )
        assert d1.status == "indexed"
        d2 = pipeline.process_document(
            document_id="celery-doc-4",
            filename="v2.txt",
            file_type="txt",
            text="Second version content here",
        )
        assert d2.document_id == "celery-doc-4"
        assert d2.status == "indexed"

    def test_regenerate_embeddings(self, pipeline):
        doc = pipeline.ingest_text("Regenerate my embeddings please", "regen")
        count = pipeline.regenerate_embeddings(doc.document_id)
        assert count == doc.chunk_count
        assert count >= 1

    def test_regenerate_embeddings_unknown_doc(self, pipeline):
        assert pipeline.regenerate_embeddings("nope-id") == 0

    def test_ocr_process(self, tmp_path, pipeline):
        f = tmp_path / "scanned.txt"
        f.write_text("OCR extracted content")
        doc = pipeline.ocr_process(
            document_id="ocr-doc-1",
            storage_path=str(f),
            file_type="txt",
        )
        assert doc.status == "indexed"
        assert doc.chunk_count >= 1

    def test_ocr_process_missing_file_raises(self, pipeline):
        with pytest.raises(FileNotFoundError):
            pipeline.ocr_process(
                document_id="ocr-doc-2",
                storage_path="/nonexistent/scanned.pdf",
                file_type="pdf",
            )

    def test_upsert_vector_and_delete(self, pipeline):
        pipeline.upsert_vector(
            collection="memory",
            point_id="mem-1",
            vector=[0.1, 0.2, 0.3],
            payload={"user_id": "u1"},
        )
        deleted = pipeline.delete_vectors("memory", {"user_id": "u1"})
        assert deleted == 1

    def test_upsert_vector_no_match_delete(self, pipeline):
        pipeline.upsert_vector("memory", "mem-2", [0.5, 0.5], {})
        deleted = pipeline.delete_vectors("memory", {"user_id": "nobody"})
        assert deleted == 0
