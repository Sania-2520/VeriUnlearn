"""
Simulated zk-SNARK proof service for development and testing.

This module provides a hash-based simulation of zk-SNARK proof generation and
verification. It uses SHA-256 hashing and Ed25519 signatures instead of actual
zero-knowledge elliptic curve arithmetic (Groth16, PLONK, etc.). The classes
ZKProvingKey, ZKVerificationKey, and ZKProofService are placeholder types that
imply a full circuit-based system was planned but not yet realized.

SECURITY NOTE: This implementation provides NO cryptographic zero-knowledge
guarantees. It is suitable for integration testing and development workflows
only. For production use, replace with a real zk-SNARK library (e.g., snarkjs,
py_ecc, circom) or integrate with a cloud HSM/attestation service.
"""

import hashlib
import json
from typing import Any, Optional

from verification.merkle_tree import MerkleTree
from verification.signatures import SignatureManager


__all__ = [
    "ZKProofService",
    "ZKProofError",
    "ZKProof",
    "ZKVerificationKey",
    "ZKProvingKey",
]


class ZKProofError(Exception):
    pass


class ZKProvingKey:
    def __init__(
        self,
        hash_function: str = "sha3_256",
        tree_depth: int = 0,
        curve: str = "bn254",
    ) -> None:
        self.hash_function = hash_function
        self.tree_depth = tree_depth
        self.curve = curve
        raw = f"{hash_function}:{tree_depth}:{curve}".encode()
        self.key_id = hashlib.sha256(raw).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_type": "proving_key",
            "hash_function": self.hash_function,
            "tree_depth": self.tree_depth,
            "curve": self.curve,
            "key_id": self.key_id,
        }


class ZKVerificationKey:
    def __init__(
        self,
        merkle_root: str = "",
        hash_function: str = "sha3_256",
        tree_depth: int = 0,
        curve: str = "bn254",
        public_key_pem: str = "",
    ) -> None:
        self.merkle_root = merkle_root
        self.hash_function = hash_function
        self.tree_depth = tree_depth
        self.curve = curve
        self.public_key_pem = public_key_pem
        raw = f"{merkle_root}:{hash_function}:{curve}:{tree_depth}".encode()
        self.key_id = hashlib.sha256(raw).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_type": "verification_key",
            "hash_function": self.hash_function,
            "tree_depth": self.tree_depth,
            "curve": self.curve,
            "merkle_root": self.merkle_root,
            "key_id": self.key_id,
            "public_key_pem": self.public_key_pem,
        }


class ZKProof:
    def __init__(
        self,
        circuit_type: str = "merkle_inclusion",
        protocol: str = "groth16",
        curve: str = "bn254",
        proof_data: Optional[dict[str, Any]] = None,
        public_inputs: Optional[list[str]] = None,
        verification_key: Optional[ZKVerificationKey] = None,
    ) -> None:
        self.circuit_type = circuit_type
        self.protocol = protocol
        self.curve = curve
        self.proof_data = proof_data or {}
        self.public_inputs = public_inputs or []
        self.verification_key = verification_key

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "circuit_type": self.circuit_type,
            "protocol": self.protocol,
            "curve": self.curve,
            "proof": self.proof_data,
            "public_inputs": self.public_inputs,
        }
        if self.verification_key:
            d["verification_key"] = self.verification_key.to_dict()
        return d


class ZKProofService:
    def __init__(self, hash_algorithm: str = "sha3_256") -> None:
        self.hash_algorithm = hash_algorithm
        self.sig_manager = SignatureManager()

    def _hash(self, data: str) -> str:
        try:
            h = hashlib.new(self.hash_algorithm, data.encode("utf-8"))
        except ValueError:
            h = hashlib.sha256(data.encode("utf-8"))
        return h.hexdigest()

    def generate_proof(
        self,
        leaf_data: str,
        all_leaves: Optional[list[str]] = None,
        tree: Optional[MerkleTree] = None,
        leaf_index: Optional[int] = None,
    ) -> ZKProof:
        if tree is None:
            if all_leaves is None:
                raise ZKProofError("Either tree or all_leaves must be provided")
            tree = MerkleTree(hash_algorithm=self.hash_algorithm)
            tree.add_leaves(all_leaves)
            tree.build_tree()

        if tree.root is None:
            raise ZKProofError("Tree has no root. Build tree first.")

        if leaf_index is None:
            try:
                target_hash = self._hash(leaf_data)
                leaf_index = tree.leaves.index(target_hash)
            except ValueError:
                raise ZKProofError("leaf_data not found in tree leaves")

        sibling_path = tree.get_proof(leaf_index)

        leaf_hash = self._hash(leaf_data)
        private_key, public_key = self.sig_manager.generate_key_pair()
        root_hash = tree.root
        signature = self.sig_manager.sign(root_hash, private_key)

        proof_data = {
            "pi_a": [
                leaf_hash,
                signature,
            ],
            "pi_b": [[node["hash"] for node in sibling_path]],
            "pi_c": [
                self._hash(leaf_hash + root_hash),
            ],
            "sibling_path": sibling_path,
            "leaf_index": leaf_index,
            "leaf_count": len(tree.leaves),
            "tree_depth": len(tree.tree),
        }

        vk = ZKVerificationKey(
            merkle_root=root_hash,
            hash_function=self.hash_algorithm,
            tree_depth=len(tree.tree),
            curve="bn254",
            public_key_pem=self.sig_manager.serialize_public_key(public_key),
        )

        pk = ZKProvingKey(
            hash_function=self.hash_algorithm,
            tree_depth=len(tree.tree),
            curve="bn254",
        )

        public_inputs = [
            root_hash,
            leaf_hash,
            str(len(tree.tree)),
        ]

        proof = ZKProof(
            circuit_type="merkle_inclusion",
            protocol="groth16",
            curve="bn254",
            proof_data={
                **proof_data,
                "proving_key": pk.to_dict(),
            },
            public_inputs=public_inputs,
            verification_key=vk,
        )

        return proof

    def verify_proof(self, proof: ZKProof) -> bool:
        if proof.circuit_type != "merkle_inclusion":
            raise ZKProofError(f"Unsupported circuit type: {proof.circuit_type}")
        if not proof.verification_key:
            raise ZKProofError("Proof has no verification key")

        vk = proof.verification_key
        pd = proof.proof_data

        sibling_path = pd.get("sibling_path", [])
        pi_a = pd.get("pi_a", [])
        pi_c = pd.get("pi_c", [])

        if not pi_a or not pi_c:
            return False

        leaf_hash = pi_a[0]
        expected_root_hash = vk.merkle_root

        current_hash = leaf_hash
        for node in sibling_path:
            pos = node.get("position", "right")
            sibling_hash = node.get("hash", "")
            if pos == "left":
                current_hash = self._hash(sibling_hash + current_hash)
            else:
                current_hash = self._hash(current_hash + sibling_hash)

        merkle_valid = current_hash == expected_root_hash
        if not merkle_valid:
            return False

        expected_pi_c = self._hash(leaf_hash + expected_root_hash)
        if pi_c[0] != expected_pi_c:
            return False

        signature = pi_a[1]
        try:
            pub_key = self.sig_manager.load_public_key(vk.public_key_pem)
            sig_valid = self.sig_manager.verify(expected_root_hash, signature, pub_key)
        except Exception:
            sig_valid = False

        if not sig_valid:
            return False

        return True

    def generate_and_verify(
        self,
        leaf_data: str,
        all_leaves: list[str],
    ) -> tuple[ZKProof, bool]:
        proof = self.generate_proof(leaf_data, all_leaves=all_leaves)
        is_valid = self.verify_proof(proof)
        return proof, is_valid
