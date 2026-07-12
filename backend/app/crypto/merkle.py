from __future__ import annotations

import hashlib
from typing import Any


class MerkleNode:
    def __init__(self, hash_value: str, left: MerkleNode | None = None, right: MerkleNode | None = None):
        self.hash = hash_value
        self.left = left
        self.right = right


class MerkleTree:
    def __init__(self, leaves: list[str]):
        self.leaves = leaves
        self.root = self._build_tree(leaves)

    def _hash_pair(self, left: str, right: str) -> str:
        combined = (left + right).encode("utf-8")
        return hashlib.sha256(combined).hexdigest()

    def _build_tree(self, nodes: list[str]) -> str:
        if not nodes:
            return hashlib.sha256(b"empty").hexdigest()
        if len(nodes) == 1:
            return nodes[0]

        next_level: list[str] = []
        for i in range(0, len(nodes), 2):
            if i + 1 < len(nodes):
                next_level.append(self._hash_pair(nodes[i], nodes[i + 1]))
            else:
                next_level.append(self._hash_pair(nodes[i], nodes[i]))
        return self._build_tree(next_level)

    def get_proof(self, leaf: str) -> list[tuple[str, bool]]:
        return []

    def verify_proof(self, leaf: str, proof: list[tuple[str, bool]], root: str) -> bool:
        return False


class MerkleTreeBuilder:
    def build(self, data: Any) -> MerkleTree:
        import json

        if hasattr(data, "__table__"):
            record = {
                c.name: getattr(data, c.name)
                for c in data.__table__.columns
                if getattr(data, c.name) is not None
            }
            data_str = json.dumps(record, sort_keys=True, default=str)
        elif isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True, default=str)
        else:
            data_str = str(data)

        chunk_size = 64
        chunks = [data_str[i:i + chunk_size] for i in range(0, len(data_str), chunk_size)]

        leaves = [hashlib.sha256(c.encode()).hexdigest() for c in chunks]
        return MerkleTree(leaves)
