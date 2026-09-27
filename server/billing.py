from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

MICRO_USD = Decimal("1000000")


@dataclass(frozen=True)
class Pricing:
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal

    @classmethod
    def from_values(cls, input_rate: float | str, output_rate: float | str) -> "Pricing":
        return cls(Decimal(str(input_rate)), Decimal(str(output_rate)))

    def charge_microusd(self, prompt_tokens: int, completion_tokens: int) -> int:
        usd = (
            Decimal(max(0, prompt_tokens)) * self.input_usd_per_million / MICRO_USD
            + Decimal(max(0, completion_tokens)) * self.output_usd_per_million / MICRO_USD
        )
        return int((usd * MICRO_USD).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def max_authorization_microusd(self, estimated_prompt_tokens: int, max_tokens: int) -> int:
        return self.charge_microusd(estimated_prompt_tokens, max_tokens)

    def public(self) -> dict[str, Any]:
        return {
            "currency": "USD",
            "input_usd_per_1m_tokens": float(self.input_usd_per_million),
            "output_usd_per_1m_tokens": float(self.output_usd_per_million),
            "billing_unit": "token",
        }


def estimate_prompt_tokens(messages: list[Any]) -> int:
    # Solvency pre-check only. Never presented as exact billed usage.
    chars = 0
    for message in messages:
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content", "")
        chars += len(str(content or ""))
    return max(1, (chars + 3) // 4)


def usage_tokens(usage: dict[str, Any], *, messages: list[Any], output_text: str) -> tuple[int, int, str]:
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if prompt is not None and completion is not None:
        return int(prompt), int(completion), "provider_exact"

    prompt_est = estimate_prompt_tokens(messages)
    completion_est = max(1, (len(output_text) + 3) // 4) if output_text else 0
    return prompt_est, completion_est, "estimated_chars"
