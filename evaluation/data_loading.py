"""Dataset loaders for the VeriUnlearn evaluation framework.

Provides unified access to image (MNIST, CIFAR-10) and text (IMDB, AG News)
datasets with deterministic subsampling, stratified splits, forget-set creation,
and DataLoaders ready for benchmarking unlearning algorithms.
"""
from __future__ import annotations

import logging
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

import torch
import importlib
_hf_datasets = importlib.import_module("datasets")
from torch.utils.data import (
    DataLoader,
    Dataset,
    IterableDataset,
    Subset,
    random_split,
)
from evaluation.config import DatasetConfig, SeedConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Generic utilities
# ---------------------------------------------------------------------------

NUM_WORKERS = 0  # safe default; overridden per-platform in DataLoader helpers


def _seed_generator(seed: int) -> random.Random:
    """Return an independent ``random.Random`` instance so global state is untouched."""
    return random.Random(seed)


def _stratified_split(
    indices: list[int],
    labels: list[int],
    *,
    train_frac: float,
    val_frac: float,
    seed: int,
) -> tuple[list[int], list[int], list[int]]:
    """Return ``(train_idx, val_idx, test_idx)`` preserving class proportions."""
    rng = _seed_generator(seed)

    # Group indices by label
    label_to_indices: dict[int, list[int]] = {}
    for idx, lbl in zip(indices, labels):
        label_to_indices.setdefault(lbl, []).append(idx)

    train_idx: list[int] = []
    val_idx: list[int] = []
    test_idx: list[int] = []

    for lbl in sorted(label_to_indices):
        group = list(label_to_indices[lbl])
        rng.shuffle(group)
        n = len(group)
        n_train = int(n * train_frac)
        n_val = int(n * val_frac)
        train_idx.extend(group[:n_train])
        val_idx.extend(group[n_train : n_train + n_val])
        test_idx.extend(group[n_train + n_val :])

    return train_idx, val_idx, test_idx


def _subsample(indices: list[int], max_samples: int | None, seed: int) -> list[int]:
    """Randomly subsample *indices* down to *max_samples* (deterministic)."""
    if max_samples is None or max_samples >= len(indices):
        return indices
    rng = _seed_generator(seed)
    return rng.sample(indices, max_samples)


def _compute_stats(
    dataset: Dataset,
    indices: Sequence[int],
    split_name: str,
) -> dict[str, Any]:
    """Return lightweight statistics for a set of *indices* inside *dataset*."""
    n = len(indices)
    labels: list[int] = []
    for i in indices:
        _, lbl = dataset[i]
        if isinstance(lbl, torch.Tensor):
            lbl = lbl.item()
        labels.append(int(lbl))
    dist = Counter(labels)
    return {
        "split": split_name,
        "n_samples": n,
        "num_classes": len(dist),
        "class_distribution": dict(sorted(dist.items())),
        "class_balance": {k: round(v / n, 4) for k, v in sorted(dist.items())},
    }


# ---------------------------------------------------------------------------
# Image classification datasets
# ---------------------------------------------------------------------------

class _WrappedImageDataset(Dataset):
    """Thin wrapper that normalises tensor images and casts labels to int."""

    def __init__(
        self,
        base: Dataset,
        mean: tuple[float, ...],
        std: tuple[float, ...],
        normalize: bool = True,
    ) -> None:
        self._base = base
        self._normalize = normalize
        if normalize:
            self.registered_mean = torch.tensor(mean).view(len(mean), 1, 1)
            self.registered_std = torch.tensor(std).view(len(std), 1, 1)
        else:
            self.registered_mean = None
            self.registered_std = None

    def __len__(self) -> int:
        return len(self._base)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        img, lbl = self._base[idx]
        if not isinstance(img, torch.Tensor):
            img = torch.tensor(img, dtype=torch.float32)
        if img.dtype != torch.float32:
            img = img.float()
        if self._normalize and self.registered_mean is not None and self.registered_std is not None:
            img = (img - self.registered_mean) / self.registered_std
        return img, int(lbl)


class _ImageClassificationDataset(Dataset):
    """Load an image classification dataset from torchvision with lazy import."""

    def __init__(self, cfg: DatasetConfig, split: str) -> None:
        import torchvision  # lazy
        import torchvision.transforms as T

        root = Path(cfg.root)
        root.mkdir(parents=True, exist_ok=True)

        if cfg.name == "mnist":
            train = split == "train" or split == "val"
            ds = torchvision.datasets.MNIST(
                root=str(root), train=train, download=True, transform=T.ToTensor()
            )
        elif cfg.name == "cifar10":
            train = split == "train" or split == "val"
            transform = T.Compose([
                T.ToTensor(),
            ])
            ds = torchvision.datasets.CIFAR10(
                root=str(root), train=train, download=True, transform=transform
            )
        else:
            raise ValueError(f"Unknown image dataset: {cfg.name}")

        self._base = ds
        self._wrap = _WrappedImageDataset(
            ds, mean=cfg.mean, std=cfg.std, normalize=cfg.normalize,
        )

    def __len__(self) -> int:
        return len(self._wrap)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        return self._wrap[idx]

    @property
    def base(self) -> Dataset:
        return self._base


def _load_image_dataset(cfg: DatasetConfig, seed_cfg: SeedConfig) -> dict[str, Any]:
    """Full pipeline for an image dataset: load, split, subsample, wrap."""
    try:
        import torchvision
        import torchvision.transforms as T
    except ImportError:
        raise ImportError(
            "torchvision is required for image datasets (mnist, cifar10). "
            "Install with: pip install torchvision"
        )

    root = Path(cfg.root)
    root.mkdir(parents=True, exist_ok=True)

    if cfg.name == "mnist":
        full_train = torchvision.datasets.MNIST(
            root=str(root), train=True, download=True, transform=T.ToTensor()
        )
        test_ds = torchvision.datasets.MNIST(
            root=str(root), train=False, download=True, transform=T.ToTensor()
        )
    elif cfg.name == "cifar10":
        transform = T.Compose([T.ToTensor()])
        full_train = torchvision.datasets.CIFAR10(
            root=str(root), train=True, download=True, transform=transform
        )
        test_ds = torchvision.datasets.CIFAR10(
            root=str(root), train=False, download=True, transform=transform
        )
    else:
        raise ValueError(f"Unsupported image dataset: {cfg.name}")

    # Gather all labels from training set
    train_labels = [full_train[i][1] for i in range(len(full_train))]

    all_indices = list(range(len(full_train)))
    train_idx, val_idx, _ = _stratified_split(
        all_indices,
        train_labels,
        train_frac=cfg.train_split,
        val_frac=cfg.val_split / (cfg.train_split + cfg.val_split),
        seed=seed_cfg.global_seed,
    )

    # Subsample
    train_idx = _subsample(train_idx, cfg.max_samples, seed_cfg.global_seed)
    val_idx = _subsample(val_idx, cfg.max_samples, seed_cfg.global_seed)

    # Test indices come from the held-out torchvision test split
    test_indices = list(range(len(test_ds)))
    test_idx = _subsample(test_indices, cfg.max_samples, seed_cfg.global_seed)

    train_sub = Subset(full_train, train_idx)
    val_sub = Subset(full_train, val_idx)
    test_sub = Subset(test_ds, test_idx)

    # Normalise wrappers
    train_wrapped = _WrappedImageDataset(train_sub, mean=cfg.mean, std=cfg.std, normalize=cfg.normalize)
    val_wrapped = _WrappedImageDataset(val_sub, mean=cfg.mean, std=cfg.std, normalize=cfg.normalize)
    test_wrapped = _WrappedImageDataset(test_sub, mean=cfg.mean, std=cfg.std, normalize=cfg.normalize)

    return {
        "train": train_wrapped,
        "val": val_wrapped,
        "test": test_wrapped,
        "train_labels": [train_labels[i] for i in train_idx],
        "val_labels": [train_labels[i] for i in val_idx],
        "test_labels": [test_ds[i][1] for i in test_idx],
        "cfg": cfg,
    }


# ---------------------------------------------------------------------------
# Text classification datasets (HuggingFace)
# ---------------------------------------------------------------------------

class _TextClassificationDataset(Dataset):
    """Tokenised text classification dataset backed by HuggingFace ``datasets``."""

    def __init__(
        self,
        texts: list[str],
        labels: list[int],
        tokenizer: Any,
        max_seq_length: int,
    ) -> None:
        self._texts = texts
        self._labels = labels
        self._tokenizer = tokenizer
        self._max_seq_length = max_seq_length

    def __len__(self) -> int:
        return len(self._texts)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        encoding = self._tokenizer(
            self._texts[idx],
            max_length=self._max_seq_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "label": torch.tensor(self._labels[idx], dtype=torch.long),
        }


def _get_text_tokenizer(name: str, vocab_size: int) -> Any:
    """Return a simple whitespace+lower tokenizer (no heavy dependency)."""
    from typing import NamedTuple

    class _SimpleEncoding(NamedTuple):
        input_ids: torch.Tensor
        attention_mask: torch.Tensor

    class SimpleTokenizer:
        """Lightweight tokenizer that builds a vocab from training texts."""

        def __init__(self, vocab_size: int) -> None:
            self.vocab_size = vocab_size
            self.pad_token_id = 0
            self.unk_token_id = 1
            self._word2idx: dict[str, int] = {}

        def build_vocab(self, texts: list[str]) -> None:
            counter: Counter = Counter()
            for t in texts:
                counter.update(t.lower().split())
            most_common = counter.most_common(self.vocab_size - 2)
            self._word2idx = {"<pad>": 0, "<unk>": 1}
            for word, _ in most_common:
                self._word2idx[word] = len(self._word2idx)

        def __call__(
            self, text: str, max_length: int, padding: str, truncation: str, return_tensors: str
        ) -> dict[str, torch.Tensor]:
            tokens = text.lower().split()
            if truncation == "max_length" or truncation is True:
                tokens = tokens[:max_length]
            ids = [self._word2idx.get(t, self.unk_token_id) for t in tokens]
            mask = [1] * len(ids)
            pad_len = max_length - len(ids)
            ids += [self.pad_token_id] * pad_len
            mask += [0] * pad_len
            return {
                "input_ids": torch.tensor([ids], dtype=torch.long),
                "attention_mask": torch.tensor([mask], dtype=torch.long),
            }

    return SimpleTokenizer(vocab_size)


def _get_hf_tokenizer(name: str) -> Any:
    """Try to return a HuggingFace fast tokenizer, fall back to simple one."""
    try:
        from transformers import AutoTokenizer
        return AutoTokenizer.from_pretrained(name)
    except Exception:
        return None


_HF_DATASET_CONFIGS: dict[str, dict[str, Any]] = {
    "imdb": {
        "hf_name": "stanfordnlp/imdb",
        "text_key": "text",
        "label_key": "label",
        "num_classes": 2,
    },
    "ag_news": {
        "hf_name": "fancyzhx/ag_news",
        "text_key": "text",
        "label_key": "label",
        "num_classes": 4,
    },
}


def _load_text_dataset(cfg: DatasetConfig, seed_cfg: SeedConfig) -> dict[str, Any]:
    """Full pipeline for a text dataset via HuggingFace ``datasets``."""

    hf_cfg = _HF_DATASET_CONFIGS[cfg.name]
    raw = _hf_datasets.load_dataset(hf_cfg["hf_name"])

    # We use the standard HuggingFace train/test split
    all_texts: list[str] = raw["train"][hf_cfg["text_key"]]
    all_labels: list[int] = raw["train"][hf_cfg["label_key"]]
    test_texts: list[str] = raw["test"][hf_cfg["text_key"]]
    test_labels: list[int] = raw["test"][hf_cfg["label_key"]]

    # Stratified split of the HuggingFace train set into train+val
    all_indices = list(range(len(all_texts)))
    train_idx, val_idx, _ = _stratified_split(
        all_indices,
        all_labels,
        train_frac=cfg.train_split,
        val_frac=cfg.val_split / (cfg.train_split + cfg.val_split),
        seed=seed_cfg.global_seed,
    )

    train_idx = _subsample(train_idx, cfg.max_samples, seed_cfg.global_seed)
    val_idx = _subsample(val_idx, cfg.max_samples, seed_cfg.global_seed)
    test_idx = _subsample(list(range(len(test_texts))), cfg.max_samples, seed_cfg.global_seed)

    train_texts = [all_texts[i] for i in train_idx]
    train_labels_split = [all_labels[i] for i in train_idx]
    val_texts = [all_texts[i] for i in val_idx]
    val_labels_split = [all_labels[i] for i in val_idx]
    test_texts_split = [test_texts[i] for i in test_idx]
    test_labels_split = [test_labels[i] for i in test_idx]

    # Build vocabulary / tokenizer
    tokenizer = _get_text_tokenizer(cfg.name, cfg.vocab_size)
    if tokenizer is None:
        tokenizer = _get_hf_tokenizer("bert-base-uncased")
    if hasattr(tokenizer, "build_vocab"):
        tokenizer.build_vocab(train_texts)

    train_ds = _TextClassificationDataset(
        train_texts, train_labels_split, tokenizer, cfg.max_seq_length,
    )
    val_ds = _TextClassificationDataset(
        val_texts, val_labels_split, tokenizer, cfg.max_seq_length,
    )
    test_ds = _TextClassificationDataset(
        test_texts_split, test_labels_split, tokenizer, cfg.max_seq_length,
    )

    return {
        "train": train_ds,
        "val": val_ds,
        "test": test_ds,
        "train_labels": train_labels_split,
        "val_labels": val_labels_split,
        "test_labels": test_labels_split,
        "tokenizer": tokenizer,
        "cfg": cfg,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

IMAGE_DATASETS = {"mnist", "cifar10"}
TEXT_DATASETS = {"imdb", "ag_news"}


@dataclass
class DatasetBundle:
    """Container returned by :func:`load_dataset`."""
    name: str
    train: Dataset
    val: Dataset
    test: Dataset
    train_labels: list[int]
    val_labels: list[int]
    test_labels: list[int]
    cfg: DatasetConfig
    tokenizer: Any = None
    forget: Dataset | None = None
    retain: Dataset | None = None
    forget_labels: list[int] = field(default_factory=list)
    retain_labels: list[int] = field(default_factory=list)


def load_dataset(
    cfg: DatasetConfig,
    seed_cfg: SeedConfig | None = None,
) -> DatasetBundle:
    """Load a dataset according to *cfg* and return a :class:`DatasetBundle`.

    Parameters
    ----------
    cfg:
        Dataset-specific configuration (name, splits, preprocessing, etc.).
    seed_cfg:
        Seed configuration for deterministic subsampling / splitting.
        Defaults to global ``SeedConfig()``.
    """
    if seed_cfg is None:
        seed_cfg = SeedConfig()

    if cfg.name in IMAGE_DATASETS:
        result = _load_image_dataset(cfg, seed_cfg)
    elif cfg.name in TEXT_DATASETS:
        result = _load_text_dataset(cfg, seed_cfg)
    else:
        raise ValueError(f"Unsupported dataset: {cfg.name!r}. Choose from {IMAGE_DATASETS | TEXT_DATASETS}.")

    return DatasetBundle(
        name=cfg.name,
        train=result["train"],
        val=result["val"],
        test=result["test"],
        train_labels=result["train_labels"],
        val_labels=result["val_labels"],
        test_labels=result["test_labels"],
        cfg=cfg,
        tokenizer=result.get("tokenizer"),
    )


def create_forget_set(
    bundle: DatasetBundle,
    forget_ratio: float,
    seed: int = 42,
) -> DatasetBundle:
    """Partition ``bundle.train`` into *retain* and *forget* subsets.

    After this call ``bundle.retain`` and ``bundle.forget`` are populated
    and ``bundle.train`` is replaced with only the retain portion so that
    downstream training loops see only the retained data.
    """
    n_total = len(bundle.train)
    n_forget = max(1, int(n_total * forget_ratio))
    rng = _seed_generator(seed)
    forget_indices = sorted(rng.sample(range(n_total), n_forget))
    forget_set = {i for i in forget_indices}

    retain_indices = [i for i in range(n_total) if i not in forget_set]

    # Build forget / retain subsets from the underlying wrapped dataset
    base_dataset = bundle.train
    forget_labels = [bundle.train_labels[i] for i in forget_indices]
    retain_labels = [bundle.train_labels[i] for i in retain_indices]

    forget_subset = Subset(base_dataset, forget_indices)
    retain_subset = Subset(base_dataset, retain_indices)

    bundle.forget = forget_subset
    bundle.retain = retain_subset
    bundle.forget_labels = forget_labels
    bundle.retain_labels = retain_labels

    # Replace train with retain so that training loops only see retained data
    bundle.train = retain_subset
    bundle.train_labels = retain_labels

    logger.info(
        "Forget set created: %d / %d samples (%.1f%%) for '%s'",
        n_forget, n_total, forget_ratio * 100, bundle.name,
    )
    return bundle


# ---------------------------------------------------------------------------
# DataLoader helpers
# ---------------------------------------------------------------------------

def _text_collate_fn(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    """Stack dicts returned by :class:`_TextClassificationDataset`."""
    keys = batch[0].keys()
    return {k: torch.stack([b[k] for b in batch]) for k in keys}


def make_dataloader(
    dataset: Dataset,
    *,
    batch_size: int = 128,
    shuffle: bool = True,
    num_workers: int = NUM_WORKERS,
    drop_last: bool = False,
) -> DataLoader:
    """Create a :class:`DataLoader` with appropriate collation."""
    # Detect text datasets (they return dicts)
    sample = dataset[0] if len(dataset) > 0 else None
    collate = _text_collate_fn if isinstance(sample, dict) else None

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        collate_fn=collate,
        drop_last=drop_last,
        pin_memory=torch.cuda.is_available(),
    )


# ---------------------------------------------------------------------------
# Data statistics reporting
# ---------------------------------------------------------------------------

def report_statistics(bundle: DatasetBundle) -> dict[str, Any]:
    """Return a structured report of dataset statistics across all splits."""
    report: dict[str, Any] = {
        "dataset": bundle.name,
        "splits": {},
        "total_samples": 0,
    }
    for split_name, labels in [
        ("train", bundle.train_labels),
        ("val", bundle.val_labels),
        ("test", bundle.test_labels),
    ]:
        n = len(labels)
        dist = Counter(labels)
        report["splits"][split_name] = {
            "n_samples": n,
            "num_classes": len(dist),
            "class_distribution": dict(sorted(dist.items())),
            "class_balance": {k: round(v / n, 4) for k, v in sorted(dist.items())} if n > 0 else {},
        }
        report["total_samples"] += n

    if bundle.forget is not None:
        n_forget = len(bundle.forget)
        n_retain = len(bundle.retain)
        report["splits"]["forget"] = {
            "n_samples": n_forget,
            "num_classes": len(Counter(bundle.forget_labels)),
            "class_distribution": dict(sorted(Counter(bundle.forget_labels).items())),
            "class_balance": {
                k: round(v / n_forget, 4)
                for k, v in sorted(Counter(bundle.forget_labels).items())
            } if n_forget > 0 else {},
        }
        report["splits"]["retain"] = {
            "n_samples": n_retain,
            "num_classes": len(Counter(bundle.retain_labels)),
            "class_distribution": dict(sorted(Counter(bundle.retain_labels).items())),
            "class_balance": {
                k: round(v / n_retain, 4)
                for k, v in sorted(Counter(bundle.retain_labels).items())
            } if n_retain > 0 else {},
        }
        report["total_samples"] += n_forget  # retain already counted via train replacement

    return report


def print_statistics(bundle: DatasetBundle) -> None:
    """Pretty-print the dataset statistics to stdout."""
    report = report_statistics(bundle)
    print(f"\n{'=' * 60}")
    print(f"  Dataset: {report['dataset']}")
    print(f"  Total samples (train+val+test): {report['total_samples']}")
    print(f"{'=' * 60}")
    for split_name, info in report["splits"].items():
        print(f"\n  [{split_name.upper()}]  n={info['n_samples']}  classes={info['num_classes']}")
        for cls_id, count in sorted(info["class_distribution"].items()):
            bar = "#" * max(1, int(info["class_balance"][cls_id] * 40))
            print(f"    class {cls_id}: {count:>6d}  ({info['class_balance'][cls_id]:.1%})  {bar}")
    print()


# ---------------------------------------------------------------------------
# Convenience: load everything for a single dataset name
# ---------------------------------------------------------------------------

def load_by_name(
    name: str,
    *,
    seed_cfg: SeedConfig | None = None,
    max_samples: int | None = None,
    forget_ratio: float | None = None,
) -> DatasetBundle:
    """High-level helper that builds a :class:`DatasetConfig` on the fly.

    Parameters
    ----------
    name:
        One of ``"mnist"``, ``"cifar10"``, ``"imdb"``, ``"ag_news"``.
    seed_cfg:
        Global seed configuration.
    max_samples:
        Optional cap on the number of training / val / test samples.
    forget_ratio:
        If provided, partition training data into retain / forget sets.
    """
    defaults: dict[str, dict[str, Any]] = {
        "mnist": {
            "num_classes": 10, "input_shape": (1, 28, 28),
            "mean": (0.1307,), "std": (0.3081,),
        },
        "cifar10": {
            "num_classes": 10, "input_shape": (3, 32, 32),
            "mean": (0.4914, 0.4822, 0.4465), "std": (0.2023, 0.1994, 0.2010),
        },
        "imdb": {
            "num_classes": 2, "vocab_size": 30000, "max_seq_length": 512,
            "input_shape": (512,),
        },
        "ag_news": {
            "num_classes": 4, "vocab_size": 30000, "max_seq_length": 256,
            "input_shape": (256,),
        },
    }
    if name not in defaults:
        raise ValueError(f"Unknown dataset {name!r}; choose from {list(defaults)}")

    cfg = DatasetConfig(name=name, max_samples=max_samples, **defaults[name])
    if seed_cfg is None:
        seed_cfg = SeedConfig()

    bundle = load_dataset(cfg, seed_cfg)
    if forget_ratio is not None:
        create_forget_set(bundle, forget_ratio=forget_ratio, seed=seed_cfg.global_seed)

    print_statistics(bundle)
    return bundle
