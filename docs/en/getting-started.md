# EDNAi — Getting Started

EDNAi is a developer layer for the official `NCAIR1/N-ATLaS` model. It provides consistent SDKs, a gateway, evaluation tools, adaptation scripts and deployment helpers.

## Python

Install:

```bash
pip install -e .
```

Use:

```python
from ednai import EDNAi

client = EDNAi(base_url="https://your-ednai-gateway.example")

response = client.generate(
    "Explain electricity metering in simple Nigerian English.",
    system="Answer clearly and concisely.",
    temperature=0.2,
    max_tokens=300,
)

print(response.text)
print(response.provider, response.latency_ms)
```

Async:

```python
from ednai import AsyncEDNAi

client = AsyncEDNAi(base_url="https://your-ednai-gateway.example")
response = await client.generate("Kí ni API?", system="Dáhùn ní Yorùbá.")
```

## TypeScript

```ts
import { EDNAi } from "@ednai/sdk";

const ai = new EDNAi({ baseUrl: "https://your-ednai-gateway.example" });

const result = await ai.generate("Ka bayyana API da Hausa.", {
  temperature: 0.2,
  maxTokens: 300,
});

console.log(result.text);
```

## OpenAI-compatible HTTP

```bash
curl -X POST https://your-ednai-gateway.example/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "NCAIR1/N-ATLaS",
    "messages": [{"role":"user","content":"Kọwaa API n\u0027Igbo."}],
    "temperature": 0.2,
    "max_tokens": 300
  }'
```

EDNAi rejects any different model ID on the qualifying runtime.

## Runtime modes

### Local Transformers

Set:

```text
EDNAI_PROVIDER=local
EDNAI_MODEL=NCAIR1/N-ATLaS
HF_TOKEN=...
```

Install `ednai[local]`. The base model is loaded directly from the official NCAIR Hugging Face repository.

### OpenAI-compatible N-ATLaS deployment

Set:

```text
EDNAI_PROVIDER=openai_compatible
EDNAI_UPSTREAM_BASE_URL=https://your-natlas-server.example/v1
EDNAI_UPSTREAM_API_KEY=...
```

The gateway still requires the request model ID to be `NCAIR1/N-ATLaS`.

### EDNAi Gradio runtime

Set:

```text
EDNAI_PROVIDER=gradio_space
EDNAI_GRADIO_SPACE_ID=<account>/<space>
HF_TOKEN=...
```

## Evaluate

```bash
ednai eval benchmarks/natlas_smoke.jsonl \
  --base-url https://your-ednai-gateway.example \
  --output report.json
```

Each benchmark case can specify:
- prompt;
- language;
- required strings;
- forbidden strings;
- JSON validity.

For research-grade evaluation, add human review or task-specific metrics rather than treating keyword checks as semantic quality measurement.

## Adapt

See `fine_tuning/README.md`.

EDNAi's QLoRA starter:
- starts from `NCAIR1/N-ATLaS`;
- uses 4-bit NF4;
- trains lightweight LoRA adapters;
- saves the adapter separately from the base weights.

## Speech

```python
from ednai.speech import asr_model_for

print(asr_model_for("yoruba"))
# NCAIR1/Yoruba-ASR
```

Supported official speech repositories:
- Nigerian English: `NCAIR1/NigerianAccentedEnglish`
- Yorùbá: `NCAIR1/Yoruba-ASR`
- Hausa: `NCAIR1/Hausa-ASR`
- Igbo: `NCAIR1/Igbo-ASR`
