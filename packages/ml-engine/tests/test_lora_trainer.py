import hashlib
import json
import os
import shutil
import tempfile

import pytest
import torch

from training.lora_trainer import (
    TrainingConfig,
    TrainingMetrics,
    CheckpointInfo,
    ConversationDataset,
    LoRATrainer,
    _set_seed,
    _save_rng_state,
    _load_rng_state,
)


class TestSetSeed:
    def test_sets_reproducible_state(self):
        _set_seed(42)
        a = torch.rand(5)
        _set_seed(42)
        b = torch.rand(5)
        assert torch.equal(a, b)

    def test_different_seeds_differ(self):
        _set_seed(1)
        a = torch.rand(5)
        _set_seed(2)
        b = torch.rand(5)
        assert not torch.equal(a, b)


class TestRngState:
    def test_save_and_load_roundtrip(self):
        _set_seed(123)
        state = _save_rng_state()
        _set_seed(999)
        _load_rng_state(state)
        a = torch.rand(5)
        _set_seed(123)
        b = torch.rand(5)
        assert torch.equal(a, b)

    def test_state_dict_keys(self):
        state = _save_rng_state()
        assert "python" in state
        assert "numpy" in state
        assert "torch_cpu" in state


class TestTrainingConfig:
    def test_default_config(self):
        config = TrainingConfig()
        assert config.base_model_name == "Qwen/Qwen2.5-0.5B-Instruct"
        assert config.lora_r == 16
        assert config.lora_alpha == 32
        assert config.lora_dropout == 0.05
        assert config.num_epochs == 3
        assert config.batch_size == 4
        assert config.learning_rate == 2e-4
        assert config.seed == 42

    def test_config_hash(self):
        config = TrainingConfig()
        h = config.config_hash()
        assert isinstance(h, str)
        assert len(h) == 16

    def test_config_hash_deterministic(self):
        config = TrainingConfig()
        assert config.config_hash() == config.config_hash()

    def test_config_hash_changes_with_params(self):
        a = TrainingConfig(lora_r=8)
        b = TrainingConfig(lora_r=32)
        assert a.config_hash() != b.config_hash()

    def test_custom_config(self):
        config = TrainingConfig(
            lora_r=8,
            lora_alpha=16,
            num_epochs=1,
            batch_size=2,
            learning_rate=1e-3,
            seed=0,
        )
        assert config.lora_r == 8
        assert config.num_epochs == 1
        assert config.seed == 0

    def test_remove_data_ids_default_empty(self):
        config = TrainingConfig()
        assert config.remove_data_ids == []

    def test_config_to_dict_roundtrip(self):
        config = TrainingConfig(num_epochs=5)
        raw = json.dumps(config.__dict__, sort_keys=True, default=str)
        restored = json.loads(raw)
        assert restored["num_epochs"] == 5


class TestTrainingMetrics:
    def test_creation(self):
        m = TrainingMetrics(
            epoch=1.5,
            step=100,
            train_loss=0.5,
            eval_loss=0.6,
            learning_rate=2e-4,
            grad_norm=1.0,
            train_samples_per_second=10.0,
            global_step=100,
        )
        assert m.epoch == 1.5
        assert m.step == 100
        assert m.train_loss == 0.5
        assert m.eval_loss == 0.6
        assert m.timestamp is not None

    def test_default_timestamp(self):
        m = TrainingMetrics(
            epoch=0, step=0, train_loss=0.0, eval_loss=None,
            learning_rate=0.0, grad_norm=0.0,
            train_samples_per_second=0.0, global_step=0,
        )
        assert "T" in m.timestamp


class TestCheckpointInfo:
    def test_creation(self):
        c = CheckpointInfo(
            checkpoint_id="ckpt_abc",
            adapter_path="/tmp/adapter",
            epoch=1,
            step=50,
            metrics={"loss": 0.5},
            config_hash="abc123",
            created_at="2024-01-01T00:00:00",
            parent_checkpoint_id=None,
            is_best=True,
            file_size_bytes=1024,
            sha256="deadbeef",
        )
        assert c.checkpoint_id == "ckpt_abc"
        assert c.is_best is True


class TestConversationDataset:
    def test_dataset_creation(self):
        conversations = [
            {"instruction": "What is AI?", "input": "", "output": "AI is artificial intelligence."},
            {"instruction": "Explain ML", "input": "", "output": "ML is a subset of AI."},
        ]

        class MockTokenizer:
            pad_token_id = 0
            eos_token_id = 1

            def __call__(self, text, truncation=True, max_length=512, padding=False, return_tensors=None):
                tokens = list(range(5, 15))
                return {"input_ids": tokens, "attention_mask": [1] * len(tokens)}

            def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
                return messages[-1]["content"]

        ds = ConversationDataset(conversations, MockTokenizer(), max_length=512)
        assert len(ds) == 2
        item = ds[0]
        assert "input_ids" in item
        assert "attention_mask" in item
        assert "labels" in item
        assert item["input_ids"].shape[0] == 512

    def test_dataset_length(self):
        conversations = [{"instruction": "q", "input": "", "output": "a"}] * 5

        class MockTokenizer:
            pad_token_id = 0
            eos_token_id = 1
            def __call__(self, **kw):
                return {"input_ids": [1, 2, 3], "attention_mask": [1, 1, 1]}
            def apply_chat_template(self, messages, **kw):
                return messages[-1]["content"]

        ds = ConversationDataset(conversations, MockTokenizer(), max_length=512)
        assert len(ds) == 5

    def test_labels_mask_prompt(self):
        conversations = [{"instruction": "Hi", "input": "", "output": "Hello"}]

        class MockTokenizer:
            pad_token_id = 0
            eos_token_id = 1
            def __call__(self, text, truncation=True, max_length=512, padding=False, return_tensors=None):
                ids = list(range(10))
                return {"input_ids": ids, "attention_mask": [1] * len(ids)}
            def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
                return "PROMPT"

        ds = ConversationDataset(conversations, MockTokenizer(), max_length=512)
        item = ds[0]
        label_list = item["labels"].tolist()
        assert label_list.count(-100) > 0


class TestLoRATrainer:
    def test_init(self):
        config = TrainingConfig(num_epochs=1, batch_size=2)
        trainer = LoRATrainer(config)
        assert trainer.config == config
        assert trainer.model is None
        assert trainer.tokenizer is None
        assert trainer.peft_model is None
        assert isinstance(trainer.training_history, list)
        assert len(trainer.checkpoints) == 0

    def test_output_dir_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "ckpts")
            config = TrainingConfig(output_dir=out)
            trainer = LoRATrainer(config)
            assert os.path.isdir(out)

    def test_get_adapter_info_no_model(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        info = trainer.get_adapter_info()
        assert info["mode"] == "no_model"
        assert "peft_available" in info

    def test_predict_without_model_raises(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        with pytest.raises(RuntimeError, match="Call setup_model"):
            trainer.predict("test")

    def test_train_without_model_raises(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        with pytest.raises(RuntimeError, match="Call setup_model"):
            trainer.train([{"instruction": "q", "input": "", "output": "a"}])

    def test_evaluate_without_model_raises(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        with pytest.raises(RuntimeError, match="Call setup_model"):
            ds = ConversationDataset([], None)
            trainer.evaluate(ds)

    def test_prepare_dataset_without_tokenizer_raises(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        with pytest.raises(RuntimeError, match="Call setup_model"):
            trainer.prepare_dataset([{"instruction": "q", "input": "", "output": "a"}])

    def test_save_checkpoint_without_model_raises(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        with pytest.raises(RuntimeError, match="No model to checkpoint"):
            trainer.save_checkpoint(epoch=0, step=0, metrics={})

    def test_compute_sha256_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            path = f.name
        try:
            h = LoRATrainer._compute_sha256(path)
            assert len(h) == 64
            expected = hashlib.sha256(b"hello world").hexdigest()
            assert h == expected
        finally:
            os.unlink(path)

    def test_compute_sha256_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = os.path.join(tmpdir, "a.txt")
            f2 = os.path.join(tmpdir, "b.txt")
            with open(f1, "w") as f:
                f.write("aaa")
            with open(f2, "w") as f:
                f.write("bbb")
            h = LoRATrainer._compute_sha256(tmpdir)
            assert len(h) == 64

    def test_dir_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f = os.path.join(tmpdir, "data.bin")
            with open(f, "wb") as fh:
                fh.write(b"x" * 1024)
            size = LoRATrainer._dir_size(tmpdir)
            assert size == 1024

    def test_cleanup_old_checkpoints_noop(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        removed = trainer.cleanup_old_checkpoints(keep_last_n=5)
        assert removed == []

    def test_export_adapter_not_found_raises(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        with pytest.raises(FileNotFoundError):
            trainer.export_adapter("nonexistent_ckpt", "/tmp/export")

    def test_device_is_cpu_or_cuda(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        assert trainer._device.type in ("cpu", "cuda")

    def test_peft_mode_flag(self):
        from training.lora_trainer import PEFT_AVAILABLE
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        assert trainer._peft_mode == PEFT_AVAILABLE

    def test_get_trainable_count_no_model(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        assert trainer._get_trainable_count() == 0

    def test_training_history_empty_init(self):
        config = TrainingConfig()
        trainer = LoRATrainer(config)
        assert trainer.training_history == []
        assert trainer.checkpoints == []
