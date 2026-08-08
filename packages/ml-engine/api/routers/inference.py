"""Inference endpoints (generate, stream, batch, adapter control).

Security posture: every user-supplied prompt is scanned for prompt-injection
patterns before generation (fail-closed on detection), and every model output
is sanitized (control-character stripping + length cap) before it leaves the
engine. This is the single enforcement chokepoint for LLM traffic — the
backend proxies all generation through these routes.
"""

import json
from dataclasses import replace

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api import deps
from api.schemas import AdapterLoadRequest, AdapterSwapRequest, InferenceRequestModel
from security.input_validator import InputValidator

router = APIRouter()

# Strict validator shared by all inference routes. Injection is a hard reject;
# output sanitization is always applied.
_validator = InputValidator(strict=True)


def _validate_prompt(prompt: str) -> None:
    """Reject adversarial prompts before they reach the model (fail closed)."""
    _validator.validate_prompt_safety(prompt)


def _validate_system_prompt(system_prompt: str | None) -> None:
    """Scan a caller-supplied system prompt with the same injection rules.

    The backend exposes user-settable system prompts, so they must not be able
    to bypass the inference chokepoint by smuggling instructions in there.
    """
    if system_prompt:
        _validator.validate_prompt_safety(system_prompt)


def _sanitize_output(text: str) -> str:
    """Strip control characters and bound response length."""
    return _validator.sanitize_text_output(text)


@router.post("/inference/generate")
async def generate_text(request: InferenceRequestModel):
    from inference.service import InferenceRequest

    _validate_prompt(request.prompt)
    _validate_system_prompt(request.system_prompt)
    service = deps.get_inference_service()
    req = InferenceRequest(
        prompt=request.prompt,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        stream=False,
        adapter_name=request.adapter_name,
        system_prompt=request.system_prompt,
    )
    response = service.generate(req)
    return replace(response, text=_sanitize_output(response.text))


@router.post("/inference/generate/stream")
async def generate_stream(request: InferenceRequestModel):
    from inference.service import InferenceRequest

    _validate_prompt(request.prompt)
    _validate_system_prompt(request.system_prompt)
    service = deps.get_inference_service()
    req = InferenceRequest(
        prompt=request.prompt,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        stream=True,
        adapter_name=request.adapter_name,
        system_prompt=request.system_prompt,
    )

    async def event_generator():
        for token in service.generate_stream(req):
            yield f"data: {json.dumps({'token': _sanitize_output(token)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/inference/batch")
async def batch_generate(requests: list[InferenceRequestModel]):
    from inference.service import InferenceRequest

    for r in requests:
        _validate_prompt(r.prompt)
        _validate_system_prompt(r.system_prompt)
    service = deps.get_inference_service()
    inf_requests = [
        InferenceRequest(
            prompt=r.prompt,
            max_new_tokens=r.max_new_tokens,
            temperature=r.temperature,
            top_p=r.top_p,
            stream=False,
            adapter_name=r.adapter_name,
            system_prompt=r.system_prompt,
        )
        for r in requests
    ]
    results = service.batch_generate(inf_requests)
    return [replace(resp, text=_sanitize_output(resp.text)) for resp in results]


@router.get("/inference/metrics")
async def inference_metrics():
    service = deps.get_inference_service()
    return service.get_metrics()


@router.post("/inference/adapters/load")
async def load_adapter(request: AdapterLoadRequest):
    service = deps.get_inference_service()
    result = service.load_adapter(request.adapter_name, request.adapter_path)
    return result


@router.post("/inference/adapters/unload")
async def unload_adapter(request: AdapterSwapRequest):
    service = deps.get_inference_service()
    result = service.unload_adapter(request.new_adapter)
    return result


@router.get("/inference/adapters")
async def list_adapters():
    service = deps.get_inference_service()
    return service.list_adapters()


@router.get("/inference/health")
async def inference_health():
    service = deps.get_inference_service()
    return service.health_check()
