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
- Direct local Transformers integration with `NCAIR1/N-ATLaS`.
- Hugging Face/Gradio Space integration for hosted N-ATLaS runtimes.
- Nigerian-language ASR model registry.
- Evaluation harness and multilingual smoke benchmark.
- QLoRA/LoRA fine-tuning starter kit.
- First-class English / Nigerian English, Yorùbá, Hausa and Igbo developer documentation.
- Challenge-readiness and external beta-test evidence endpoints.

EDNAi deliberately refuses to identify a different general-purpose model as N-ATLaS.

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

EDNAi includes a first-class Speech Studio and developer APIs for Nigerian voice applications.

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

The ASR model ID is provenance-checked against the selected language. WER and CER scoring are available in Speech Studio and through `/api/studio/speech/score`.

### TTS

NCAIR currently publishes no official N-ATLaS TTS checkpoint. EDNAi therefore does **not** label speech synthesis as N-ATLaS. The hosted interface and TypeScript SDK use matching browser/device voices only when available:

```ts
await ai.speak("Ẹ káàbọ̀ sí EDNAi.", "yoruba");
```

No silent fallback to a different language is performed.
