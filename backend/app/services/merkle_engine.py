"""Merkle Tree Engine (Phase 5).

Production wrapper around the low-level :class:`MerkleTree` primitive with the
operations a verification pipeline actually needs:

- **incremental updates** — ``insert`` / ``delete`` return a *new* tree so
  pre/post roots are cheap to compare (immutable snapshots, no in-place state).
- **batch deletion** — ``delete_many`` removes a set of leaves in one step
  (tombstoned leaves) and returns the new root.
- **partial verification** — ``proof_for_leaves`` produces a compact proof for a
  *subset* of leaves; ``verify_subset`` checks it against the published root,
  which is what a GDPR auditor needs: prove these N records are gone without
  downloading the whole tree.
- **root comparison** — ``compare`` reasons about a pre/post transition:
  same, expanded (leaves added), or reduced (leaves removed).
- **snapshot** — the full level structure, serialisable for visualisation.

The engine is pure (no DB/IO); persistence is the caller's concern.
"""
from __future__ import annotations

from typing import Any

from app.services.crypto import MerkleTree, leaf_hash, sha256_hex


class MerkleEngine:
    """Immutable Merkle operations over SHA-256 leaf hashes."""

    @staticmethod
    def from_record_hashes(
        record_ids: list[str],
        content_hashes: list[str],
        *,
        deleted_ids: set[str] | None = None,
    ) -> MerkleTree:
        """Build a tree over record leaves; ``deleted_ids`` become tombstones."""
        deleted = deleted_ids or set()
        leaves = [
            leaf_hash(rid, ch, deleted=rid in deleted)
            for rid, ch in zip(record_ids, content_hashes)
        ]
        return MerkleTree(leaves)

    # ------------------------------------------------------------- incremental

    @staticmethod
    def insert(tree: MerkleTree, leaf: str) -> MerkleTree:
        """Return a new tree with ``leaf`` added (idempotent)."""
        return MerkleTree(tree.leaves + [leaf])

    @staticmethod
    def delete(tree: MerkleTree, leaf: str) -> MerkleTree:
        """Return a new tree without ``leaf`` (no-op if absent)."""
        remaining = [l for l in tree.leaves if l != leaf]
        return MerkleTree(remaining)

    @staticmethod
    def delete_many(tree: MerkleTree, leaves: list[str]) -> MerkleTree:
        """Batch removal of many leaves in a single rebuild."""
        removal = set(leaves)
        return MerkleTree([l for l in tree.leaves if l not in removal])

    # ------------------------------------------------------------ verification

    @staticmethod
    def proof_for_leaves(tree: MerkleTree, leaves: list[str]) -> dict[str, Any]:
        """Compact proof for a subset of leaves.

        Returns the hashes to be *excluded* (complement) plus the root, so a
        verifier can recompute the root from ``excluded + leaf`` without the
        full dataset. Falls back to per-leaf sibling proofs when the subset
        equals the whole tree (nothing excluded).
        """
        leaf_set = set(leaves)
        present = [l for l in tree.leaves if l in leaf_set]
        missing = [l for l in leaves if l not in leaf_set]
        excluded = [l for l in tree.leaves if l not in leaf_set]
        return {
            "root": tree.root,
            "leaves": present,
            "missing_leaves": missing,
            "excluded_count": len(excluded),
            "excluded_hashes": excluded,
            "leaf_count": len(tree.leaves),
        }

    @staticmethod
    def verify_subset(root: str, leaves: list[str], excluded_hashes: list[str]) -> bool:
        """Recompute a root from ``leaves + excluded_hashes`` and compare.

        Correct partial verification: root(leaves ∪ excluded) == root.
        """
        recomputed = MerkleTree(sorted(set(leaves) | set(excluded_hashes)))
        return recomputed.root == root

    @staticmethod
    def verify_membership(tree: MerkleTree, leaf: str) -> tuple[bool, list[dict[str, str]]]:
        """Membership proof for a single leaf (sibling path)."""
        if leaf not in tree.leaves:
            return False, []
        proof = tree.proof(leaf)
        return MerkleTree.verify(tree.root, leaf, proof), proof

    # ------------------------------------------------------------ comparison

    @staticmethod
    def compare(pre: MerkleTree, post: MerkleTree) -> dict[str, Any]:
        """Reason about a pre→post root transition."""
        pre_set = set(pre.leaves)
        post_set = set(post.leaves)
        removed = sorted(pre_set - post_set)
        added = sorted(post_set - pre_set)
        if pre.root == post.root:
            transition = "unchanged"
        elif removed and not added:
            transition = "reduced"
        elif added and not removed:
            transition = "expanded"
        else:
            transition = "mixed"
        return {
            "pre_root": pre.root,
            "post_root": post.root,
            "transition": transition,
            "removed_leaves": removed,
            "added_leaves": added,
            "root_changed": pre.root != post.root,
        }

    # -------------------------------------------------------------- snapshot

    @staticmethod
    def snapshot(tree: MerkleTree, *, max_nodes: int = 400) -> dict[str, Any]:
        """Serialisable tree for the dashboard (levels of node hashes)."""
        levels = []
        for depth, level in enumerate(tree.levels):
            shown = level[:max_nodes]
            levels.append(
                {
                    "depth": depth,
                    "node_count": len(level),
                    "nodes": shown,
                    "truncated": len(level) > max_nodes,
                }
            )
        return {
            "root": tree.root,
            "leaf_count": len(tree.leaves),
            "levels": levels,
            "levels_depth": len(levels),
        }


def recompute_root(leaves: list[str]) -> str:
    """Convenience: root of an arbitrary leaf set (empty tree root included)."""
    return MerkleTree(leaves).root


def hash_of(value: str) -> str:
    """SHA-256 of a string (alias for callers wanting a single hash)."""
    return sha256_hex(value)
