from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

from .client import EDNAi


@dataclass
class EvalCase:
    id: str
    prompt: str
    language: str = "english"
    system: str | None = None
    must_include: list[str] | None = None
    must_not_include: list[str] | None = None
    json_mode: bool = False


@dataclass
class EvalResult:
    id: str
    passed: bool
    text: str
    latency_ms: float | None
    checks: dict[str, bool]
    error: str | None = None


def load_jsonl(path: str | Path) -> list[EvalCase]:
    items: list[EvalCase] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                items.append(EvalCase(**raw))
            except Exception as exc:
                raise ValueError(f"Invalid benchmark line {line_no}: {exc}") from exc
    return items


def _contains(text: str, values: Iterable[str]) -> bool:
    low = text.casefold()
    return all(value.casefold() in low for value in values)


def score(case: EvalCase, text: str) -> dict[str, bool]:
    checks: dict[str, bool] = {"non_empty": bool(text.strip())}
    if case.must_include:
        checks["must_include"] = _contains(text, case.must_include)
    if case.must_not_include:
        checks["must_not_include"] = not any(
            value.casefold() in text.casefold() for value in case.must_not_include
        )
    if case.json_mode:
        try:
            json.loads(text)
            checks["valid_json"] = True
        except Exception:
            checks["valid_json"] = False

    # Lightweight language signals. These are smoke checks, not linguistic quality scores.
    if case.language == "yoruba":
        checks["language_signal"] = bool(re.search(r"[ẹọṣẸỌṢ]|\b(àti|ní|jẹ́|ṣe|ẹ̀|ọ̀)\b", text))
    elif case.language == "hausa":
        checks["language_signal"] = bool(re.search(r"\b(da|ne|ce|yana|akwai|domin|wannan)\b", text, re.I))
    elif case.language == "igbo":
        checks["language_signal"] = bool(re.search(r"[ịọụṅỊỌỤṄ]|\b(na|bụ|anyị|nke|ọkụ|ihe)\b", text, re.I))
    else:
        checks["language_signal"] = True
    return checks


def run_benchmark(client: EDNAi, cases: list[EvalCase]) -> list[EvalResult]:
    results: list[EvalResult] = []
    for case in cases:
        try:
            generation = client.generate(
                case.prompt,
                system=case.system,
                json_mode=case.json_mode,
                temperature=0,
            )
            checks = score(case, generation.text)
            results.append(EvalResult(
                id=case.id,
                passed=all(checks.values()),
                text=generation.text,
                latency_ms=generation.latency_ms,
                checks=checks,
            ))
        except Exception as exc:
            results.append(EvalResult(
                id=case.id,
                passed=False,
                text="",
                latency_ms=None,
                checks={},
                error=str(exc),
            ))
    return results


def summarize(results: list[EvalResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    latencies = [r.latency_ms for r in results if r.latency_ms is not None]
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "median_latency_ms": round(statistics.median(latencies), 2) if latencies else None,
        "results": [asdict(r) for r in results],
    }
