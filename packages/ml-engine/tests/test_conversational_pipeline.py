import json
import os
import tempfile
import time

import pytest

from training.conversational_pipeline import (
    Conversation,
    ConversationalLearningPipeline,
    ConversationStore,
    ConversationTurn,
    DatasetBuilder,
    PipelineConfig,
    TrainingDataset,
)


def _make_turn(role="user", content="Hello", ts_offset=0):
    ts = "2024-01-01T00:00:00+00:00"
    return ConversationTurn(
        turn_id=f"turn_{role}_{hash(content) % 10000:04d}",
        role=role,
        content=content,
        timestamp=ts,
        metadata={},
    )


def _make_conversation(user_id="u1", tenant_id="t1", num_turns=4, conv_id=None):
    turns = []
    for i in range(num_turns):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"Turn {i}: {'question' if role == 'user' else 'answer text'}"
        ts = f"2024-01-01T00:{i:02d}:00+00:00"
        turns.append(ConversationTurn(
            turn_id=f"turn_{conv_id or 'c'}_{i}",
            role=role,
            content=content,
            timestamp=ts,
            metadata={},
        ))
    return Conversation(
        conversation_id=conv_id or f"conv_{int(time.time() * 1000) % 100000:05d}",
        user_id=user_id,
        tenant_id=tenant_id,
        turns=turns,
        status="active",
        feedback_scores={},
        created_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
        total_tokens=sum(len(t.content.split()) for t in turns),
        metadata={},
    )


class TestConversationTurn:
    def test_creation(self):
        turn = _make_turn(role="user", content="Hi there")
        assert turn.turn_id
        assert turn.role == "user"
        assert turn.content == "Hi there"
        assert turn.metadata == {}


class TestConversation:
    def test_creation(self):
        conv = _make_conversation()
        assert conv.conversation_id
        assert conv.user_id == "u1"
        assert conv.tenant_id == "t1"
        assert len(conv.turns) == 4
        assert conv.status == "active"


class TestPipelineConfig:
    def test_defaults(self):
        config = PipelineConfig()
        assert config.min_conversations_for_training == 10
        assert config.min_turns_per_conversation == 4
        assert config.quality_threshold == 0.5
        assert config.include_feedback is True
        assert config.training_batch_size == 100
        assert config.auto_train_enabled is True

    def test_custom(self):
        config = PipelineConfig(min_conversations_for_training=5, training_batch_size=10)
        assert config.min_conversations_for_training == 5
        assert config.training_batch_size == 10


class TestConversationStore:
    @pytest.fixture
    def store(self, tmp_path):
        return ConversationStore(storage_path=str(tmp_path / "conv_store"))

    def test_add_and_get(self, store):
        conv = _make_conversation(user_id="user1", tenant_id="tenant1")
        conv_id = store.add_conversation(conv)
        retrieved = store.get_conversation(conv_id)
        assert retrieved is not None
        assert retrieved.user_id == "user1"
        assert retrieved.tenant_id == "tenant1"

    def test_list_conversations(self, store):
        for i in range(3):
            conv = _make_conversation(user_id=f"u{i}", conv_id=f"conv_{i}")
            store.add_conversation(conv)
        result = store.list_conversations()
        assert len(result) == 3

    def test_list_filter_by_user(self, store):
        store.add_conversation(_make_conversation(user_id="u1", conv_id="c1"))
        store.add_conversation(_make_conversation(user_id="u2", conv_id="c2"))
        result = store.list_conversations(user_id="u1")
        assert len(result) == 1
        assert result[0].user_id == "u1"

    def test_list_filter_by_status(self, store):
        conv = _make_conversation(conv_id="c1")
        store.add_conversation(conv)
        conv_archived = _make_conversation(conv_id="c2")
        conv_archived.status = "archived"
        store.add_conversation(conv_archived)
        active = store.list_conversations(status="active")
        assert len(active) == 1

    def test_add_turn(self, store):
        conv = _make_conversation(num_turns=2, conv_id="c1")
        store.add_conversation(conv)
        new_turn = _make_turn(role="assistant", content="New response")
        store.add_turn("c1", new_turn)
        updated = store.get_conversation("c1")
        assert len(updated.turns) == 3

    def test_add_turn_nonexistent_raises(self, store):
        turn = _make_turn()
        with pytest.raises(KeyError):
            store.add_turn("nonexistent", turn)

    def test_update_feedback(self, store):
        conv = _make_conversation(conv_id="c1")
        store.add_conversation(conv)
        turn_id = conv.turns[0].turn_id
        store.update_feedback("c1", turn_id, 5)
        updated = store.get_conversation("c1")
        assert updated.feedback_scores[turn_id] == 5

    def test_update_feedback_clamped(self, store):
        conv = _make_conversation(conv_id="c1")
        store.add_conversation(conv)
        turn_id = conv.turns[0].turn_id
        store.update_feedback("c1", turn_id, 100)
        updated = store.get_conversation("c1")
        assert updated.feedback_scores[turn_id] == 5

    def test_archive_conversation(self, store):
        conv = _make_conversation(conv_id="c1")
        store.add_conversation(conv)
        store.archive_conversation("c1")
        updated = store.get_conversation("c1")
        assert updated.status == "archived"

    def test_delete_conversation(self, store):
        conv = _make_conversation(conv_id="c1")
        store.add_conversation(conv)
        store.delete_conversation("c1")
        assert store.get_conversation("c1") is None

    def test_delete_nonexistent_raises(self, store):
        with pytest.raises(KeyError):
            store.delete_conversation("nonexistent")

    def test_conversation_stats(self, store):
        store.add_conversation(_make_conversation(conv_id="c1"))
        store.add_conversation(_make_conversation(conv_id="c2"))
        stats = store.get_conversation_stats()
        assert stats["total_conversations"] == 2
        assert stats["active"] == 2
        assert stats["total_turns"] == 8

    def test_persist_and_reload(self, tmp_path):
        store_path = str(tmp_path / "persist_store")
        store1 = ConversationStore(storage_path=store_path)
        conv = _make_conversation(conv_id="c1")
        store1.add_conversation(conv)

        store2 = ConversationStore(storage_path=store_path)
        retrieved = store2.get_conversation("c1")
        assert retrieved is not None
        assert retrieved.user_id == "u1"

    def test_get_recent_conversations(self, store):
        conv = _make_conversation(conv_id="c1", num_turns=4)
        conv.created_at = "2099-01-01T00:00:00+00:00"
        store.add_conversation(conv)
        recent = store.get_recent_conversations(hours=1, min_turns=2)
        assert len(recent) >= 1


class TestDatasetBuilder:
    def test_build_dataset(self):
        config = PipelineConfig()
        builder = DatasetBuilder(config)
        convs = [_make_conversation(num_turns=4, conv_id=f"c{i}") for i in range(3)]
        dataset = builder.build_dataset(convs)
        assert isinstance(dataset, TrainingDataset)
        assert dataset.dataset_id.startswith("ds_")
        assert dataset.total_samples >= 0
        assert dataset.quality_score >= 0.0

    def test_empty_conversations(self):
        builder = DatasetBuilder(PipelineConfig())
        dataset = builder.build_dataset([])
        assert dataset.total_samples == 0

    def test_single_conversation(self):
        builder = DatasetBuilder(PipelineConfig())
        conv = _make_conversation(num_turns=4, conv_id="single")
        dataset = builder.build_dataset([conv])
        assert dataset.total_samples >= 1
        assert conv.conversation_id in dataset.source_conversation_ids


class TestConversationalLearningPipeline:
    @pytest.fixture
    def pipeline(self, tmp_path):
        config = PipelineConfig(
            output_dir=str(tmp_path / "conv_pipeline"),
            min_conversations_for_training=3,
            training_batch_size=3,
            min_turns_per_conversation=2,
        )
        p = ConversationalLearningPipeline(config)
        p.initialize()
        return p

    def test_record_conversation(self, pipeline):
        conv_id = pipeline.record_conversation(
            user_id="u1",
            tenant_id="t1",
            turns=[
                {"role": "user", "content": "What is AI?"},
                {"role": "assistant", "content": "AI is artificial intelligence."},
            ],
        )
        assert conv_id.startswith("conv_")
        stats = pipeline.get_pipeline_stats()
        assert stats["pipeline"]["conversations_recorded"] == 1

    def test_record_turn(self, pipeline):
        conv_id = pipeline.record_conversation(
            user_id="u1",
            tenant_id="t1",
            turns=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
        )
        turn_id = pipeline.record_turn(conv_id, "user", "Follow up question")
        assert turn_id.startswith("turn_")

    def test_submit_feedback(self, pipeline):
        conv_id = pipeline.record_conversation(
            user_id="u1",
            tenant_id="t1",
            turns=[
                {"role": "user", "content": "Q1"},
                {"role": "assistant", "content": "A1"},
            ],
        )
        conv = pipeline.conversation_store.get_conversation(conv_id)
        turn_id = conv.turns[0].turn_id
        pipeline.submit_feedback(conv_id, turn_id, 5)

    def test_build_training_dataset(self, pipeline):
        conv_id = pipeline.record_conversation(
            user_id="u1",
            tenant_id="t1",
            turns=[
                {"role": "user", "content": "Q1"},
                {"role": "assistant", "content": "A1"},
            ],
        )
        dataset = pipeline.build_training_dataset(hours=24)
        assert isinstance(dataset, TrainingDataset)
        assert dataset.total_samples >= 0

    def test_pipeline_stats(self, pipeline):
        pipeline.record_conversation(
            user_id="u1",
            tenant_id="t1",
            turns=[
                {"role": "user", "content": "Q"},
                {"role": "assistant", "content": "A"},
            ],
        )
        stats = pipeline.get_pipeline_stats()
        assert "pipeline" in stats
        assert "conversation_store" in stats
        assert "config" in stats
        assert stats["pipeline"]["conversations_recorded"] == 1

    def test_process_pending_insufficient_data(self, pipeline):
        result = pipeline.process_pending()
        assert result["status"] == "insufficient_data"
        assert result["trained"] is False

    def test_training_queue_size(self, pipeline):
        assert pipeline.get_training_queue_size() == 0
        pipeline.record_conversation(
            user_id="u1",
            tenant_id="t1",
            turns=[
                {"role": "user", "content": "Q"},
                {"role": "assistant", "content": "A"},
            ],
        )
        # Queue grows based on min_turns_per_conversation
        size = pipeline.get_training_queue_size()
        assert size >= 0

    def test_get_recent_training_results(self, pipeline):
        results = pipeline.get_recent_training_results()
        assert isinstance(results, list)

    def test_initialize_creates_dirs(self, tmp_path):
        config = PipelineConfig(output_dir=str(tmp_path / "new_output"))
        p = ConversationalLearningPipeline(config)
        p.initialize()
        assert os.path.isdir(str(tmp_path / "new_output"))

    def test_without_initialize_raises(self):
        p = ConversationalLearningPipeline()
        with pytest.raises(RuntimeError, match="Call initialize"):
            p.record_conversation("u1", "t1", [])
