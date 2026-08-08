"""Cryptographic proof and privacy evaluation endpoints."""

import hashlib

from fastapi import APIRouter

from api import deps
from api.schemas import (
    MIARequest,
    ProofRequest,
    VerificationRequest,
    ZKProofRequest,
    ZKVerifyRequest,
)
from unlearning.algorithms.base import UnlearningContext
from verification.merkle_tree import MerkleTree

router = APIRouter()


def _stable_seed(key: str) -> int:
    """Deterministic seed derived from ``key``.

    The builtin ``hash()`` is salted per-process (PYTHONHASHSEED), which made
    MIA/privacy evaluations non-reproducible across workers and restarts.
    SHA-256 gives the same seed for the same key on every run.
    """
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)


@router.post("/proof/generate")
async def generate_proof(request: ProofRequest):
    tree = MerkleTree()
    tree.add_leaves(request.deletion_steps)
    root = tree.build_tree()

    private_key, public_key = deps.sig_manager.generate_key_pair()
    signature = deps.sig_manager.sign(root, private_key)

    return {
        "merkle_root": root,
        "merkle_tree": tree.to_dict(),
        "signature_hex": signature,
        "algorithm": request.algorithm,
        "public_key_pem": deps.sig_manager.serialize_public_key(public_key),
        "leaf_count": len(request.deletion_steps),
        "tree_depth": len(tree.tree),
    }


@router.post("/proof/verify")
async def verify_proof(request: VerificationRequest):
    public_key = deps.sig_manager.load_public_key(request.public_key_pem)
    is_valid = deps.sig_manager.verify(
        request.message, request.signature_hex, public_key
    )
    return {"is_valid": is_valid, "algorithm": "ed25519"}


@router.post("/evaluate/mia")
async def evaluate_mia(request: MIARequest):
    from security.attacks.membership_inference import LossBasedMIA, MembershipInferenceAttack
    from training.data import generate_synthetic_data
    from unlearning.algorithms.sisa import SISAUnlearning

    target_ids = set(request.target_data_ids) if request.target_data_ids else set()
    data_size = max(request.data_size, 100)

    dataset = generate_synthetic_data(
        num_samples=data_size,
        seed=_stable_seed(request.model_name + "_mia"),
    )
    unlearned = (
        dataset.get_by_ids(target_ids) if target_ids else dataset.get_subset(list(range(5)))
    )
    split = dataset.size // 2
    member = dataset.get_subset(list(range(1, split)))
    nonmember = dataset.get_subset(list(range(split, dataset.size)))

    ctx = UnlearningContext(
        target_data_ids=list(target_ids) if target_ids else ["data_000000"],
        model_name=request.model_name if request.model_name else "mia_model",
        data_size=data_size,
        config=request.config,
    )

    algo = SISAUnlearning(num_shards=4)
    await algo.unlearn(ctx)
    model = algo.model

    conf_mia = MembershipInferenceAttack()
    conf_result = conf_mia.attack(
        model,
        unlearned.features if unlearned.size > 0 else member.features,
        member.features,
        nonmember.features,
    )

    loss_mia = LossBasedMIA()
    loss_result = loss_mia.attack(
        model,
        unlearned if unlearned.size > 0 else member,
        member,
        nonmember,
    )

    return {
        "model_name": request.model_name,
        "confidence_based_mia": conf_result,
        "loss_based_mia": loss_result,
    }


@router.post("/evaluate/privacy")
async def evaluate_privacy(request: MIARequest):
    from training.data import generate_synthetic_data
    from unlearning.algorithms.sisa import SISAUnlearning

    target_ids = set(request.target_data_ids) if request.target_data_ids else set()
    data_size = max(request.data_size, 100)

    original = generate_synthetic_data(
        num_samples=data_size,
        seed=_stable_seed(request.model_name + "_priv"),
    )

    ctx = UnlearningContext(
        target_data_ids=list(target_ids) if target_ids else ["data_000000"],
        model_name=request.model_name if request.model_name else "priv_model",
        data_size=data_size,
        config=request.config,
    )

    algo = SISAUnlearning(num_shards=4)
    await algo.unlearn(ctx)

    retained = original.remove_by_ids(target_ids) if target_ids else original
    model = algo.model

    report = deps.privacy_evaluator.evaluate(
        model=model,
        original_dataset=original,
        retained_dataset=retained,
        unlearned_ids=target_ids,
    )

    return report.to_dict()


@router.post("/proof/generate-zksnark")
async def generate_zksnark_proof(request: ZKProofRequest):
    from verification.zksnark_service import ZKProofService

    svc = ZKProofService(hash_algorithm=request.hash_algorithm)
    proof = svc.generate_proof(
        leaf_data=request.leaf_data,
        all_leaves=request.all_leaves,
    )
    result = proof.to_dict()
    result["proving_scheme"] = "SIMULATED"
    result["disclaimer"] = (
        "Hash-based simulation, NOT a real zero-knowledge proof. Do not use in production."
    )
    return result


@router.post("/proof/verify-zksnark")
async def verify_zksnark_proof(request: ZKVerifyRequest):
    from verification.zksnark_service import ZKProof, ZKProofService, ZKVerificationKey

    pdata = request.proof
    vk_data = pdata.get("verification_key", {})
    vk = ZKVerificationKey(
        merkle_root=vk_data.get("merkle_root", ""),
        hash_function=vk_data.get("hash_function", "sha3_256"),
        tree_depth=vk_data.get("tree_depth", 0),
        curve=vk_data.get("curve", "bn254"),
        public_key_pem=vk_data.get("public_key_pem", ""),
    )
    proof_obj = ZKProof(
        circuit_type=pdata.get("circuit_type", "merkle_inclusion"),
        protocol=pdata.get("protocol", "groth16"),
        curve=pdata.get("curve", "bn254"),
        proof_data=pdata.get("proof", {}),
        public_inputs=pdata.get("public_inputs", []),
        verification_key=vk,
    )
    svc = ZKProofService(hash_algorithm=vk.hash_function)
    is_valid = svc.verify_proof(proof_obj)
    return {
        "is_valid": is_valid,
        "algorithm": "groth16",
        "curve": "bn254",
        "circuit_type": pdata.get("circuit_type", "merkle_inclusion"),
        "proving_scheme": "SIMULATED",
        "disclaimer": "Hash-based simulation, NOT a real zero-knowledge proof.",
    }
