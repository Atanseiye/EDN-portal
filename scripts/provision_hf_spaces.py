"""Provision PowerRights' two zero-cost Hugging Face ZeroGPU Spaces.

Run locally. Do not paste your Hugging Face token into chat or commit it.
The script will never request paid GPU hardware; only zero-a10g is permitted.
"""
from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import HfApi, get_token, hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
OWNER = os.getenv("HF_OWNER", "Kolade1")
LLM_SPACE = os.getenv("POWERRIGHTS_LLM_SPACE", f"{OWNER}/powerrights-natlas-llm")
ASR_SPACE = os.getenv("POWERRIGHTS_ASR_SPACE", f"{OWNER}/powerrights-natlas-asr")
ZERO_GPU_HARDWARE = "zero-a10g"

MODELS = [
    "NCAIR1/N-ATLaS",
    "NCAIR1/NigerianAccentedEnglish",
    "NCAIR1/Yoruba-ASR",
    "NCAIR1/Hausa-ASR",
    "NCAIR1/Igbo-ASR",
]


def token_or_die() -> str:
    token = os.getenv("HF_TOKEN") or get_token()
    if not token:
        raise SystemExit(
            "No Hugging Face token found. Run `hf auth login` or set HF_TOKEN locally. "
            "Use a token that can create Spaces and read the gated NCAIR repositories. "
            "Never paste the token into chat or commit it."
        )
    return token


def verify_gated_access(token: str) -> None:
    print("Verifying access to official NCAIR model files...")
    failed: list[str] = []
    for repo_id in MODELS:
        try:
            hf_hub_download(repo_id=repo_id, filename="config.json", token=token)
            print(f"  OK  {repo_id}")
        except Exception as exc:
            failed.append(repo_id)
            print(f"  FAIL {repo_id}: {type(exc).__name__}")
    if failed:
        print("\nAccess is still missing for:")
        for repo_id in failed:
            print(f"  https://huggingface.co/{repo_id}")
        raise SystemExit(
            "\nAccept the access conditions on every failed repository while logged into the same "
            "Hugging Face account, then run this script again."
        )


def create_zero_gpu_space(api: HfApi, token: str, repo_id: str, folder: Path) -> None:
    print(f"\nProvisioning {repo_id}...")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="gradio",
        private=False,
        exist_ok=True,
        token=token,
    )
    api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=str(folder),
        path_in_repo="",
        commit_message="Deploy PowerRights official N-ATLaS ZeroGPU service",
        token=token,
    )
    api.add_space_secret(repo_id=repo_id, key="HF_TOKEN", value=token, token=token)

    requested = os.getenv("POWERRIGHTS_HF_HARDWARE", ZERO_GPU_HARDWARE)
    if requested != ZERO_GPU_HARDWARE:
        raise SystemExit(
            f"Refusing hardware '{requested}'. PowerRights provisioning permits only "
            f"'{ZERO_GPU_HARDWARE}' to honor the no-billable-infrastructure requirement."
        )
    api.request_space_hardware(repo_id=repo_id, hardware=ZERO_GPU_HARDWARE, token=token)
    runtime = api.get_space_runtime(repo_id=repo_id, token=token)
    print(
        f"  stage={runtime.stage} hardware={runtime.hardware} "
        f"requested_hardware={runtime.requested_hardware}"
    )
    if str(runtime.requested_hardware) != ZERO_GPU_HARDWARE and str(runtime.hardware) != ZERO_GPU_HARDWARE:
        raise SystemExit(f"ZeroGPU was not accepted for {repo_id}. Stop here; do not choose a paid GPU.")


def main() -> None:
    token = token_or_die()
    api = HfApi(token=token)
    who = api.whoami(token=token)
    username = who.get("name") or who.get("fullname")
    print(f"Authenticated Hugging Face account: {username}")
    if username and username.lower() != OWNER.lower():
        raise SystemExit(
            f"Authenticated as {username}, but HF_OWNER is {OWNER}. "
            "Use the intended account or set HF_OWNER explicitly."
        )

    verify_gated_access(token)
    create_zero_gpu_space(api, token, LLM_SPACE, ROOT / "hf_spaces" / "llm")
    create_zero_gpu_space(api, token, ASR_SPACE, ROOT / "hf_spaces" / "asr")

    print("\nZeroGPU provisioning submitted successfully.")
    print(f"LLM Space: https://huggingface.co/spaces/{LLM_SPACE}")
    print(f"ASR Space: https://huggingface.co/spaces/{ASR_SPACE}")
    print("\nRender variables after both Spaces show Running:")
    print("NATLAS_PROVIDER=gradio_space")
    print(f"NATLAS_SPACE_ID={LLM_SPACE}")
    print("ASR_PROVIDER=gradio_space")
    print(f"ASR_SPACE_ID={ASR_SPACE}")


if __name__ == "__main__":
    main()
