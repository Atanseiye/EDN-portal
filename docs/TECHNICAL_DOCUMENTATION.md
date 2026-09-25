# Technical documentation

## System overview

PowerRights NG is a mobile-first FastAPI/PWA application for Nigerian electricity-consumer information.

### Components

**Client**
- responsive HTML/CSS/JavaScript;
- microphone capture with MediaRecorder;
- typed language detection;
- same-language UI;
- installable PWA shell and static caching;
- explicit validation consent.

**API**
- FastAPI;
- structured Pydantic request/response contracts;
- voice and text endpoints;
- complaint drafting;
- challenge-readiness endpoint;
- admin validation export.

**Language stack**
- official N-ATLaS language-specific ASR adapter;
- official N-ATLaS LLM adapter;
- fail-closed behavior for unavailable official ASR;
- deterministic verified-grounded fallback for non-challenge text testing.

**Knowledge**
- curated/versioned official electricity consumer facts;
- issue-aware retrieval;
- source URLs/excerpts;
- state electricity regulator directory.

**Validation**
- random interaction IDs;
- hashed browser session IDs;
- no audio storage by default;
- no transcript content in challenge validation events;
- explicit consent flag;
- exact `competition_model_path` eligibility flag.

## Architecture

```
Mobile browser / PWA
        |
        +-- typed input -------------------------+
        |                                       |
        +-- voice -> official N-ATLaS ASR ------+
                                                |
                                      issue + intent analysis
                                                |
                                      official-source retrieval
                                                |
                                      N-ATLaS grounded answer
                                                |
                                  directness / safety quality gate
                                                |
                          state-aware complaint & escalation routing
                                                |
                answer + rights + next steps + sources + complaint draft
                                                |
                            anonymous validation/audit evidence
```

## Important API routes

- `GET /` — product
- `GET /challenge` — live challenge-readiness dashboard
- `GET /health`
- `GET /api/v1/challenge/readiness`
- `POST /api/v1/advice`
- `POST /api/v1/voice/advice`
- `POST /api/v1/complaint`
- `POST /api/v1/feedback`
- `GET /api/v1/admin/validation/stats`
- `GET /api/v1/admin/validation/export.csv`

## Safety and grounding

Regulatory facts are not generated from memory alone. The model receives verified context and is instructed not to invent rights, tariffs, timelines, contacts or procedures. Regulator routing is deterministic.

If a question cannot be answered from available verified material, the application should say so rather than invent a rule.

## Language behavior

For typed input, clear Yorùbá/Hausa/Igbo language signals override a stale dropdown selection. For voice, the selected ASR language is authoritative because the correct official speech model must be selected before transcription.

Output language follows effective input language.

## Privacy

Validation records intentionally exclude raw audio and transcript content. Do not enter PINs, passwords or payment-card data.

## Testing

CI runs on Python 3.11. Tests cover:
- billing vs metering response variation;
- direct-question answering;
- complaint timelines;
- meter replacement responsibility;
- state regulator escalation;
- compound questions;
- same-language Yorùbá/Hausa/Igbo output;
- stale-selector language correction;
- challenge-validation counting safeguards.

## Deployment

Current application hosting is configured on Render free tier. N-ATLaS inference is designed to run on zero-cost/credit-backed official or Hugging Face GPU infrastructure rather than pretending an 8B model can run on the small free web process.
