import pytest

from verification.merkle_tree import MerkleTree
from verification.zksnark_service import (
    ZKProof,
    ZKProofError,
    ZKProofService,
    ZKProvingKey,
    ZKVerificationKey,
)


class TestZKProvingKey:
    def test_to_dict_contains_key_fields(self):
        pk = ZKProvingKey(hash_function="sha3_256", tree_depth=4, curve="bn254")
        d = pk.to_dict()
        assert d["key_type"] == "proving_key"
        assert d["hash_function"] == "sha3_256"
        assert d["tree_depth"] == 4
        assert d["curve"] == "bn254"
        assert len(d["key_id"]) == 16

    def test_different_configs_different_key_ids(self):
        pk1 = ZKProvingKey(hash_function="sha256", tree_depth=4, curve="bn254")
        pk2 = ZKProvingKey(hash_function="sha3_256", tree_depth=4, curve="bn254")
        assert pk1.key_id != pk2.key_id


class TestZKVerificationKey:
    def test_to_dict_contains_merkle_root(self):
        vk = ZKVerificationKey(
            merkle_root="abc123",
            hash_function="sha3_256",
            tree_depth=4,
            curve="bn254",
            public_key_pem="pem_data",
        )
        d = vk.to_dict()
        assert d["merkle_root"] == "abc123"
        assert d["key_type"] == "verification_key"
        assert d["public_key_pem"] == "pem_data"

    def test_different_roots_different_key_ids(self):
        vk1 = ZKVerificationKey(merkle_root="root1")
        vk2 = ZKVerificationKey(merkle_root="root2")
        assert vk1.key_id != vk2.key_id


class TestZKProofService:
    def test_generate_proof_returns_proof_object(self):
        svc = ZKProofService(hash_algorithm="sha256")
        leaves = ["data_a", "data_b", "data_c", "data_d"]
        proof = svc.generate_proof("data_a", all_leaves=leaves)
        assert isinstance(proof, ZKProof)
        assert proof.circuit_type == "merkle_inclusion"
        assert proof.protocol == "groth16"
        assert proof.curve == "bn254"
        assert proof.verification_key is not None

    def test_generate_proof_sets_public_inputs(self):
        svc = ZKProofService(hash_algorithm="sha256")
        leaves = ["x", "y", "z"]
        proof = svc.generate_proof("y", all_leaves=leaves)
        assert len(proof.public_inputs) == 3
        assert proof.verification_key is not None
        assert proof.verification_key.merkle_root != ""

    def test_generate_proof_proof_data_contains_pi_a_pi_b_pi_c(self):
        svc = ZKProofService(hash_algorithm="sha256")
        leaves = ["a", "b", "c", "d", "e"]
        proof = svc.generate_proof("c", all_leaves=leaves)
        pd = proof.proof_data
        assert "pi_a" in pd
        assert "pi_b" in pd
        assert "pi_c" in pd
        assert "sibling_path" in pd
        assert len(pd["pi_a"]) == 2
        assert isinstance(pd["pi_a"][0], str)
        assert isinstance(pd["pi_a"][1], str)

    def test_verify_proof_valid_returns_true(self):
        svc = ZKProofService(hash_algorithm="sha256")
        leaves = ["alice", "bob", "charlie", "diana"]
        proof = svc.generate_proof("bob", all_leaves=leaves)
        is_valid = svc.verify_proof(proof)
        assert is_valid is True

    def test_verify_proof_tampered_leaf_returns_false(self):
        svc = ZKProofService(hash_algorithm="sha256")
        leaves = ["alice", "bob", "charlie"]
        proof = svc.generate_proof("alice", all_leaves=leaves)
        proof.proof_data["pi_a"][0] = svc._hash("tampered_data")
        is_valid = svc.verify_proof(proof)
        assert is_valid is False

    def test_verify_proof_tampered_sibling_path_returns_false(self):
        svc = ZKProofService(hash_algorithm="sha256")
        leaves = ["a", "b", "c", "d"]
        proof = svc.generate_proof("a", all_leaves=leaves)
        proof.proof_data["sibling_path"][0]["hash"] = "0" * 64
        is_valid = svc.verify_proof(proof)
        assert is_valid is False

    def test_generate_and_verify_roundtrip(self):
        svc = ZKProofService()
        leaves = ["data_1", "data_2", "data_3", "data_4", "data_5"]
        proof, is_valid = svc.generate_and_verify("data_3", all_leaves=leaves)
        assert is_valid is True

    def test_multiple_leaves_and_indices(self):
        svc = ZKProofService(hash_algorithm="sha256")
        leaves = [f"record_{i}" for i in range(16)]
        for idx in range(0, 16, 3):
            proof = svc.generate_proof(leaves[idx], all_leaves=leaves)
            assert svc.verify_proof(proof) is True

    def test_verify_proof_single_leaf(self):
        svc = ZKProofService(hash_algorithm="sha256")
        proof = svc.generate_proof("only", all_leaves=["only"])
        assert svc.verify_proof(proof) is True

    def test_proof_includes_proving_key(self):
        svc = ZKProofService(hash_algorithm="sha256")
        proof = svc.generate_proof("x", all_leaves=["x", "y"])
        pd = proof.proof_data
        assert "proving_key" in pd
        assert pd["proving_key"]["key_type"] == "proving_key"

    def test_proof_serializes_to_dict(self):
        svc = ZKProofService(hash_algorithm="sha256")
        proof = svc.generate_proof("test", all_leaves=["test", "data"])
        d = proof.to_dict()
        assert d["circuit_type"] == "merkle_inclusion"
        assert d["protocol"] == "groth16"
        assert "proof" in d
        assert "public_inputs" in d
        assert "verification_key" in d
        assert d["verification_key"]["key_type"] == "verification_key"

    def test_generate_proof_missing_tree_raises(self):
        svc = ZKProofService()
        with pytest.raises(ZKProofError, match="Either tree or all_leaves"):
            svc.generate_proof("data")

    def test_generate_proof_missing_leaf_raises(self):
        svc = ZKProofService()
        with pytest.raises(ZKProofError, match="not found in tree leaves"):
            svc.generate_proof("unknown", all_leaves=["a", "b"])

    def test_verify_proof_wrong_circuit_type_raises(self):
        svc = ZKProofService()
        proof = ZKProof(circuit_type="invalid")
        with pytest.raises(ZKProofError, match="Unsupported circuit type"):
            svc.verify_proof(proof)

    def test_verify_proof_missing_vk_raises(self):
        svc = ZKProofService()
        proof = ZKProof(
            circuit_type="merkle_inclusion",
            proof_data={"pi_a": ["a", "b"], "pi_c": ["c"]},
        )
        with pytest.raises(ZKProofError, match="no verification key"):
            svc.verify_proof(proof)
