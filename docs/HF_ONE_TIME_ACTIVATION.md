# One-time Hugging Face activation — no paid infrastructure

The application code is already wired for the official N-ATLaS LLM and four official N-ATLaS ASR models. The connected ChatGPT Hugging Face OAuth permission is read-only, so repository/Space creation cannot be performed from this chat.

This is the single account-owner action required to activate the zero-cost inference layer.

## Safety rule

Do **not** paste your Hugging Face access token into ChatGPT, GitHub, screenshots or application source code.

The provisioner accepts only Hugging Face ZeroGPU hardware (`zero-a10g`). It refuses another hardware value rather than accidentally creating billable GPU infrastructure.

## Step 1 — accept all gated models

While logged in as `Kolade1`, make sure these repositories allow file access:

- https://huggingface.co/NCAIR1/N-ATLaS
- https://huggingface.co/NCAIR1/NigerianAccentedEnglish
- https://huggingface.co/NCAIR1/Yoruba-ASR
- https://huggingface.co/NCAIR1/Hausa-ASR
- https://huggingface.co/NCAIR1/Igbo-ASR

## Step 2 — authenticate locally

Create a User Access Token that can read the gated models and create/write your own Spaces. Then authenticate on your machine:

```powershell
hf auth login
```

Do not send the token in chat.

## Step 3 — run the checked-in provisioner

From a checkout of the `powerrights-ng` branch:

```powershell
pip install "huggingface_hub>=1.0"
python scripts/provision_hf_spaces.py
```

The script verifies all five gates, creates the two PowerRights Spaces, uploads the exact checked-in inference code, stores the model token as a private Space secret, and requests only ZeroGPU hardware.

## Step 4 — report only the Space IDs

Once both Space pages show Running, the only values needed in ChatGPT are:

```text
Kolade1/powerrights-natlas-llm
Kolade1/powerrights-natlas-asr
```

Those IDs are not secrets. Do not share the token.

## Step 5 — live configuration

The Render service then uses:

```text
NATLAS_PROVIDER=gradio_space
NATLAS_SPACE_ID=Kolade1/powerrights-natlas-llm
ASR_PROVIDER=gradio_space
ASR_SPACE_ID=Kolade1/powerrights-natlas-asr
```

After configuration, run:

```powershell
python scripts/verify_live_challenge.py
```

Do not count real-user validation traffic until both official model checks are true.
