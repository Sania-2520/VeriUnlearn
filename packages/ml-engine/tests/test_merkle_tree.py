import pytest
from verification.merkle_tree import MerkleTree


class TestMerkleTree:
    def test_empty_tree(self):
        tree = MerkleTree()
        root = tree.build_tree()
        assert root is not None
        assert len(root) == 64

    def test_single_leaf(self):
        tree = MerkleTree()
        tree.add_leaf("data1")
        root = tree.build_tree()
        assert root is not None
        assert len(root) == 64

    def test_multiple_leaves(self):
        tree = MerkleTree()
        leaves = ["data1", "data2", "data3", "data4"]
        tree.add_leaves(leaves)
        root = tree.build_tree()
        assert root is not None
        assert len(root) == 64

    def test_proof_generation_and_verification(self):
        tree = MerkleTree()
        leaves = ["data1", "data2", "data3", "data4"]
        tree.add_leaves(leaves)
        root = tree.build_tree()

        proof = tree.get_proof(0)
        assert len(proof) > 0

        is_valid = tree.verify_proof("data1", proof, root)
        assert is_valid

    def test_proof_rejects_wrong_data(self):
        tree = MerkleTree()
        leaves = ["data1", "data2", "data3", "data4"]
        tree.add_leaves(leaves)
        root = tree.build_tree()

        proof = tree.get_proof(0)
        is_valid = tree.verify_proof("wrong_data", proof, root)
        assert not is_valid

    def test_static_verify_method(self):
        leaves = ["a", "b", "c", "d"]
        tree = MerkleTree()
        tree.add_leaves(leaves)
        root = tree.build_tree()
        assert MerkleTree.verify_merkle_root(leaves, root)

    def test_consistency(self):
        tree1 = MerkleTree.from_leaves(["a", "b", "c"])
        tree2 = MerkleTree.from_leaves(["a", "b", "c"])
        assert tree1.root == tree2.root

    def test_different_leaves_different_root(self):
        tree1 = MerkleTree.from_leaves(["a", "b", "c"])
        tree2 = MerkleTree.from_leaves(["x", "y", "z"])
        assert tree1.root != tree2.root

    def test_to_dict(self):
        tree = MerkleTree.from_leaves(["a", "b", "c"])
        data = tree.to_dict()
        assert "root" in data
        assert "depth" in data
        assert "leaf_count" in data
        assert data["leaf_count"] == 3
