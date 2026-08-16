"""Cryptographic building blocks.

- ``canonical_json``: deterministic serialization (sorted keys, compact) so
  hashes are stable across runs and languages.
- ``MerkleTree``: SHA-256 Merkle tree over leaf hashes. Deleted records are
  replaced by *tombstone leaves* (hash of record id + deletion marker), so the
  post-deletion root provably excludes the data while still covering the
  dataset namespace.
- ``hash_chain``: links successive audit events.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def leaf_hash(record_id: str, content_hash: str, *, deleted: bool = False) -> str:
    """Hash of a dataset record leaf.

    ``content_hash`` is the SHA-256 of the record's canonical JSON. When a
    record is deleted its leaf becomes a tombstone so the Merkle root changes
    in a way that is independently recomputable from the tombstone hash.
    """
    payload = canonical_json(
        {
            "record_id": record_id,
            "content_hash": content_hash,
            "state": "deleted" if deleted else "active",
        }
    )
    return sha256_hex(payload)


def tombstone_hash(record_id: str, content_hash: str) -> str:
    """Deterministic tombstone hash recorded at deletion time."""
    return sha256_hex(canonical_json({"record_id": record_id, "deleted": True, "of": content_hash}))


class MerkleTree:
    """SHA-256 binary Merkle tree over a list of leaf hashes.

    Leaves are sorted before hashing so the root is independent of insertion
    order (important for reproducible roots across shard retraining).
    """

    def __init__(self, leaves: list[str]) -> None:
        self.leaves: list[str] = sorted(set(leaves))
        self.levels: list[list[str]] = self._build(self.leaves)

    @staticmethod
    def _hash_pair(left: str, right: str) -> str:
        return sha256_hex(left + right)

    def _build(self, leaves: list[str]) -> list[list[str]]:
        level = list(leaves)
        levels = [level]
        while len(level) > 1:
            next_level: list[str] = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left  # duplicate odd leaf
                next_level.append(self._hash_pair(left, right))
            level = next_level
            levels.append(level)
        return levels

    @property
    def root(self) -> str:
        return self.levels[-1][0] if self.levels else sha256_hex("empty-tree")

    def proof(self, leaf: str) -> list[dict[str, str]]:
        """Merkle proof for ``leaf``: list of {hash, side} siblings."""
        if leaf not in self.leaves:
            raise ValueError("Leaf not present in tree")
        proof: list[dict[str, str]] = []
        index = self.leaves.index(leaf)
        for level in self.levels[:-1]:
            sibling_index = index ^ 1
            if sibling_index < len(level):
                sibling = level[sibling_index]
                proof.append({"hash": sibling, "side": "right" if index % 2 == 0 else "left"})
            index //= 2
        return proof

    @staticmethod
    def verify(root: str, leaf: str, proof: list[dict[str, str]]) -> bool:
        current = leaf
        for item in proof:
            current = MerkleTree._hash_pair(current, item["hash"]) if item["side"] == "right" else MerkleTree._hash_pair(item["hash"], current)
        return current == root


def hash_chain_link(prev_hash: str | None, event_type: str, payload: dict[str, Any], nonce: str) -> str:
    """Hash of an audit event given the previous event hash (chain link)."""
    return sha256_hex(canonical_json({"prev": prev_hash, "type": event_type, "payload": payload, "nonce": nonce}))
