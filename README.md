# EDNAi

**Developer infrastructure for N-ATLaS — built by Energy Data Network (EDN)**

EDNAi is an open developer platform that makes Nigeria's N-ATLaS model easier to integrate, test, evaluate, adapt and deploy.

It is being built for the **National AI Innovation Challenge 2026 — Developer Infrastructure** problem statement.

**Live developer playground:** https://ednai-6znf.onrender.com  
**English docs:** https://ednai-6znf.onrender.com/guide/en  
**Yorùbá docs:** https://ednai-6znf.onrender.com/guide/yo  
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
- English + Yorùbá developer documentation.
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
