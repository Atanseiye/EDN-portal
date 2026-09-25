# Zero-cost N-ATLaS activation

PowerRights uses two Hugging Face ZeroGPU Spaces so the official 8B N-ATLaS LLM and four N-ATLaS Whisper-small ASR models do not compete for memory.

## Why ZeroGPU

Hugging Face currently allows eligible free personal accounts to host up to two ZeroGPU Spaces. ZeroGPU dynamically allocates GPU resources to Gradio functions and is therefore suitable for challenge validation without paid infrastructure.

## Space 1: LLM

Copy the contents of `hf_spaces/llm/` into a Gradio Space.

Required:
- Hardware: ZeroGPU (free)
- Secret: `HF_TOKEN`
- The token owner must have accepted the gated terms for `NCAIR1/N-ATLaS`.

The Space exposes:
- `/generate_json`

## Space 2: ASR

Copy the contents of `hf_spaces/asr/` into a second Gradio Space.

Required:
- Hardware: ZeroGPU (free)
- Secret: `HF_TOKEN`
- The token owner must have accepted the gated terms for all four official ASR repositories.

The Space exposes:
- `/transcribe`

## Connect Render

Set the PowerRights Render service environment:

```
NATLAS_PROVIDER=gradio_space
NATLAS_SPACE_ID=<hugging-face-username>/<llm-space>
ASR_PROVIDER=gradio_space
ASR_SPACE_ID=<hugging-face-username>/<asr-space>
```

Then verify:

```
GET /health
GET /api/v1/challenge/readiness
```

Both official model checks must be true before collecting challenge validation traffic.
