# N-ATLaS integration evidence

## Purpose

This document is the technical evidence for the NAIC requirement that PowerRights genuinely integrates with N-ATLaS.

## Official models

| Function | Official model |
| --- | --- |
| Multilingual answer generation | `NCAIR1/N-ATLaS` |
| Nigerian-accented English ASR | `NCAIR1/NigerianAccentedEnglish` |
| Yorùbá ASR | `NCAIR1/Yoruba-ASR` |
| Hausa ASR | `NCAIR1/Hausa-ASR` |
| Igbo ASR | `NCAIR1/Igbo-ASR` |

## Runtime flow

1. Browser captures a real user's voice.
2. `POST /api/v1/voice/advice` receives the audio and selected language.
3. `NAtlasASR` maps the language to the official NCAIR model.
4. The transcript is passed into the same grounded consumer-rights pipeline used by typed input.
5. Official regulatory facts are retrieved from the versioned knowledge base.
6. `NAtlasClient` receives the user question plus verified context and is instructed to answer the question directly in the user's language.
7. The answer is checked for directness; unsupported regulatory claims are not accepted.
8. The response includes the relevant regulator route and sources.
9. If explicit validation consent was provided, an anonymous evidence event is produced.

## Deployment implementations

### Gradio Space / ZeroGPU

- LLM package: `hf_spaces/llm/`
- ASR package: `hf_spaces/asr/`
- Render adapter: `gradio_client`

Expected environment:

```
NATLAS_PROVIDER=gradio_space
NATLAS_SPACE_ID=<username>/<space>
ASR_PROVIDER=gradio_space
ASR_SPACE_ID=<username>/<space>
```

### Local GPU / partner compute

The repository also supports direct Transformers loading and an OpenAI-compatible N-ATLaS endpoint.

## Anti-fake safeguards

- `grounded_rules` is explicitly non-qualifying.
- `mock` is explicitly non-qualifying.
- disabled ASR cannot accept voice.
- voice validation only counts if the model configuration is challenge-valid.
- validation consent is required.
- `/api/v1/challenge/readiness` remains false until the official paths are active and the real-user target is reached.

## Verification procedure

Before collecting challenge evidence:

1. open `/health`;
2. verify the N-ATLaS provider is not mock/grounded fallback;
3. open `/api/v1/challenge/readiness`;
4. verify both official model checks are true;
5. record a voice sample in each language;
6. capture the transcript/result and corresponding structured validation event;
7. retain screenshots/log excerpts for the submission evidence folder.

Do not describe the fallback engine as N-ATLaS output.
