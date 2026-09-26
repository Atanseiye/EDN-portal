# EDNAi architecture

## Goal

Move a Nigerian developer from "I can download N-ATLaS" to "I can integrate, test, adapt and deploy it with repeatable tooling."

## Layers

### 1. Model identity layer

EDNAi defines one qualifying base model:

`NCAIR1/N-ATLaS`

All providers call `assert_natlas_model()`. A different foundation model cannot silently pass through the gateway as N-ATLaS.

### 2. Runtime layer

Supported runtime adapters:

- **Local Transformers** — direct model loading from the NCAIR Hugging Face repository.
- **Gradio/ZeroGPU** — EDNAi's own Space directly loading the same repository.
- **OpenAI-compatible N-ATLaS server** — for vLLM/TGI/partner infrastructure exposing a chat endpoint.

### 3. Developer gateway

FastAPI exposes:

- `POST /v1/generate`
- `POST /v1/chat/completions`
- `GET /v1/models`
- `GET /health`

The OpenAI-compatible route is an interoperability layer, not a model substitution layer.

### 4. SDK layer

Python:
- synchronous client;
- asynchronous client;
- typed Pydantic responses;
- CLI.

TypeScript:
- browser/Node-compatible fetch client;
- typed messages and generation response.

### 5. Evaluation layer

A JSONL benchmark runner provides:
- versioned prompts;
- language labels;
- required/forbidden text smoke checks;
- JSON validity;
- basic Nigerian-language signal checks;
- latency reporting;
- JSON report export.

These are engineering regression checks, not substitutes for human linguistic evaluation.

### 6. Adaptation layer

The QLoRA starter:
- validates/normalizes chat data;
- loads `NCAIR1/N-ATLaS` in 4-bit NF4;
- prepares k-bit training;
- applies LoRA to all linear layers;
- trains adapter weights;
- saves adapters separately.

### 7. Documentation layer

English and Yorùbá documentation ship with working examples. The code samples are identical across language docs to reduce divergence.

### 8. Validation layer

External beta feedback is deduplicated by a one-way tester hash. Internal testers are excluded from the two-external-tester gate. Structured evidence is emitted to server logs and can be persisted in Postgres.

## Request flow

```
Developer
   |
   +-- Python SDK
   +-- TypeScript SDK
   +-- curl / OpenAI client
   +-- Browser Playground
            |
            v
       EDNAi Gateway
            |
       model-ID guard
            |
   +--------+----------+
   |        |          |
 local   ZeroGPU   N-ATLaS endpoint
   |        |          |
   +--------+----------+
            |
      NCAIR1/N-ATLaS
```
