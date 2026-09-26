"""Create EDNAi's zero-cost N-ATLaS runtime Space.

This script intentionally permits only Hugging Face ZeroGPU hardware.
Run it locally with an HF token that can create Spaces and read NCAIR1/N-ATLaS.
"""
from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import HfApi, get_token, hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
OWNER = os.getenv("HF_OWNER", "Kolade1")
SPACE_ID = os.getenv("EDNAI_HF_SPACE", f"{OWNER}/ednai-natlas-runtime")
MODEL_ID = "NCAIR1/N-ATLaS"
ZERO_GPU = "zero-a10g"


def main():
    token = os.getenv("HF_TOKEN") or get_token()
    if not token:
        raise SystemExit(
            "Run hf auth login or set HF_TOKEN locally. Do not commit the token."
        )

    api = HfApi(token=token)
    user = api.whoami(token=token).get("name")
    if user and user.lower() != OWNER.lower():
        raise SystemExit(f"Authenticated as {user}; expected {OWNER}.")

    print("Verifying gated N-ATLaS access...")
    hf_hub_download(MODEL_ID, "config.json", token=token)

    api.create_repo(
        repo_id=SPACE_ID,
        repo_type="space",
        space_sdk="gradio",
        private=False,
        exist_ok=True,
        token=token,
    )
    api.upload_folder(
        repo_id=SPACE_ID,
        repo_type="space",
        folder_path=str(ROOT / "runtime" / "hf_space"),
        path_in_repo="",
        commit_message="Deploy EDNAi direct N-ATLaS runtime",
        token=token,
    )
    api.add_space_secret(
        repo_id=SPACE_ID,
        key="HF_TOKEN",
        value=token,
        token=token,
    )

    requested = os.getenv("EDNAI_HF_HARDWARE", ZERO_GPU)
    if requested != ZERO_GPU:
        raise SystemExit(
            f"Refusing {requested}. EDNAi provisioner only permits {ZERO_GPU}."
        )

    api.request_space_hardware(
        repo_id=SPACE_ID,
        hardware=ZERO_GPU,
        token=token,
    )
    runtime = api.get_space_runtime(repo_id=SPACE_ID, token=token)
    print(f"Space: https://huggingface.co/spaces/{SPACE_ID}")
    print(f"Stage: {runtime.stage}")
    print(f"Hardware: {runtime.hardware}; requested: {runtime.requested_hardware}")
    print("\nWhen the Space is Running, set:")
    print("EDNAI_PROVIDER=gradio_space")
    print(f"EDNAI_GRADIO_SPACE_ID={SPACE_ID}")


if __name__ == "__main__":
    main()
