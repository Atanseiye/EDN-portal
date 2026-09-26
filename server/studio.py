from __future__ import annotations

import io
import json
import statistics
import zipfile
from collections import Counter
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ednai.evals import EvalCase, EvalResult, score, summarize
from ednai.models import Message
from ednai.providers import NATLAS_MODEL_ID, Provider, ProviderError
from fine_tuning.prepare_data import normalize_row

router = APIRouter(prefix="/api/studio", tags=["Developer Studio"])


class StudioEvalCase(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=20_000)
    language: str = "english"
    system: str | None = Field(default=None, max_length=20_000)
    must_include: list[str] | None = None
    must_not_include: list[str] | None = None
    json_mode: bool = False


class EvalRunRequest(BaseModel):
    cases: list[StudioEvalCase] = Field(min_length=1, max_length=50)
    temperature: float = Field(default=0, ge=0, le=2)
    max_tokens: int = Field(default=512, ge=1, le=2048)


class DatasetInspectRequest(BaseModel):
    jsonl: str = Field(min_length=1, max_length=2_000_000)
    preview_rows: int = Field(default=3, ge=1, le=10)


class FineTunePlanRequest(BaseModel):
    examples: int = Field(default=500, ge=1)
    epochs: float = Field(default=2.0, ge=0.1, le=20)
    learning_rate: float = Field(default=0.0002, gt=0, le=0.1)
    batch_size: int = Field(default=1, ge=1, le=64)
    gradient_accumulation: int = Field(default=16, ge=1, le=256)
    max_length: int = Field(default=2048, ge=128, le=8192)
    lora_r: int = Field(default=16, ge=1, le=256)
    lora_alpha: int = Field(default=32, ge=1, le=512)
    output_dir: str = Field(default="outputs/my-natlas-adapter", min_length=1, max_length=200)


def run_studio_eval(provider: Provider | None, data: EvalRunRequest) -> dict[str, Any]:
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail="Connect a direct N-ATLaS runtime before running live evaluations.",
        )

    results: list[EvalResult] = []
    for item in data.cases:
        case = EvalCase(
            id=item.id,
            prompt=item.prompt,
            language=item.language,
            system=item.system,
            must_include=item.must_include,
            must_not_include=item.must_not_include,
            json_mode=item.json_mode,
        )
        messages = []
        if item.system:
            messages.append(Message(role="system", content=item.system))
        messages.append(Message(role="user", content=item.prompt))
        try:
            generation = provider.generate(
                messages,
                model=NATLAS_MODEL_ID,
                temperature=data.temperature,
                max_tokens=data.max_tokens,
                json_mode=item.json_mode,
            )
            checks = score(case, generation.text)
            results.append(EvalResult(
                id=item.id,
                passed=all(checks.values()),
                text=generation.text,
                latency_ms=generation.latency_ms,
                checks=checks,
            ))
        except ProviderError as exc:
            results.append(EvalResult(
                id=item.id,
                passed=False,
                text="",
                latency_ms=None,
                checks={},
                error=str(exc),
            ))

    report = summarize(results)
    report["model"] = NATLAS_MODEL_ID
    report["languages"] = dict(Counter(item.language for item in data.cases))
    return report


def inspect_dataset(data: DatasetInspectRequest) -> dict[str, Any]:
    normalized: list[dict] = []
    errors: list[dict] = []
    roles: Counter[str] = Counter()
    lengths: list[int] = []
    turns: list[int] = []

    lines = [line for line in data.jsonl.splitlines() if line.strip()]
    if len(lines) > 5000:
        raise HTTPException(status_code=413, detail="Dataset Studio accepts up to 5,000 rows per inspection.")

    for line_no, line in enumerate(lines, 1):
        try:
            raw = json.loads(line)
            row = normalize_row(raw, line_no)
            normalized.append(row)
            turns.append(len(row["messages"]))
            for message in row["messages"]:
                roles[message["role"]] += 1
                lengths.append(len(message["content"]))
        except Exception as exc:
            errors.append({"line": line_no, "error": str(exc)})

    total_chars = sum(lengths)
    normalized_jsonl = "\n".join(
        json.dumps(row, ensure_ascii=False) for row in normalized
    )
    if normalized_jsonl:
        normalized_jsonl += "\n"

    return {
        "valid": len(errors) == 0 and bool(normalized),
        "rows_received": len(lines),
        "valid_examples": len(normalized),
        "invalid_examples": len(errors),
        "errors": errors[:50],
        "stats": {
            "message_count": sum(roles.values()),
            "roles": dict(roles),
            "average_turns_per_example": round(statistics.mean(turns), 2) if turns else 0,
            "average_characters_per_message": round(statistics.mean(lengths), 2) if lengths else 0,
            "total_characters": total_chars,
            "rough_token_estimate": round(total_chars / 4),
        },
        "preview": normalized[: data.preview_rows],
        "normalized_jsonl": normalized_jsonl,
        "model": NATLAS_MODEL_ID,
    }


def fine_tune_plan(data: FineTunePlanRequest) -> dict[str, Any]:
    micro_batches_per_epoch = max(
        1,
        (data.examples + data.batch_size - 1) // data.batch_size,
    )
    optimizer_steps_per_epoch = max(
        1,
        (micro_batches_per_epoch + data.gradient_accumulation - 1)
        // data.gradient_accumulation,
    )
    total_steps = max(1, round(optimizer_steps_per_epoch * data.epochs))
    effective_batch = data.batch_size * data.gradient_accumulation

    command = (
        "python fine_tuning/train_qlora.py "
        "--dataset prepared.jsonl "
        f"--output-dir {data.output_dir} "
        f"--epochs {data.epochs} "
        f"--learning-rate {data.learning_rate} "
        f"--batch-size {data.batch_size} "
        f"--grad-accum {data.gradient_accumulation} "
        f"--max-length {data.max_length} "
        f"--lora-r {data.lora_r} "
        f"--lora-alpha {data.lora_alpha}"
    )

    return {
        "model": NATLAS_MODEL_ID,
        "method": "QLoRA",
        "quantization": "4-bit NF4 + double quantization",
        "adapter_target": "all-linear",
        "examples": data.examples,
        "effective_batch_size": effective_batch,
        "estimated_optimizer_steps": total_steps,
        "plan": data.model_dump(),
        "command": command,
        "warnings": [
            "The estimate is for planning only; actual memory/runtime depend on sequence lengths and GPU.",
            "Use a held-out evaluation set before claiming an adapted model is better than base N-ATLaS.",
            "Keep HF_TOKEN outside source control.",
        ],
    }


def starter_zip() -> StreamingResponse:
    files = {
        "ednai-starter/README.md": """# EDNAi N-ATLaS Starter

Install EDNAi, connect a qualifying N-ATLaS runtime, and run `python app.py`.

Evaluate with:

    ednai eval benchmarks/smoke.jsonl --base-url http://localhost:8000
""",
        "ednai-starter/app.py": """from ednai import EDNAi

ai = EDNAi(base_url="http://localhost:8000")
result = ai.generate(
    "Explain what an API is in simple Nigerian English.",
    temperature=0.2,
)
print(result.text)
""",
        "ednai-starter/.env.example": "EDNAI_BASE_URL=http://localhost:8000\n",
        "ednai-starter/benchmarks/smoke.jsonl": (
            '{"id":"capital","prompt":"What is the capital of Nigeria? Answer briefly.",'
            '"language":"english","must_include":["Abuja"]}\n'
        ),
        "ednai-starter/data/example.jsonl": (
            '{"messages":[{"role":"user","content":"What is an API?"},'
            '{"role":"assistant","content":"An API is an interface that lets software systems communicate."}]}\n'
        ),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, body in files.items():
            archive.writestr(path, body)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="ednai-natlas-starter.zip"'},
    )


@router.post("/dataset/inspect")
def dataset_inspect(data: DatasetInspectRequest):
    return inspect_dataset(data)


@router.post("/fine-tune/plan")
def fine_tune(data: FineTunePlanRequest):
    return fine_tune_plan(data)


@router.get("/starter.zip")
def starter():
    return starter_zip()
