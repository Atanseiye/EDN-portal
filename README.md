# PowerRights NG

**NAIC 2026 — Innovation & Enterprise — Voice-First Access**

PowerRights NG is a voice-first Nigerian electricity-consumer rights and complaint-navigation application designed to run on Nigeria's official N-ATLaS language stack.

**Live application:** https://powerrights-ng.onrender.com  
**Live challenge readiness:** https://powerrights-ng.onrender.com/challenge  
**API docs:** https://powerrights-ng.onrender.com/docs

## Problem

Electricity consumers often know that something is wrong — a faulty or removed meter, estimated billing, disconnection, supply-quality problem, tariff-band dispute, failed token or delayed connection — but do not know the applicable consumer protection, the first complaint step, or the correct escalation body.

PowerRights allows a user to speak or type the problem in Nigerian English, Yorùbá, Hausa or Igbo. The system answers the actual question first, grounds regulatory claims in verified electricity sources, gives actionable next steps, identifies the correct federal/state regulator path and can generate a formal complaint.

## Challenge architecture

Voice → official N-ATLaS ASR for selected language → complaint/intention analysis → verified regulatory retrieval → N-ATLaS grounded answer → state-aware escalation → feedback/validation evidence.

Official model IDs:

- LLM: `NCAIR1/N-ATLaS`
- Nigerian English ASR: `NCAIR1/NigerianAccentedEnglish`
- Yorùbá ASR: `NCAIR1/Yoruba-ASR`
- Hausa ASR: `NCAIR1/Hausa-ASR`
- Igbo ASR: `NCAIR1/Igbo-ASR`

The application refuses to count fallback or mock traffic as challenge-valid interactions.

## Features

- voice and typed complaints;
- English, Yorùbá, Hausa and Igbo;
- typed-language auto-detection and same-language responses;
- direct query answering, including multi-part questions;
- issue-specific consumer-rights guidance;
- official-source citations;
- NERC/state-regulator routing;
- formal complaint generation;
- explicit validation consent;
- anonymous validation evidence;
- live NAIC readiness dashboard;
- responsive installable PWA;
- automated regression tests;
- free-tier deployment.

## Submission evidence

See:

- `docs/CHALLENGE_MAPPING.md`
- `docs/NATLAS_INTEGRATION_EVIDENCE.md`
- `docs/TECHNICAL_DOCUMENTATION.md`
- `docs/REAL_USER_VALIDATION.md`
- `docs/VALIDATION_REPORT_TEMPLATE.md`
- `docs/DEMO_VIDEO_SCRIPT.md`
- `docs/TEAM_PROFILE.md`
- `docs/IMPACT_SCALABILITY.md`
- `docs/SUBMISSION_CHECKLIST.md`

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
pytest -q
```

## Production providers

Development fallback:

```
NATLAS_PROVIDER=grounded_rules
ASR_PROVIDER=disabled
```

Challenge-valid ZeroGPU configuration:

```
NATLAS_PROVIDER=gradio_space
NATLAS_SPACE_ID=<account>/<natlas-llm-space>
ASR_PROVIDER=gradio_space
ASR_SPACE_ID=<account>/<natlas-asr-space>
```

See `docs/ZEROGPU_ACTIVATION.md`.

## Attribution

N-ATLaS is an initiative of the Federal Ministry of Communications, Innovation and Digital Economy, and powered by Awarri Technologies.

PowerRights NG is an independent civic-information application. It is not NERC, a State Electricity Regulatory Commission, a DisCo or a law firm.
