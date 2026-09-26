# EDNAi — Getting Started (English / Nigerian English)

EDNAi is a developer layer for the official `NCAIR1/N-ATLaS` model. It provides consistent SDKs, a gateway, evaluation tools, dataset preparation, adaptation tooling and runtime helpers.

## Core guarantee

EDNAi does not substitute another general-purpose model. Qualifying inference must identify the upstream model as exactly `NCAIR1/N-ATLaS`.

## Python SDK

```python
from ednai import EDNAi

client = EDNAi(base_url="https://ednai-6znf.onrender.com")
response = client.generate(
    "Explain prepaid electricity metering simply.",
    system="Answer clearly in Nigerian English.",
    temperature=0.2,
    max_tokens=300,
)
print(response.text)
```

## TypeScript SDK

```ts
import { EDNAi } from "@ednai/sdk";

const ai = new EDNAi({
  baseUrl: "https://ednai-6znf.onrender.com"
});

const result = await ai.generate("Ka bayyana API da Hausa.");
console.log(result.text);
```

## OpenAI-compatible API

```bash
curl -X POST https://ednai-6znf.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"NCAIR1/N-ATLaS",
    "messages":[{"role":"user","content":"Kí ni API?"}],
    "temperature":0.2,
    "max_tokens":300
  }'
```

## Prompting and JSON mode

Use a system message to specify language, tone or task constraints. Leave JSON mode off for normal prose. Enable it only when the application requires machine-readable JSON.

## Evaluation

```bash
ednai eval benchmarks/natlas_smoke.jsonl \
  --base-url https://ednai-6znf.onrender.com \
  --output report.json
```

Benchmark cases can validate required strings, forbidden strings, JSON validity and latency. For semantic quality, add human review or task-specific metrics.

## Dataset Studio

Dataset Studio accepts:
- chat-format `messages[]`;
- instruction/input/output JSONL.

It validates records, normalizes the dataset and produces training-ready JSONL without intentionally persisting uploaded content.

## Fine-tuning

```bash
python fine_tuning/prepare_data.py --input raw.jsonl --output prepared.jsonl
python fine_tuning/train_qlora.py \
  --dataset prepared.jsonl \
  --output-dir outputs/my-natlas-adapter
```

The QLoRA starter derives adapters directly from `NCAIR1/N-ATLaS`.

## Runtime modes

- **ZeroGPU** — hosted development/demo runtime. Free quota may queue or temporarily exhaust.
- **Local Transformers** — load official N-ATLaS weights on your own machine or server.
- **OpenAI-compatible N-ATLaS** — connect EDNAi to an endpoint that truly serves N-ATLaS.

## Runtime verification

```bash
curl -X POST https://ednai-6znf.onrender.com/api/runtime/probe
```

The probe verifies model provenance and fails if the upstream model identity is not exactly `NCAIR1/N-ATLaS`.

## Speech model registry

- Nigerian English — `NCAIR1/NigerianAccentedEnglish`
- Yorùbá — `NCAIR1/Yoruba-ASR`
- Hausa — `NCAIR1/Hausa-ASR`
- Igbo — `NCAIR1/Igbo-ASR`
