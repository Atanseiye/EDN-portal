# EDNAi

**Developer infrastructure for N-ATLaS — built by Energy Data Network (EDN)**

EDNAi is an open developer platform that makes Nigeria's N-ATLaS model easier to integrate, test, evaluate, adapt and deploy.

It is being built for the **National AI Innovation Challenge 2026 — Developer Infrastructure** problem statement.

**Live developer playground:** https://ednai-6znf.onrender.com  
**Documentation hub:** https://ednai-6znf.onrender.com/guide  
**English / Nigerian English docs:** https://ednai-6znf.onrender.com/guide/en  
**Yorùbá docs:** https://ednai-6znf.onrender.com/guide/yo  
**Hausa docs:** https://ednai-6znf.onrender.com/guide/ha  
**Igbo docs:** https://ednai-6znf.onrender.com/guide/ig  
**Challenge readiness:** https://ednai-6znf.onrender.com/challenge  
**OpenAPI:** https://ednai-6znf.onrender.com/docs

## What EDNAi ships

- Python SDK with sync + async clients.
- TypeScript/JavaScript SDK.
- OpenAI-compatible N-ATLaS gateway.
- Browser playground for prompts, parameters and JSON-mode testing.
- Structured Use Case Studio for chatbot, translation, education, cultural preservation, government services, digital inclusion, research and original song-lyrics generation.
- Direct local Transformers integration with `NCAIR1/N-ATLaS`.
- Hugging Face/Gradio Space integration for hosted N-ATLaS runtimes.
- Nigerian-language ASR model registry.
- Evaluation harness and multilingual smoke benchmark.
- QLoRA/LoRA fine-tuning starter kit.
- First-class English / Nigerian English, Yorùbá, Hausa and Igbo developer documentation.
- Challenge-readiness and external beta-test evidence endpoints.

EDNAi deliberately refuses to identify a different general-purpose model as N-ATLaS.

For real-user deployment, follow the fail-closed production baseline in `docs/PRODUCTION_DEPLOYMENT.md`. The shared challenge demo account must not share a database/environment with real customer accounts.

## Start a new N-ATLaS project

```bash
ednai init my-natlas-app
cd my-natlas-app
```

## Quick start — SDK

```bash
pip install -e .
```

```python
from ednai import EDNAi

client = EDNAi(base_url="http://localhost:8000")
result = client.generate(
    "Explain transformer attention in simple Nigerian English.",
    temperature=0.3,
)
print(result.text)
```

## Run the developer gateway + playground

```bash
uvicorn server.main:app --reload
```

Open http://localhost:8000.

## Direct local N-ATLaS

Install the local runtime extras:

```bash
pip install -e ".[local]"
```

Then:

```bash
EDNAI_PROVIDER=local \
HF_TOKEN=... \
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

The model ID is locked to `NCAIR1/N-ATLaS`.

## Hosted N-ATLaS

EDNAi supports:
- an OpenAI-compatible endpoint that serves `NCAIR1/N-ATLaS`;
- an EDNAi Gradio/ZeroGPU N-ATLaS runtime;
- direct local Transformers inference.

See `docs/en/getting-started.md`.

## Developer accounts, API keys and billing

EDNAi includes a developer control plane at `/developer`.

Developers can:

- register and sign in;
- create multiple API keys;
- grant each key only the features it needs;
- revoke keys without changing account credentials;
- see prepaid balance, token usage and request costs;
- inspect whether token usage was provider-exact or estimated.

The challenge/demo identity is:

```text
email: demo@edn.com
password: 12345
```

This is an intentionally weak, public **demo-only** credential and must never be reused as a production password.

API keys use the `ednai_live_` prefix. The full key is returned once at creation; only a SHA-256 hash and display prefix are stored afterward.

Current enforced scopes:

```text
inference.generate
inference.chat
usecases.run
speech.transcribe
evaluation.run
dataset.inspect
finetuning.plan
```

Example:

```bash
export EDNAI_API_KEY="ednai_live_..."

curl -X POST https://ednai-6znf.onrender.com/v1/generate \
  -H "Authorization: Bearer $EDNAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model":"NCAIR1/N-ATLaS",
    "messages":[{"role":"user","content":"Explain APIs simply."}]
  }'
```

### Token metering

The hosted N-ATLaS runtime reports tokenizer-derived `prompt_tokens` and `completion_tokens`. EDNAi records those counts in the usage ledger and charges the account according to the configured input/output rates.

When an upstream provider does not return token counts, EDNAi explicitly marks the measurement as an estimate instead of presenting it as exact.

The default demo rates are configurable deployment values, not final commercial pricing:

```text
EDNAI_INPUT_USD_PER_1M_TOKENS
EDNAI_OUTPUT_USD_PER_1M_TOKENS
EDNAI_DEMO_CREDIT_USD
```

Wallet deductions are atomic, so concurrent requests cannot spend the same prepaid balance twice.

### Payment collection

The prepaid wallet, ledger, balance enforcement and per-request charging are implemented. External card/bank checkout is intentionally not fabricated in the repository: the selected payment provider should credit the ledger only after a verified successful payment/webhook.

## N-ATLaS Use Case Studio

EDNAi productizes the model's published application patterns as structured developer workflows:

```text
chatbot
translation
education
culture
government
digital_inclusion
research
song
```

Discover workflows:

```bash
curl https://ednai-6znf.onrender.com/v1/use-cases
```

Run one from Python:

```python
from ednai import EDNAi

ai = EDNAi(base_url="https://ednai-6znf.onrender.com")
result = ai.run_use_case(
    "translation",
    {
        "source_language": "english",
        "target_language": "yoruba",
        "text": "Digital tools should be understandable and useful to everyone.",
    },
    language="yoruba",
)
print(result.text)
```

Or through HTTP:

```text
POST /v1/use-cases/{use_case}
```

Each workflow builds a task-specific prompt contract and executes through the same provenance-locked `NCAIR1/N-ATLaS` runtime. Song generation means original text lyrics only; it does not introduce an audio/TTS model.

See `docs/USE_CASES.md` for the full workflow contract.

## Fine-tuning

```bash
pip install -e ".[train]"
python fine_tuning/prepare_data.py --input your.jsonl --output prepared.jsonl
python fine_tuning/train_qlora.py --dataset prepared.jsonl --output-dir ./outputs/my-adapter
```

The starter kit always derives adapters from `NCAIR1/N-ATLaS`.

## Evaluation

```bash
ednai eval benchmarks/natlas_smoke.jsonl --base-url http://localhost:8000
```

Compare a base runtime with an adapted N-ATLaS runtime:

```bash
ednai compare benchmarks/natlas_smoke.jsonl \
  --baseline-url http://localhost:8000 \
  --candidate-url http://localhost:8001 \
  --output comparison.json
```

Live provenance check after a runtime is configured:

```bash
curl -X POST https://ednai-6znf.onrender.com/api/runtime/probe
```

## Challenge validation

Developer Infrastructure requires at least two external beta testers. EDNAi records only tester-supplied feedback and does not manufacture validation evidence.

- `GET /challenge`
- `GET /api/challenge/readiness`
- `POST /api/beta/feedback`

## License

Apache-2.0.


## Speech development

EDNAi's challenge submission uses only official NCAIR / N-ATLaS speech-recognition models. No unrelated speech model is part of the submission path.

### Official NCAIR ASR

The gateway exposes:

```text
POST /v1/audio/transcriptions
GET  /v1/audio/capabilities
POST /api/studio/speech/score
```

Supported official models:

- English / Nigerian English — `NCAIR1/NigerianAccentedEnglish`
- Yorùbá — `NCAIR1/Yoruba-ASR`
- Hausa — `NCAIR1/Hausa-ASR`
- Igbo — `NCAIR1/Igbo-ASR`

Python:

```python
from ednai import EDNAi

ai = EDNAi(base_url="https://ednai-6znf.onrender.com")
result = ai.transcribe("sample.wav", language="yoruba")
print(result.text)
print(result.model)
```

CLI:

```bash
ednai transcribe sample.wav --language yoruba \
  --base-url https://ednai-6znf.onrender.com
```

Browser/TypeScript applications can compose official speech input with N-ATLaS generation:

```ts
const result = await ai.voiceTurn(audioBlob, "yoruba", {
  system: "Dáhùn ní Yorùbá tó rọrùn.",
});

console.log(result.transcription.text);
console.log(result.generation.text);
```

This performs:

```text
audio
  -> official NCAIR ASR
  -> transcript
  -> NCAIR1/N-ATLaS
  -> text response
```

The ASR model ID is provenance-checked against the selected language. EDNAi rejects substituted speech models.

WER and CER scoring are available in Speech Studio and through `/api/studio/speech/score`.

Batch benchmark a JSONL manifest of audio/reference pairs:

```bash
ednai speech-eval examples/speech-benchmark.jsonl \
  --base-url https://ednai-6znf.onrender.com \
  --output speech-report.json
```
