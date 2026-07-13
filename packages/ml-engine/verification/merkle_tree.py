import hashlib
import json
from typing import Any, Optional


class MerkleTree:
    """Merkle tree implementation for verifiable deletion proofs."""

    def __init__(self, hash_algorithm: str = "sha256") -> None:
        self.hash_func = getattr(hashlib, hash_algorithm, hashlib.sha256)
        self.leaves: list[str] = []
        self.tree: list[list[str]] = []
        self.root: Optional[str] = None

    def add_leaf(self, data: str) -> None:
        leaf_hash = self._hash(data)
        self.leaves.append(leaf_hash)

    def add_leaves(self, data_list: list[str]) -> None:
        for data in data_list:
            self.add_leaf(data)

    def build_tree(self) -> str:
        if not self.leaves:
            self.root = self._hash("")
            return self.root

        current_level = self.leaves.copy()
        self.tree = [current_level]

        while len(current_level) > 1:
            next_level: list[str] = []
            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    combined = current_level[i] + current_level[i + 1]
                else:
                    combined = current_level[i] + current_level[i]
                next_level.append(self._hash(combined))
            self.tree.append(next_level)
            current_level = next_level

        self.root = current_level[0]
        return self.root

    def get_proof(self, leaf_index: int) -> list[dict[str, str]]:
        """Generate a Merkle proof for a specific leaf."""
        if not self.tree:
            raise ValueError("Tree not built. Call build_tree() first.")
        if leaf_index < 0 or leaf_index >= len(self.leaves):
            raise IndexError("Leaf index out of range.")

        proof: list[dict[str, str]] = []
        current_index = leaf_index

        for level in range(len(self.tree) - 1):
            is_right_node = current_index % 2 == 1
            sibling_index = current_index - 1 if is_right_node else current_index + 1

            if sibling_index < len(self.tree[level]):
                proof.append({
                    "position": "left" if is_right_node else "right",
                    "hash": self.tree[level][sibling_index],
                })

            current_index //= 2

        return proof

    def verify_proof(
        self,
        leaf_data: str,
        proof: list[dict[str, str]],
        root: str,
    ) -> bool:
        """Verify a Merkle proof against a root hash."""
        current_hash = self._hash(leaf_data)

        for node in proof:
            if node["position"] == "left":
                current_hash = self._hash(node["hash"] + current_hash)
            else:
                current_hash = self._hash(current_hash + node["hash"])

        return current_hash == root

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "depth": len(self.tree),
            "leaf_count": len(self.leaves),
            "leaves": [l[:16] + "..." for l in self.leaves],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @staticmethod
    def verify_merkle_root(
        leaves: list[str], expected_root: str, hash_func: str = "sha256"
    ) -> bool:
        tree = MerkleTree(hash_func)
        tree.add_leaves(leaves)
        computed_root = tree.build_tree()
        return computed_root == expected_root

    @classmethod
    def from_leaves(
        cls, leaves: list[str], hash_algorithm: str = "sha256"
    ) -> "MerkleTree":
        tree = cls(hash_algorithm)
        tree.add_leaves(leaves)
        tree.build_tree()
        return tree

    def _hash(self, data: str) -> str:
        return self.hash_func(data.encode("utf-8")).hexdigest()
