from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_ROLES = {"system", "user", "assistant"}


def normalize_row(raw: dict, line_no: int) -> dict:
    if "messages" in raw:
        messages = raw["messages"]
        if not isinstance(messages, list) or not messages:
            raise ValueError(f"line {line_no}: messages must be a non-empty list")
        cleaned = []
        for idx, message in enumerate(messages):
            if not isinstance(message, dict):
                raise ValueError(f"line {line_no}: message {idx} is not an object")
            role = str(message.get("role", "")).strip()
            content = str(message.get("content", "")).strip()
            if role not in ALLOWED_ROLES:
                raise ValueError(f"line {line_no}: unsupported role {role!r}")
            if not content:
                raise ValueError(f"line {line_no}: empty content in message {idx}")
            cleaned.append({"role": role, "content": content})
        if cleaned[-1]["role"] != "assistant":
            raise ValueError(f"line {line_no}: final training message must be assistant")
        return {"messages": cleaned}

    instruction = str(raw.get("instruction", "")).strip()
    input_text = str(raw.get("input", "")).strip()
    output = str(raw.get("output", "")).strip()
    if not instruction or not output:
        raise ValueError(
            f"line {line_no}: provide messages[] or instruction/output fields"
        )
    user = instruction if not input_text else f"{instruction}\n\n{input_text}"
    return {
        "messages": [
            {"role": "user", "content": user},
            {"role": "assistant", "content": output},
        ]
    }


def main():
    parser = argparse.ArgumentParser(description="Validate and normalize N-ATLaS SFT JSONL")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.input)
    target = Path(args.output)
    rows = []
    with source.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if line.strip():
                rows.append(normalize_row(json.loads(line), line_no))

    if not rows:
        raise SystemExit("Dataset is empty")

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Prepared {len(rows)} examples -> {target}")


if __name__ == "__main__":
    main()
