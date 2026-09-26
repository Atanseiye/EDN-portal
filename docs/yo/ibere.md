# EDNAi — Ìbẹ̀rẹ̀ fún Developer (Yorùbá)

EDNAi jẹ́ developer layer fún model osise `NCAIR1/N-ATLaS`. Ó ń fún developer ní SDK, gateway, evaluation tools, Dataset Studio, fine-tuning starter àti runtime tooling.

## Ìlérí pàtàkì

EDNAi kò gba model míì láti rọ́pò N-ATLaS. Qualifying inference gbọ́dọ̀ fi model ID `NCAIR1/N-ATLaS` hàn.

## Python SDK

```python
from ednai import EDNAi

client = EDNAi(base_url="https://ednai-6znf.onrender.com")
response = client.generate(
    "Ṣàlàyé ohun tí API jẹ́.",
    system="Dáhùn ní Yorùbá tó rọrùn.",
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

const result = await ai.generate("Kí ni API?");
console.log(result.text);
```

## OpenAI-compatible API

```bash
curl -X POST https://ednai-6znf.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"NCAIR1/N-ATLaS",
    "messages":[{"role":"user","content":"Ṣàlàyé transformer attention."}]
  }'
```

## Prompt àti JSON mode

Lo system prompt láti sọ èdè, tone tàbí constraint. Má tan JSON mode fún prose deede. Tan-an nígbà tí application bá nílò JSON tó ṣeé ka lọ́nà machine.

## Evaluation

```bash
ednai eval benchmarks/natlas_smoke.jsonl \
  --base-url https://ednai-6znf.onrender.com
```

Evaluation Workbench lè ṣàyẹ̀wò required strings, forbidden strings, JSON validity àti latency. Fún semantic quality, fi human review tàbí metric tó bá task mu kún un.

## Dataset Studio

Dataset Studio gba:
- chat-format `messages[]`;
- instruction/input/output JSONL.

Ó ń validate row kọ̀ọ̀kan, normalize dataset, ó sì ń ṣẹ̀dá training-ready JSONL.

## Fine-tuning

```bash
python fine_tuning/prepare_data.py --input raw.jsonl --output prepared.jsonl
python fine_tuning/train_qlora.py \
  --dataset prepared.jsonl \
  --output-dir outputs/my-natlas-adapter
```

QLoRA starter náà ń ṣẹ̀dá adapter láti `NCAIR1/N-ATLaS` gan-an.

## Runtime modes

- **ZeroGPU** — hosted runtime fún development/demo; free quota lè queue tàbí tán fún ìgbà díẹ̀.
- **Local Transformers** — load official N-ATLaS weights lórí machine/server tirẹ.
- **OpenAI-compatible N-ATLaS** — so EDNAi mọ́ endpoint tó ń ṣiṣẹ́ N-ATLaS gidi.

## Runtime verification

```bash
curl -X POST https://ednai-6znf.onrender.com/api/runtime/probe
```

Probe yìí ń jẹ́risi provenance model, ó sì máa fail bí upstream model kì í ṣe `NCAIR1/N-ATLaS`.


## Speech Studio àti ASR osise

EDNAi ń fún developer ní àwọn speech-recognition model osise NCAIR ní gateway, SDK, CLI àti Speech Studio.

```python
result = client.transcribe("audio.wav", language="yoruba")
print(result.text)
print(result.model)
```

EDNAi máa ń ṣàyẹ̀wò model ID tí runtime dá padà kí ó bá èdè tí a yàn mu; kò gba ASR model substitution.

## Ààlà TTS

NCAIR kò tíì ṣe official N-ATLaS TTS checkpoint. EDNAi yà speech synthesis sọ́tọ̀ kúrò ní qualifying N-ATLaS provenance. Speech Studio máa ń lo browser/device voice tó bá Yorùbá mu nígbà tí voice bẹ́ẹ̀ bá wà; kò ní fi voice èdè míì rọ́pò rẹ̀ láì sọ.

```ts
await ai.speak("Ẹ káàbọ̀ sí EDNAi.", "yoruba");
```

## Speech models

- Nigerian English — `NCAIR1/NigerianAccentedEnglish`
- Yorùbá — `NCAIR1/Yoruba-ASR`
- Hausa — `NCAIR1/Hausa-ASR`
- Igbo — `NCAIR1/Igbo-ASR`
