# EDNAi N-ATLaS Use Case Studio

EDNAi turns the published N-ATLaS application patterns into reusable developer workflows. Every generation request in this document is executed through the provenance-locked `NCAIR1/N-ATLaS` runtime.

## Discovery

```http
GET /v1/use-cases
```

The response contains the eight workflow definitions, supported languages, required fields, defaults and safe example inputs. The same registry drives the hosted Use Case Studio.

## Execution

```http
POST /v1/use-cases/{use_case}
Content-Type: application/json
```

Shared request shape:

```json
{
  "language": "yoruba",
  "inputs": {},
  "temperature": null,
  "max_tokens": null,
  "json_mode": false
}
```

The server builds a task-specific system/user prompt, sends it to `NCAIR1/N-ATLaS`, and returns the normal generation provenance plus `use_case` and `language`.

## Workflows

| Slug | Workflow | Purpose |
| --- | --- | --- |
| `chatbot` | Multilingual Chatbot | Conversational assistants in supported Nigerian languages |
| `translation` | Content Translation | English ↔ Yorùbá/Hausa/Igbo translation with structure preservation |
| `education` | Educational Tools | Lessons, study notes and quizzes matched to learner level |
| `culture` | Cultural Preservation | Document supplied oral-history/linguistic material without inventing missing facts |
| `government` | Government Services | Explain supplied public-service information neutrally; specific requirements must be grounded in authoritative context |
| `digital_inclusion` | Digital Inclusion | Simplify complex instructions into accessible local-language guidance |
| `research` | Research Applications | Analyse supplied material while separating evidence, inference and uncertainty |
| `song` | Song Generation | Generate original song lyrics as text in a supported language |

## Python

```python
from ednai import EDNAi

ai = EDNAi(base_url="https://ednai-6znf.onrender.com")

result = ai.run_use_case(
    "education",
    {
        "topic": "Photosynthesis",
        "learner_level": "JSS 2 / beginner",
        "objective": "Explain how plants make food.",
        "format": "lesson_quiz",
    },
    language="english",
)

print(result.text)
print(result.model)
```

## TypeScript

```ts
const result = await ai.runUseCase(
  "digital_inclusion",
  {
    content: "Enable two-factor authentication and keep your verification code private.",
    audience: "first-time smartphone user",
    channel: "whatsapp"
  },
  { language: "hausa" }
);

console.log(result.text);
```

## CLI

```bash
ednai use-cases --base-url https://ednai-6znf.onrender.com

ednai use-case education \
  --language english \
  --inputs '{"topic":"Photosynthesis","learner_level":"JSS 2","objective":"Explain how plants make food.","format":"lesson_quiz"}' \
  --base-url https://ednai-6znf.onrender.com
```

## Guardrails built into the workflows

Translation preserves names, numbers and structure. Cultural-preservation prompts distinguish supplied material from interpretation and mark uncertainty. Government-service prompts require supplied authoritative context for specific eligibility, fees, dates, documents or procedures. Research prompts forbid fabricated citations or evidence. Song generation requests original lyrics and explicitly remains text-only.

These workflow-level constraints improve developer ergonomics but do not replace application-specific evaluation, human review or authoritative data sources.
