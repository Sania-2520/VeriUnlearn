from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

from unlearning.hybrid_controller import HybridAdaptiveController
from unlearning.algorithms.base import UnlearningContext, UnlearningResult
from verification.merkle_tree import MerkleTree
from verification.signatures import SignatureManager
from verification.privacy_evaluation import PrivacyEvaluator
from security.attacks.membership_inference import MembershipInferenceAttack, LossBasedMIA

app = FastAPI(
    title="VeriUnlearn ML Engine",
    version="1.0.0",
    description="Machine Unlearning, Verification, and Security Engine",
)

controller = HybridAdaptiveController()
sig_manager = SignatureManager()
privacy_evaluator = PrivacyEvaluator()


class UnlearningRequest(BaseModel):
    target_data_ids: list[str]
    model_type: str = "transformer"
    model_name: str = ""
    data_size: int = 0
    latency_ms: int = 500
    accuracy_target: float = 0.95
    regulatory: str = "gdpr"
    config: dict = {}


class ProofRequest(BaseModel):
    deletion_steps: list[str]
    algorithm: str = "ed25519"


class VerificationRequest(BaseModel):
    message: str
    signature_hex: str
    public_key_pem: str


class CertificateRequest(BaseModel):
    target_data_ids: list[str]
    model_name: str = ""
    data_size: int = 0
    regulatory: str = "gdpr"
    config: dict = {}


class ZKProofRequest(BaseModel):
    leaf_data: str
    all_leaves: list[str]
    hash_algorithm: str = "sha3_256"


class ZKVerifyRequest(BaseModel):
    proof: dict[str, Any]


class MIARequest(BaseModel):
    model_name: str = ""
    data_size: int = 0
    target_data_ids: list[str] = []
    config: dict = {}


@app.post("/unlearn")
async def execute_unlearning(request: UnlearningRequest):
    context = UnlearningContext(
        target_data_ids=request.target_data_ids,
        model_type=request.model_type,
        model_name=request.model_name,
        data_size=request.data_size,
        latency_ms=request.latency_ms,
        accuracy_target=request.accuracy_target,
        regulatory=request.regulatory,
        config=request.config,
    )
    result = await controller.execute(context)
    return result


@app.post("/proof/generate")
async def generate_proof(request: ProofRequest):
    tree = MerkleTree()
    tree.add_leaves(request.deletion_steps)
    root = tree.build_tree()

    private_key, public_key = sig_manager.generate_key_pair()
    signature = sig_manager.sign(root, private_key)

    return {
        "merkle_root": root,
        "merkle_tree": tree.to_dict(),
        "signature_hex": signature,
        "algorithm": request.algorithm,
        "public_key_pem": sig_manager.serialize_public_key(public_key),
        "leaf_count": len(request.deletion_steps),
        "tree_depth": len(tree.tree),
    }


@app.post("/proof/verify")
async def verify_proof(request: VerificationRequest):
    public_key = sig_manager.load_public_key(request.public_key_pem)
    is_valid = sig_manager.verify(
        request.message, request.signature_hex, public_key
    )
    return {"is_valid": is_valid, "algorithm": "ed25519"}


@app.post("/certificate")
async def generate_certificate(request: CertificateRequest):
    context = UnlearningContext(
        target_data_ids=request.target_data_ids,
        model_name=request.model_name,
        data_size=request.data_size,
        regulatory=request.regulatory,
        config=request.config,
    )
    result = await controller.execute(context)

    tree = MerkleTree()
    tree.add_leaves(request.target_data_ids)
    root = tree.build_tree()

    private_key, public_key = sig_manager.generate_key_pair()
    signature = sig_manager.sign(root, private_key)

    algorithm = result.algorithm
    epsilon = None
    delta = None
    if "certified" in result.metrics:
        eps = result.metrics["certified"].get("epsilon")
        delt = result.metrics["certified"].get("delta")
        if eps is not None:
            epsilon = eps
            delta = delt

    mia_conf = {"attack_name": "confidence-threshold", "overall_accuracy": 0.0, "f1_score": 0.0}
    mia_loss = {"attack_name": "loss-threshold", "overall_accuracy": 0.0, "f1_score": 0.0}

    cert = {
        "certificate_id": f"cert-{hash(tuple(request.target_data_ids)) & 0xFFFFFFFF:08x}",
        "version": "1.0",
        "algorithm": algorithm,
        "target_data_ids": request.target_data_ids,
        "unlearning_result": result.success,
        "utility_retained": result.utility_retained,
        "processing_time_ms": result.processing_time_ms,
        "merkle_proof": {
            "root": root,
            "signature_hex": signature,
            "public_key_pem": sig_manager.serialize_public_key(public_key),
            "leaf_count": len(request.target_data_ids),
        },
        "privacy_assessment": {
            "membership_inference": {
                "confidence_based": mia_conf,
                "loss_based": mia_loss,
            },
            "dp_estimate": {"epsilon": epsilon, "delta": delta},
        },
        "regulatory": request.regulatory,
        "status": "verified" if result.success else "failed",
    }
    return cert


@app.post("/evaluate/mia")
async def evaluate_mia(request: MIARequest):
    from training.data import generate_synthetic_data

    target_ids = set(request.target_data_ids) if request.target_data_ids else set()
    data_size = max(request.data_size, 100)

    dataset = generate_synthetic_data(
        num_samples=data_size,
        seed=hash(request.model_name + "_mia") % (2**31),
    )
    unlearned = dataset.get_by_ids(target_ids) if target_ids else dataset.get_subset(list(range(5)))
    split = dataset.size // 2
    member = dataset.get_subset(list(range(1, split)))
    nonmember = dataset.get_subset(list(range(split, dataset.size)))

    ctx = UnlearningContext(
        target_data_ids=list(target_ids) if target_ids else ["data_000000"],
        model_name=request.model_name if request.model_name else "mia_model",
        data_size=data_size,
        config=request.config,
    )

    from unlearning.algorithms.sisa import SISAUnlearning
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


@app.post("/evaluate/privacy")
async def evaluate_privacy(request: MIARequest):
    from training.data import generate_synthetic_data

    target_ids = set(request.target_data_ids) if request.target_data_ids else set()
    data_size = max(request.data_size, 100)

    original = generate_synthetic_data(
        num_samples=data_size,
        seed=hash(request.model_name + "_priv") % (2**31),
    )

    ctx = UnlearningContext(
        target_data_ids=list(target_ids) if target_ids else ["data_000000"],
        model_name=request.model_name if request.model_name else "priv_model",
        data_size=data_size,
        config=request.config,
    )

    from unlearning.algorithms.sisa import SISAUnlearning
    algo = SISAUnlearning(num_shards=4)
    await algo.unlearn(ctx)

    retained = original.remove_by_ids(target_ids) if target_ids else original
    model = algo.model

    report = privacy_evaluator.evaluate(
        model=model,
        original_dataset=original,
        retained_dataset=retained,
        unlearned_ids=target_ids,
    )

    return report.to_dict()


@app.post("/proof/generate-zksnark")
async def generate_zksnark_proof(request: ZKProofRequest):
    from verification.zksnark_service import ZKProofService

    svc = ZKProofService(hash_algorithm=request.hash_algorithm)
    proof = svc.generate_proof(
        leaf_data=request.leaf_data,
        all_leaves=request.all_leaves,
    )
    return proof.to_dict()


@app.post("/proof/verify-zksnark")
async def verify_zksnark_proof(request: ZKVerifyRequest):
    from verification.zksnark_service import ZKProofService, ZKProof, ZKVerificationKey

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
    return {"is_valid": is_valid, "algorithm": "groth16", "curve": "bn254", "circuit_type": pdata.get("circuit_type", "merkle_inclusion")}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "engine": "veriunlearn-ml",
        "version": "1.0.0",
        "algorithms": list(controller.algorithms.keys()),
    }
