import hashlib
import json
import logging
import os
import re
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ConversationTurn:
    turn_id: str
    role: str
    content: str
    timestamp: str
    metadata: dict


@dataclass
class Conversation:
    conversation_id: str
    user_id: str
    tenant_id: str
    turns: list[ConversationTurn]
    status: str
    feedback_scores: dict
    created_at: str
    updated_at: str
    total_tokens: int
    metadata: dict


@dataclass
class TrainingDataset:
    dataset_id: str
    conversations: list[dict]
    source_conversation_ids: list[str]
    total_samples: int
    quality_score: float
    created_at: str
    metadata: dict


@dataclass
class PipelineConfig:
    min_conversations_for_training: int = 10
    min_turns_per_conversation: int = 4
    quality_threshold: float = 0.5
    include_feedback: bool = True
    feedback_weight_threshold: float = 3.0
    deduplication_threshold: float = 0.9
    training_batch_size: int = 100
    auto_train_enabled: bool = True
    max_conversations_per_training: int = 1000
    conversation_window_hours: int = 168
    output_dir: str = "./conversational_training"


# ---------------------------------------------------------------------------
# ConversationStore
# ---------------------------------------------------------------------------

class ConversationStore:
    def __init__(self, storage_path: str = "./conversation_store") -> None:
        self._conversations: dict[str, Conversation] = {}
        self._storage_path = storage_path
        self._turn_index: dict[str, str] = {}
        self._metadata_path = os.path.join(storage_path, "conversations.json")
        Path(storage_path).mkdir(parents=True, exist_ok=True)
        self._load()

    def add_conversation(self, conversation: Conversation) -> str:
        self._conversations[conversation.conversation_id] = conversation
        for turn in conversation.turns:
            self._turn_index[turn.turn_id] = conversation.conversation_id
        self._save()
        return conversation.conversation_id

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self._conversations.get(conversation_id)

    def list_conversations(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Conversation]:
        results: list[Conversation] = []
        for conv in self._conversations.values():
            if user_id is not None and conv.user_id != user_id:
                continue
            if tenant_id is not None and conv.tenant_id != tenant_id:
                continue
            if status is not None and conv.status != status:
                continue
            results.append(conv)
        results.sort(key=lambda c: c.created_at, reverse=True)
        return results[offset: offset + limit]

    def update_conversation(self, conversation: Conversation) -> None:
        if conversation.conversation_id not in self._conversations:
            raise KeyError(f"Conversation {conversation.conversation_id} not found")
        self._conversations[conversation.conversation_id] = conversation
        for turn in conversation.turns:
            self._turn_index[turn.turn_id] = conversation.conversation_id
        self._save()

    def add_turn(self, conversation_id: str, turn: ConversationTurn) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise KeyError(f"Conversation {conversation_id} not found")
        conv.turns.append(turn)
        self._turn_index[turn.turn_id] = conversation_id
        conv.updated_at = datetime.now(timezone.utc).isoformat()
        conv.total_tokens += len(turn.content.split())
        self._save()

    def update_feedback(self, conversation_id: str, turn_id: str, score: int) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise KeyError(f"Conversation {conversation_id} not found")
        clamped = max(1, min(5, score))
        conv.feedback_scores[turn_id] = clamped
        conv.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()

    def archive_conversation(self, conversation_id: str) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise KeyError(f"Conversation {conversation_id} not found")
        conv.status = "archived"
        conv.updated_at = datetime.now(timezone.utc).isoformat()
        self._save()

    def delete_conversation(self, conversation_id: str) -> None:
        conv = self._conversations.pop(conversation_id, None)
        if conv is None:
            raise KeyError(f"Conversation {conversation_id} not found")
        for turn in conv.turns:
            self._turn_index.pop(turn.turn_id, None)
        self._save()

    def get_recent_conversations(
        self, hours: int, min_turns: int = 2
    ) -> list[Conversation]:
        cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
        results: list[Conversation] = []
        for conv in self._conversations.values():
            if conv.status == "archived":
                continue
            try:
                created_ts = datetime.fromisoformat(conv.created_at).timestamp()
            except (ValueError, TypeError):
                continue
            if created_ts < cutoff:
                continue
            if len(conv.turns) < min_turns:
                continue
            results.append(conv)
        results.sort(key=lambda c: c.created_at, reverse=True)
        return results

    def get_conversation_stats(self) -> dict:
        total = len(self._conversations)
        active = sum(1 for c in self._conversations.values() if c.status == "active")
        completed = sum(
            1 for c in self._conversations.values() if c.status == "completed"
        )
        archived = sum(
            1 for c in self._conversations.values() if c.status == "archived"
        )
        total_turns = sum(len(c.turns) for c in self._conversations.values())
        total_tokens = sum(c.total_tokens for c in self._conversations.values())
        avg_turns = total_turns / total if total > 0 else 0.0
        avg_tokens = total_tokens / total if total > 0 else 0.0
        return {
            "total_conversations": total,
            "active": active,
            "completed": completed,
            "archived": archived,
            "total_turns": total_turns,
            "avg_turns_per_conversation": round(avg_turns, 2),
            "avg_tokens_per_conversation": round(avg_tokens, 2),
        }

    def _save(self) -> None:
        data: dict[str, Any] = {}
        for cid, conv in self._conversations.items():
            data[cid] = {
                "conversation_id": conv.conversation_id,
                "user_id": conv.user_id,
                "tenant_id": conv.tenant_id,
                "turns": [
                    {
                        "turn_id": t.turn_id,
                        "role": t.role,
                        "content": t.content,
                        "timestamp": t.timestamp,
                        "metadata": t.metadata,
                    }
                    for t in conv.turns
                ],
                "status": conv.status,
                "feedback_scores": conv.feedback_scores,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "total_tokens": conv.total_tokens,
                "metadata": conv.metadata,
            }
        try:
            with open(self._metadata_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as exc:
            logger.error("Failed to persist conversations: %s", exc)

    def _load(self) -> None:
        if not os.path.exists(self._metadata_path):
            return
        try:
            with open(self._metadata_path, "r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load conversations: %s", exc)
            return
        for cid, entry in data.items():
            turns = [
                ConversationTurn(
                    turn_id=t["turn_id"],
                    role=t["role"],
                    content=t["content"],
                    timestamp=t["timestamp"],
                    metadata=t.get("metadata", {}),
                )
                for t in entry.get("turns", [])
            ]
            conv = Conversation(
                conversation_id=entry["conversation_id"],
                user_id=entry["user_id"],
                tenant_id=entry["tenant_id"],
                turns=turns,
                status=entry.get("status", "active"),
                feedback_scores=entry.get("feedback_scores", {}),
                created_at=entry["created_at"],
                updated_at=entry["updated_at"],
                total_tokens=entry.get("total_tokens", 0),
                metadata=entry.get("metadata", {}),
            )
            self._conversations[cid] = conv
            for turn in turns:
                self._turn_index[turn.turn_id] = cid
        logger.info("Loaded %d conversations from disk", len(self._conversations))


# ---------------------------------------------------------------------------
# DatasetBuilder
# ---------------------------------------------------------------------------

class DatasetBuilder:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config

    def build_dataset(self, conversations: list[Conversation]) -> TrainingDataset:
        all_pairs: list[dict] = []
        source_ids: list[str] = []
        quality_scores: list[float] = []

        for conv in conversations:
            pairs = self._extract_training_pairs(conv)
            filtered = self._apply_quality_filter(pairs, conv)
            if filtered:
                all_pairs.extend(filtered)
                source_ids.append(conv.conversation_id)
                quality_scores.append(self._compute_quality_score(filtered, conv))

        deduplicated = self._deduplicate(all_pairs)
        avg_quality = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        )

        dataset = TrainingDataset(
            dataset_id=f"ds_{uuid.uuid4().hex[:12]}",
            conversations=deduplicated,
            source_conversation_ids=source_ids,
            total_samples=len(deduplicated),
            quality_score=round(avg_quality, 4),
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "original_pair_count": len(all_pairs),
                "deduplicated_pair_count": len(deduplicated),
                "source_conversation_count": len(source_ids),
            },
        )
        logger.info(
            "Built dataset %s — %d samples from %d conversations (quality=%.3f)",
            dataset.dataset_id,
            dataset.total_samples,
            len(source_ids),
            dataset.quality_score,
        )
        return dataset

    def _extract_training_pairs(self, conv: Conversation) -> list[dict]:
        pairs: list[dict] = []
        user_turns: list[ConversationTurn] = []
        assistant_turns: list[ConversationTurn] = []

        for turn in conv.turns:
            if turn.role == "user":
                user_turns.append(turn)
            elif turn.role == "assistant":
                assistant_turns.append(turn)

        if not user_turns or not assistant_turns:
            return pairs

        context_parts: list[str] = []
        assistant_idx = 0

        for user_turn in user_turns:
            context_parts.append(user_turn.content)

            while assistant_idx < len(assistant_turns):
                asst_turn = assistant_turns[assistant_idx]
                try:
                    user_ts = datetime.fromisoformat(user_turn.timestamp)
                    asst_ts = datetime.fromisoformat(asst_turn.timestamp)
                except (ValueError, TypeError):
                    assistant_idx += 1
                    continue

                if asst_ts >= user_ts:
                    if len(context_parts) > 1:
                        instruction = context_parts[0]
                        input_text = "\n".join(context_parts[1:])
                    else:
                        instruction = context_parts[0]
                        input_text = ""

                    pair = self._format_chatml(instruction, input_text, asst_turn.content)
                    pair["_turn_ids"] = [user_turn.turn_id, asst_turn.turn_id]
                    pairs.append(pair)
                    assistant_idx += 1
                    break

                assistant_idx += 1

        if not pairs and user_turns and assistant_turns:
            user_turn = user_turns[0]
            asst_turn = assistant_turns[-1]
            pair = self._format_chatml(user_turn.content, "", asst_turn.content)
            pair["_turn_ids"] = [user_turn.turn_id, asst_turn.turn_id]
            pairs.append(pair)

        return pairs

    def _apply_quality_filter(
        self, pairs: list[dict], conv: Conversation
    ) -> list[dict]:
        if not self.config.include_feedback or not conv.feedback_scores:
            return pairs

        if not pairs:
            return pairs

        avg_feedback = sum(conv.feedback_scores.values()) / len(
            conv.feedback_scores
        )
        if avg_feedback < self.config.feedback_weight_threshold:
            return []

        filtered: list[dict] = []
        for pair in pairs:
            turn_ids = pair.get("_turn_ids", [])
            pair_scores = [
                conv.feedback_scores[tid]
                for tid in turn_ids
                if tid in conv.feedback_scores
            ]
            if pair_scores:
                pair_avg = sum(pair_scores) / len(pair_scores)
                if pair_avg < self.config.feedback_weight_threshold:
                    continue
            filtered.append(pair)
        return filtered

    def _deduplicate(self, pairs: list[dict]) -> list[dict]:
        if not pairs:
            return pairs

        kept: list[dict] = []
        seen_signatures: list[str] = []

        for pair in pairs:
            instruction = pair.get("instruction", "")
            output = pair.get("output", "")
            sig_text = f"{instruction.lower().strip()}|||{output.lower().strip()}"
            sig_tokens = set(re.findall(r"\w+", sig_text))

            is_dup = False
            for existing_sig in seen_signatures:
                existing_tokens = set(re.findall(r"\w+", existing_sig))
                if not sig_tokens or not existing_tokens:
                    continue
                intersection = sig_tokens & existing_tokens
                union = sig_tokens | existing_tokens
                similarity = len(intersection) / len(union) if union else 0.0
                if similarity >= self.config.deduplication_threshold:
                    is_dup = True
                    break

            if not is_dup:
                kept.append(pair)
                seen_signatures.append(sig_text)

        removed_count = len(pairs) - len(kept)
        if removed_count > 0:
            logger.info("Deduplication removed %d/%d pairs", removed_count, len(pairs))
        return kept

    def _compute_quality_score(
        self, pairs: list[dict], conv: Conversation
    ) -> float:
        if not pairs:
            return 0.0

        score_components: list[float] = []

        content_length_score = min(
            1.0,
            sum(len(p.get("output", "")) for p in pairs)
            / max(1, len(pairs) * 200),
        )
        score_components.append(content_length_score)

        if conv.feedback_scores:
            avg_fb = sum(conv.feedback_scores.values()) / len(conv.feedback_scores)
            feedback_score = avg_fb / 5.0
            score_components.append(feedback_score)

        turn_count_score = min(1.0, len(conv.turns) / self.config.min_turns_per_conversation)
        score_components.append(turn_count_score)

        diversity_scores: list[float] = []
        for i, pair in enumerate(pairs):
            other_outputs = [
                pairs[j].get("output", "")
                for j in range(len(pairs))
                if j != i
            ]
            if not other_outputs:
                diversity_scores.append(1.0)
                continue
            tokens_a = set(re.findall(r"\w+", pair.get("output", "").lower()))
            max_sim = 0.0
            for other in other_outputs:
                tokens_b = set(re.findall(r"\w+", other.lower()))
                if not tokens_a or not tokens_b:
                    continue
                sim = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
                max_sim = max(max_sim, sim)
            diversity_scores.append(1.0 - max_sim)

        if diversity_scores:
            score_components.append(sum(diversity_scores) / len(diversity_scores))

        return sum(score_components) / len(score_components) if score_components else 0.0

    def _format_chatml(
        self, instruction: str, input_text: str, output: str
    ) -> dict:
        return {
            "instruction": instruction,
            "input": input_text,
            "output": output,
        }


# ---------------------------------------------------------------------------
# ConversationalLearningPipeline
# ---------------------------------------------------------------------------

class ConversationalLearningPipeline:
    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self.config = config or PipelineConfig()
        self.conversation_store: Optional[ConversationStore] = None
        self.dataset_builder: Optional[DatasetBuilder] = None
        self._pending_conversations: deque[str] = deque()
        self._training_queue: deque[str] = deque()
        self._pipeline_stats: dict[str, Any] = {
            "conversations_recorded": 0,
            "training_runs_triggered": 0,
            "total_samples_generated": 0,
            "total_training_time_seconds": 0.0,
            "last_training_at": None,
            "training_results": [],
        }

    def initialize(self) -> None:
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        store_path = os.path.join(str(output_dir), "conversation_store")
        self.conversation_store = ConversationStore(storage_path=store_path)
        self.dataset_builder = DatasetBuilder(self.config)

        stats_path = os.path.join(str(output_dir), "pipeline_stats.json")
        if os.path.exists(stats_path):
            try:
                with open(stats_path, "r") as f:
                    saved = json.load(f)
                self._pipeline_stats.update(saved)
                logger.info("Loaded pipeline stats from disk")
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Could not load pipeline stats: %s", exc)

        logger.info(
            "ConversationalLearningPipeline initialized — output_dir=%s",
            self.config.output_dir,
        )

    def _ensure_initialized(self) -> None:
        if self.conversation_store is None or self.dataset_builder is None:
            raise RuntimeError("Call initialize() before using the pipeline")

    def record_conversation(
        self,
        user_id: str,
        tenant_id: str,
        turns: list[dict],
        feedback: Optional[dict] = None,
    ) -> str:
        self._ensure_initialized()
        now = datetime.now(timezone.utc).isoformat()

        conv_turns: list[ConversationTurn] = []
        total_tokens = 0
        for turn_data in turns:
            turn = ConversationTurn(
                turn_id=f"turn_{uuid.uuid4().hex[:12]}",
                role=turn_data.get("role", "user"),
                content=turn_data.get("content", ""),
                timestamp=turn_data.get("timestamp", now),
                metadata=turn_data.get("metadata", {}),
            )
            conv_turns.append(turn)
            total_tokens += len(turn.content.split())

        conversation = Conversation(
            conversation_id=f"conv_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            tenant_id=tenant_id,
            turns=conv_turns,
            status="active",
            feedback_scores=feedback or {},
            created_at=now,
            updated_at=now,
            total_tokens=total_tokens,
            metadata={},
        )

        self.conversation_store.add_conversation(conversation)
        self._pipeline_stats["conversations_recorded"] += 1
        self._pending_conversations.append(conversation.conversation_id)

        meets_criteria = (
            len(conv_turns) >= self.config.min_turns_per_conversation
        )
        if meets_criteria:
            self._training_queue.append(conversation.conversation_id)

        logger.info(
            "Recorded conversation %s (%d turns, meets_criteria=%s)",
            conversation.conversation_id,
            len(conv_turns),
            meets_criteria,
        )

        if (
            self.config.auto_train_enabled
            and len(self._training_queue) >= self.config.training_batch_size
        ):
            logger.info(
                "Auto-training triggered — queue size %d >= batch_size %d",
                len(self._training_queue),
                self.config.training_batch_size,
            )
            self.process_pending()

        self._persist_stats()
        return conversation.conversation_id

    def record_turn(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> str:
        self._ensure_initialized()
        turn = ConversationTurn(
            turn_id=f"turn_{uuid.uuid4().hex[:12]}",
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        self.conversation_store.add_turn(conversation_id, turn)

        conv = self.conversation_store.get_conversation(conversation_id)
        if conv is not None and len(conv.turns) >= self.config.min_turns_per_conversation:
            if conversation_id not in self._training_queue:
                self._training_queue.append(conversation_id)

        self._pipeline_stats["conversations_recorded"] += 1
        self._persist_stats()
        return turn.turn_id

    def submit_feedback(
        self, conversation_id: str, turn_id: str, score: int
    ) -> None:
        self._ensure_initialized()
        self.conversation_store.update_feedback(conversation_id, turn_id, score)
        logger.info(
            "Feedback recorded — conv=%s, turn=%s, score=%d",
            conversation_id,
            turn_id,
            score,
        )

    def build_training_dataset(
        self,
        hours: Optional[int] = None,
        min_quality: Optional[float] = None,
    ) -> TrainingDataset:
        self._ensure_initialized()
        window = hours or self.config.conversation_window_hours
        quality = min_quality if min_quality is not None else self.config.quality_threshold

        conversations = self.conversation_store.get_recent_conversations(
            hours=window, min_turns=self.config.min_turns_per_conversation
        )

        logger.info(
            "Found %d conversations within %dh window", len(conversations), window
        )

        conversations = conversations[: self.config.max_conversations_per_training]

        dataset = self.dataset_builder.build_dataset(conversations)

        if dataset.quality_score < quality:
            logger.warning(
                "Dataset quality %.3f below threshold %.3f — dataset still returned",
                dataset.quality_score,
                quality,
            )

        self._pipeline_stats["total_samples_generated"] += dataset.total_samples
        self._persist_stats()
        return dataset

    def train_adapter(
        self,
        dataset: TrainingDataset,
        adapter_name: str,
        base_model: str = "Qwen/Qwen2.5-0.5B-Instruct",
        **training_kwargs: Any,
    ) -> dict:
        self._ensure_initialized()

        from training.lora_trainer import (
            LoRATrainer,
            TrainingConfig,
        )
        from training.model_registry import (
            ModelRegistry,
            RegistryConfig,
        )

        t_start = time.monotonic()

        output_dir = os.path.join(
            self.config.output_dir, "adapters", adapter_name
        )
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        trainer_config = TrainingConfig(
            base_model_name=base_model,
            output_dir=output_dir,
            **training_kwargs,
        )

        trainer = LoRATrainer(trainer_config)

        logger.info("Setting up model for adapter training: %s", adapter_name)
        trainer.setup_model()

        conversations_for_trainer = dataset.conversations
        logger.info(
            "Training adapter '%s' on %d samples",
            adapter_name,
            len(conversations_for_trainer),
        )

        training_history = trainer.train(conversations_for_trainer)

        training_end = time.monotonic()
        training_time = training_end - t_start

        registry_config = RegistryConfig(
            base_path=os.path.join(self.config.output_dir, "model_registry")
        )
        registry = ModelRegistry(registry_config)

        best_checkpoint = None
        for ckpt in reversed(trainer.checkpoints):
            if ckpt.is_best:
                best_checkpoint = ckpt
                break
        if best_checkpoint is None and trainer.checkpoints:
            best_checkpoint = trainer.checkpoints[-1]

        adapter_path = best_checkpoint.adapter_path if best_checkpoint else output_dir
        checkpoint_path = output_dir

        final_loss = training_history[-1].train_loss if training_history else 0.0
        final_eval_loss = None
        for m in reversed(training_history):
            if m.eval_loss is not None:
                final_eval_loss = m.eval_loss
                break

        metrics: dict[str, Any] = {
            "train_loss": final_loss,
            "eval_loss": final_eval_loss,
            "num_steps": len(training_history),
            "dataset_size": dataset.total_samples,
            "dataset_quality_score": dataset.quality_score,
            "source_conversations": len(dataset.source_conversation_ids),
            "training_time_seconds": round(training_time, 2),
        }

        tags: dict[str, str] = {
            "adapter_name": adapter_name,
            "pipeline": "conversational",
            "dataset_id": dataset.dataset_id,
        }

        model_version = registry.register_version(
            model_name=adapter_name,
            checkpoint_path=checkpoint_path,
            config=trainer_config.__dict__,
            metrics=metrics,
            algorithm="lora",
            adapter_path=adapter_path,
            training_dataset_hash=hashlib.sha256(
                dataset.dataset_id.encode()
            ).hexdigest()[:16],
            training_dataset_size=dataset.total_samples,
            created_by="conversational_pipeline",
            tags=tags,
            training_time_seconds=training_time,
        )

        result: dict[str, Any] = {
            "adapter_name": adapter_name,
            "version_id": model_version.version_id,
            "version_number": model_version.version_number,
            "checkpoint_id": best_checkpoint.checkpoint_id if best_checkpoint else None,
            "adapter_path": adapter_path,
            "metrics": metrics,
            "training_history_steps": len(training_history),
            "dataset_id": dataset.dataset_id,
            "dataset_size": dataset.total_samples,
            "quality_score": dataset.quality_score,
            "training_time_seconds": round(training_time, 2),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        self._pipeline_stats["training_runs_triggered"] += 1
        self._pipeline_stats["total_training_time_seconds"] += training_time
        self._pipeline_stats["last_training_at"] = datetime.now(timezone.utc).isoformat()
        self._pipeline_stats.setdefault("training_results", []).append(
            {
                "adapter_name": adapter_name,
                "version_id": model_version.version_id,
                "dataset_size": dataset.total_samples,
                "train_loss": final_loss,
                "training_time_seconds": round(training_time, 2),
                "completed_at": result["completed_at"],
            }
        )
        self._persist_stats()

        logger.info(
            "Adapter '%s' trained — version %d, loss=%.4f, time=%.1fs",
            adapter_name,
            model_version.version_number,
            final_loss,
            training_time,
        )

        return result

    def process_pending(self) -> dict:
        self._ensure_initialized()

        queue_size = len(self._training_queue)
        if queue_size < self.config.min_conversations_for_training:
            return {
                "status": "insufficient_data",
                "queue_size": queue_size,
                "required": self.config.min_conversations_for_training,
                "trained": False,
            }

        batch_ids = []
        while (
            self._training_queue
            and len(batch_ids) < self.config.max_conversations_per_training
        ):
            batch_ids.append(self._training_queue.popleft())

        conversations: list[Conversation] = []
        for cid in batch_ids:
            conv = self.conversation_store.get_conversation(cid)
            if conv is not None:
                conversations.append(conv)

        if not conversations:
            return {
                "status": "no_valid_conversations",
                "queue_size": len(self._training_queue),
                "trained": False,
            }

        dataset = self.dataset_builder.build_dataset(conversations)

        if dataset.total_samples == 0:
            return {
                "status": "empty_dataset",
                "queue_size": len(self._training_queue),
                "conversations_processed": len(batch_ids),
                "trained": False,
            }

        adapter_name = f"conv_adapter_{uuid.uuid4().hex[:8]}"

        result = self.train_adapter(
            dataset=dataset,
            adapter_name=adapter_name,
        )

        for cid in batch_ids:
            conv = self.conversation_store.get_conversation(cid)
            if conv is not None:
                conv.status = "completed"
                conv.updated_at = datetime.now(timezone.utc).isoformat()
                self.conversation_store.update_conversation(conv)

        result["conversations_processed"] = len(batch_ids)
        result["status"] = "trained"
        return result

    def get_pipeline_stats(self) -> dict:
        self._ensure_initialized()

        store_stats = self.conversation_store.get_conversation_stats()
        recent_results = self.get_recent_training_results(10)

        return {
            "pipeline": dict(self._pipeline_stats),
            "conversation_store": store_stats,
            "training_queue_size": len(self._training_queue),
            "pending_conversations": len(self._pending_conversations),
            "recent_training_runs": len(recent_results),
            "config": {
                "min_conversations_for_training": self.config.min_conversations_for_training,
                "min_turns_per_conversation": self.config.min_turns_per_conversation,
                "quality_threshold": self.config.quality_threshold,
                "training_batch_size": self.config.training_batch_size,
                "auto_train_enabled": self.config.auto_train_enabled,
                "conversation_window_hours": self.config.conversation_window_hours,
            },
        }

    def get_training_queue_size(self) -> int:
        return len(self._training_queue)

    def get_recent_training_results(self, limit: int = 10) -> list[dict]:
        results = self._pipeline_stats.get("training_results", [])
        return results[-limit:]

    def _persist_stats(self) -> None:
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stats_path = os.path.join(str(output_dir), "pipeline_stats.json")
        try:
            with open(stats_path, "w") as f:
                json.dump(self._pipeline_stats, f, indent=2, default=str)
        except OSError as exc:
            logger.warning("Failed to persist pipeline stats: %s", exc)
