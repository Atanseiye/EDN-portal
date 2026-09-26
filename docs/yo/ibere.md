# EDNAi — Ìbẹ̀rẹ̀ fún Developer

EDNAi jẹ́ irinṣẹ́ developer tí a kọ́ lórí model osise `NCAIR1/N-ATLaS`. Ó ń jẹ́ kí developer lè so N-ATLaS mọ́ app, dán án wò, ṣe evaluation, ṣe adaptation, àti deploy rẹ̀ láì ní láti tún gbogbo plumbing kọ láti ìbẹ̀rẹ̀.

## Python

Fi package náà sílẹ̀:

```bash
pip install -e .
```

Lò ó:

```python
from ednai import EDNAi

client = EDNAi(base_url="https://your-ednai-gateway.example")

response = client.generate(
    "Ṣàlàyé ohun tí API jẹ́ fún developer tuntun.",
    system="Dáhùn ní Yorùbá tó rọrùn.",
    temperature=0.2,
    max_tokens=300,
)

print(response.text)
```

## TypeScript

```ts
import { EDNAi } from "@ednai/sdk";

const ai = new EDNAi({ baseUrl: "https://your-ednai-gateway.example" });

const result = await ai.generate("Kí ni API?", {
  system: "Dáhùn ní Yorùbá.",
  temperature: 0.2
});

console.log(result.text);
```

## OpenAI-compatible API

Developer tó ti ní tooling tó ń lo OpenAI-style endpoint lè yí base URL padà sí EDNAi:

```bash
curl -X POST https://your-ednai-gateway.example/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "NCAIR1/N-ATLaS",
    "messages": [{"role":"user","content":"Kí ni transformer attention?"}]
  }'
```

EDNAi kò ní gba model míì gẹ́gẹ́ bí qualifying N-ATLaS runtime. Model ID gbọ́dọ̀ jẹ́ `NCAIR1/N-ATLaS`.

## Evaluation

```bash
ednai eval benchmarks/natlas_smoke.jsonl --base-url http://localhost:8000
```

Benchmark náà lè dán English, Yorùbá, Hausa àti Igbo wò. Àwọn smoke checks kì í ṣe ìdájọ́ semantic quality tó pé; fún production tàbí research, fi human review àti metric tó bá use-case mu kún un.

## Fine-tuning

Wo `fine_tuning/README.md`.

Starter kit EDNAi ń:
- bẹ̀rẹ̀ láti `NCAIR1/N-ATLaS`;
- lo QLoRA 4-bit NF4;
- kọ́ LoRA adapter dípò kí ó tún gbogbo 8B model kọ́;
- fi adapter sí output directory lọ́tọ̀.

## Speech model

```python
from ednai.speech import asr_model_for

asr_model_for("yoruba")
```

Èyí máa dá `NCAIR1/Yoruba-ASR` padà.
