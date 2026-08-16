from __future__ import annotations

import pytest

from app.core.security import aes_decrypt, aes_encrypt, sign_sha256, verify_sha256
from app.services.crypto import MerkleTree, canonical_json, leaf_hash, sha256_hex, tombstone_hash


def test_canonical_json_is_deterministic():
    a = canonical_json({"b": 1, "a": [3, 2], "n": None})
    b = canonical_json({"a": [3, 2], "b": 1, "n": None})
    assert a == b


def test_sha256_length():
    assert len(sha256_hex("hello")) == 64
    assert sha256_hex(b"hello") == sha256_hex("hello")


def test_merkle_tree_root_is_order_independent():
    leaves = ["a", "b", "c", "d"]
    t1 = MerkleTree(leaves)
    t2 = MerkleTree(list(reversed(leaves)))
    assert t1.root == t2.root


def test_merkle_proof_verifies():
    leaves = [f"leaf-{i}" for i in range(8)]
    tree = MerkleTree(leaves)
    for leaf in leaves:
        proof = tree.proof(leaf)
        assert MerkleTree.verify(tree.root, leaf, proof)
        # Tampering with any sibling must fail verification.
        bad = proof.copy()
        bad[0] = {"hash": "deadbeef", "side": bad[0]["side"]}
        assert not MerkleTree.verify(tree.root, leaf, bad)


def test_merkle_root_changes_when_record_deleted():
    """Tombstoning a record must change the root."""
    records = [("r1", "h1"), ("r2", "h2"), ("r3", "h3")]
    active_leaves = [leaf_hash(rid, ch) for rid, ch in records]
    deleted_leaves = [leaf_hash(rid, ch, deleted=True) for rid, ch in records]
    assert MerkleTree(active_leaves).root != MerkleTree(deleted_leaves).root


def test_tombstone_hash_is_deterministic():
    a = tombstone_hash("r1", "h1")
    b = tombstone_hash("r1", "h1")
    assert a == b
    assert a != tombstone_hash("r1", "h2")


def test_aes_roundtrip():
    cipher = aes_encrypt("sensitive-identity")
    assert cipher != "sensitive-identity"
    assert aes_decrypt(cipher) == "sensitive-identity"


def test_signature_roundtrip():
    msg = b"certificate-content"
    sig = sign_sha256(msg)
    assert verify_sha256(msg, sig)
    assert not verify_sha256(b"tampered", sig)
