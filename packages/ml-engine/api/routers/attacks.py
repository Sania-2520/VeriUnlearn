"""Adversarial security attack endpoints."""

from fastapi import APIRouter

from api.schemas import (
    ExtractionAttackRequest,
    InversionAttackRequest,
    ShadowMIARequest,
)
from unlearning.algorithms.base import UnlearningContext

router = APIRouter()


@router.post("/attacks/model-inversion")
async def run_model_inversion(request: InversionAttackRequest):
    from security.attacks.model_inversion import ModelInversionAttack
    from training.data import generate_synthetic_data
    from unlearning.algorithms.sisa import SISAUnlearning

    data = generate_synthetic_data(num_samples=200, num_features=request.input_dim, seed=42)
    ctx = UnlearningContext(
        target_data_ids=["data_000000"],
        model_name="inversion_target",
        data_size=200,
    )
    algo = SISAUnlearning(num_shards=4)
    await algo.unlearn(ctx)

    attack = ModelInversionAttack(
        iterations=request.iterations,
        learning_rate=request.learning_rate,
    )
    result = attack.attack(
        model=algo.model,
        target_classes=request.target_classes,
        original_dataset=data,
    )
    return result


@router.post("/attacks/shadow-mia")
async def run_shadow_mia(request: ShadowMIARequest):
    from security.attacks.shadow_mia import ShadowModelMIA
    from training.data import generate_synthetic_data
    from unlearning.algorithms.sisa import SISAUnlearning

    data = generate_synthetic_data(num_samples=400, num_features=20, seed=42)
    ctx = UnlearningContext(
        target_data_ids=["data_000000"],
        model_name="shadow_mia_target",
        data_size=400,
    )
    algo = SISAUnlearning(num_shards=4)
    await algo.unlearn(ctx)

    split = data.size // 2
    member_data = data.get_subset(list(range(5, split)))
    nonmember_data = data.get_subset(list(range(split, data.size)))
    target_data = data.get_subset(list(range(5)))

    attack = ShadowModelMIA(
        num_shadow_models=request.num_shadow_models,
        shadow_data_size=request.shadow_data_size,
        shadow_model_epochs=request.shadow_epochs,
    )
    result = attack.attack(algo.model, target_data, member_data, nonmember_data)
    return result


@router.post("/attacks/model-extraction")
async def run_model_extraction(request: ExtractionAttackRequest):
    from security.attacks.model_extraction import ModelExtractionAttack
    from training.data import generate_synthetic_data
    from unlearning.algorithms.sisa import SISAUnlearning

    data = generate_synthetic_data(
        num_samples=200, num_features=request.input_dim,
        num_classes=request.num_classes, seed=42,
    )
    ctx = UnlearningContext(
        target_data_ids=["data_000000"],
        model_name="extraction_target",
        data_size=200,
    )
    algo = SISAUnlearning(num_shards=4)
    await algo.unlearn(ctx)

    attack = ModelExtractionAttack(
        extraction_epochs=request.extraction_epochs,
        num_queries=request.num_queries,
    )
    result = attack.attack(
        victim_model=algo.model,
        input_dim=request.input_dim,
        num_classes=request.num_classes,
        test_dataset=data,
    )
    return result


@router.get("/attacks/methods")
async def list_attack_methods():
    return {
        "methods": [
            {
                "id": "model-inversion",
                "name": "Model Inversion Attack",
                "description": "Gradient-based optimization to reconstruct training data from model parameters",
            },
            {
                "id": "shadow-mia",
                "name": "Shadow Model Membership Inference",
                "description": "Ensemble of shadow models to train a binary attack classifier for membership inference",
            },
            {
                "id": "model-extraction",
                "name": "Model Extraction Attack",
                "description": "Train a substitute model by querying the victim model on synthetic inputs",
            },
        ]
    }
