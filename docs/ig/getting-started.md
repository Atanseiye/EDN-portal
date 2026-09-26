# EDNAi — Nduzi Mbido maka Developer (Igbo)

EDNAi bụ developer layer maka model gọọmentị `NCAIR1/N-ATLaS`. Ọ na-enye SDK, gateway, evaluation tools, Dataset Studio, fine-tuning starter na runtime tooling.

## Nkwa kachasị mkpa

EDNAi anaghị ekwe ka model ọzọ dochie N-ATLaS. Qualifying inference ga-egosi model ID `NCAIR1/N-ATLaS`.

## Python SDK

```python
from ednai import EDNAi

client = EDNAi(base_url="https://ednai-6znf.onrender.com")
response = client.generate(
    "Kọwaa ihe API bụ.",
    system="Zaa n'Igbo dị mfe.",
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

const result = await ai.generate("Kọwaa API n'Igbo.");
console.log(result.text);
```

## OpenAI-compatible API

```bash
curl -X POST https://ednai-6znf.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"NCAIR1/N-ATLaS",
    "messages":[{"role":"user","content":"Kọwaa transformer attention."}]
  }'
```

## Prompt na JSON mode

Jiri system prompt họrọ asụsụ, ụda olu ma ọ bụ iwu ọrụ. Hapụ JSON mode gbanyụrụ maka azịza nkịtị. Gbanye ya naanị mgbe application chọrọ JSON ahaziri nke ọma.

## Evaluation

```bash
ednai eval benchmarks/natlas_smoke.jsonl \
  --base-url https://ednai-6znf.onrender.com
```

Evaluation Workbench nwere ike nyochaa required strings, forbidden strings, JSON validity na latency. Maka semantic quality, tinye human review ma ọ bụ metric dabara na task.

## Dataset Studio

Dataset Studio na-anabata:
- chat-format `messages[]`;
- instruction/input/output JSONL.

Ọ na-validate row ọ bụla, na-normalize dataset ma wepụta training-ready JSONL.

## Fine-tuning

```bash
python fine_tuning/prepare_data.py --input raw.jsonl --output prepared.jsonl
python fine_tuning/train_qlora.py \
  --dataset prepared.jsonl \
  --output-dir outputs/my-natlas-adapter
```

QLoRA starter na-emepụta adapter kpọmkwem site na `NCAIR1/N-ATLaS`.

## Runtime modes

- **ZeroGPU** — hosted runtime maka development/demo; free quota nwere ike ịbanye queue ma ọ bụ gwụ nwa oge.
- **Local Transformers** — load official N-ATLaS weights na machine ma ọ bụ server gị.
- **OpenAI-compatible N-ATLaS** — jikọọ EDNAi na endpoint nke na-arụ N-ATLaS n'ezie.

## Runtime verification

```bash
curl -X POST https://ednai-6znf.onrender.com/api/runtime/probe
```

Probe a na-enyocha provenance model ma fail ma ọ bụrụ na upstream model abụghị `NCAIR1/N-ATLaS`.


## Speech Studio na official ASR

EDNAi na-enye developer official NCAIR speech-recognition models site na gateway, SDK, CLI na Speech Studio.

```python
result = client.transcribe("audio.wav", language="igbo")
print(result.text)
print(result.model)
```

EDNAi na-enyocha model ID runtime weghachiri ka ọ kwekọọ na asụsụ ahọpụtara; ọ naghị ekwe ASR model substitution.

## Speech models

- Nigerian English — `NCAIR1/NigerianAccentedEnglish`
- Yorùbá — `NCAIR1/Yoruba-ASR`
- Hausa — `NCAIR1/Hausa-ASR`
- Igbo — `NCAIR1/Igbo-ASR`
