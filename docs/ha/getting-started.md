# EDNAi — Jagorar Farawa ga Developer (Hausa)

EDNAi developer layer ne domin model na hukuma `NCAIR1/N-ATLaS`. Yana ba developer SDK, gateway, evaluation tools, Dataset Studio, fine-tuning starter da runtime tooling.

## Muhimmin garanti

EDNAi baya yarda a maye gurbin N-ATLaS da wani model. Qualifying inference dole ya tabbatar da model ID `NCAIR1/N-ATLaS`.

## Python SDK

```python
from ednai import EDNAi

client = EDNAi(base_url="https://ednai-6znf.onrender.com")
response = client.generate(
    "Ka bayyana menene API.",
    system="Ka amsa da Hausa mai sauƙi.",
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
    "messages":[{"role":"user","content":"Ka bayyana transformer attention."}]
  }'
```

## Prompt da JSON mode

Yi amfani da system prompt domin saita harshe, salo ko ƙa'ida. Ka bar JSON mode a kashe don amsar rubutu ta al'ada. Ka kunna shi ne idan application yana bukatar JSON mai tsari.

## Evaluation

```bash
ednai eval benchmarks/natlas_smoke.jsonl \
  --base-url https://ednai-6znf.onrender.com
```

Evaluation Workbench na iya duba required strings, forbidden strings, JSON validity da latency. Don semantic quality, ƙara human review ko metric da ya dace da task.

## Dataset Studio

Dataset Studio yana karɓar:
- chat-format `messages[]`;
- instruction/input/output JSONL.

Yana validate kowace row, yana normalize dataset sannan ya fitar da training-ready JSONL.

## Fine-tuning

```bash
python fine_tuning/prepare_data.py --input raw.jsonl --output prepared.jsonl
python fine_tuning/train_qlora.py \
  --dataset prepared.jsonl \
  --output-dir outputs/my-natlas-adapter
```

QLoRA starter yana ƙirƙirar adapter kai tsaye daga `NCAIR1/N-ATLaS`.

## Runtime modes

- **ZeroGPU** — hosted runtime don development/demo; free quota na iya yin queue ko ƙarewa na ɗan lokaci.
- **Local Transformers** — load official N-ATLaS weights a machine ko server naka.
- **OpenAI-compatible N-ATLaS** — haɗa EDNAi da endpoint da ke hidimar N-ATLaS na gaske.

## Runtime verification

```bash
curl -X POST https://ednai-6znf.onrender.com/api/runtime/probe
```

Probe ɗin yana tabbatar da provenance na model kuma zai fail idan upstream model ba `NCAIR1/N-ATLaS` ba ne.


## Speech Studio da official ASR

EDNAi yana ba developer official NCAIR speech-recognition models ta gateway, SDK, CLI da Speech Studio.

```python
result = client.transcribe("audio.wav", language="hausa")
print(result.text)
print(result.model)
```

EDNAi yana tabbatar da model ID da runtime ya dawo da shi ya dace da harshen da aka zaɓa; baya yarda da ASR model substitution.

## Speech models

- Nigerian English — `NCAIR1/NigerianAccentedEnglish`
- Yorùbá — `NCAIR1/Yoruba-ASR`
- Hausa — `NCAIR1/Hausa-ASR`
- Igbo — `NCAIR1/Igbo-ASR`
