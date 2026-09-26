"""Provision the EDNAi zero-cost direct N-ATLaS runtime on Hugging Face ZeroGPU.

The provisioner is fail-closed:
- only NCAIR1/N-ATLaS is verified;
- only zero-a10g hardware is permitted;
- the HF token is stored only as a Space secret;
- success is reported only after the Space reaches a usable runtime stage.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from huggingface_hub import HfApi, get_token, hf_hub_download

ROOT = Path(__file__).resolve().parents[1]
OWNER = os.getenv("HF_OWNER", "KoladeOdunope")
SPACE_ID = os.getenv("EDNAI_HF_SPACE", f"{OWNER}/ednai-natlas-runtime")
MODEL_ID = "NCAIR1/N-ATLaS"
ASR_MODEL_IDS = [
    "NCAIR1/NigerianAccentedEnglish",
    "NCAIR1/Yoruba-ASR",
    "NCAIR1/Hausa-ASR",
    "NCAIR1/Igbo-ASR",
]
ZERO_GPU = "zero-a10g"


def main() -> None:
    token = os.getenv("HF_TOKEN") or get_token()
    if not token:
        raise SystemExit(
            "Run hf auth login or set HF_TOKEN locally. Do not commit the token."
        )

    api = HfApi(token=token)
    user = api.whoami(token=token).get("name")
    if user and user.lower() != OWNER.lower():
        raise SystemExit(f"Authenticated as {user}; expected {OWNER}.")

    requested = os.getenv("EDNAI_HF_HARDWARE", ZERO_GPU)
    if requested != ZERO_GPU:
        raise SystemExit(
            f"Refusing {requested}. EDNAi provisioner only permits {ZERO_GPU}."
        )

    print("Verifying gated N-ATLaS and official ASR access...", flush=True)
    missing_access = []
    for repo_id in [MODEL_ID, *ASR_MODEL_IDS]:
        try:
            hf_hub_download(repo_id, "config.json", token=token)
            print(f"  access verified: {repo_id}", flush=True)
        except Exception:
            missing_access.append(repo_id)
            print(f"  access missing:  {repo_id}", flush=True)

    if missing_access:
        raise SystemExit(
            "Missing Hugging Face gated access for: "
            + ", ".join(missing_access)
            + ". Accept/request access for these repositories using the same "
              "account that owns HF_TOKEN, then rerun this workflow."
        )

    api.create_repo(
        repo_id=SPACE_ID,
        repo_type="space",
        space_sdk="gradio",
        space_hardware=ZERO_GPU,
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

    print(f"Space: https://huggingface.co/spaces/{SPACE_ID}", flush=True)

    deadline = time.time() + 480
    last_stage = None
    runtime = None

    while time.time() < deadline:
        runtime = api.get_space_runtime(repo_id=SPACE_ID, token=token)
        stage = str(runtime.stage)

        if stage != last_stage:
            print(
                f"Stage: {stage}; hardware={runtime.hardware}; "
                f"requested={runtime.requested_hardware}",
                flush=True,
            )
            last_stage = stage

        normalized = stage.upper()
        if normalized in {"RUNNING", "RUNNING_APP_STARTING"}:
            break

        if any(
            marker in normalized
            for marker in ("ERROR", "FAILED", "BROKEN", "CONFIG_ERROR")
        ):
            raise SystemExit(f"Hugging Face Space failed to start: {stage}")

        time.sleep(10)
    else:
        raise SystemExit(
            f"Timed out waiting for {SPACE_ID}. Last stage: {last_stage}"
        )

    if runtime is None:
        raise SystemExit("Runtime status could not be read.")

    if (
        str(runtime.hardware) != ZERO_GPU
        and str(runtime.requested_hardware) != ZERO_GPU
    ):
        raise SystemExit(
            "Runtime is not configured for ZeroGPU: "
            f"hardware={runtime.hardware}, requested={runtime.requested_hardware}"
        )

    print("\nRuntime is ready. Configure EDNAi with:", flush=True)
    print("EDNAI_PROVIDER=gradio_space", flush=True)
    print(f"EDNAI_GRADIO_SPACE_ID={SPACE_ID}", flush=True)


if __name__ == "__main__":
    main()
