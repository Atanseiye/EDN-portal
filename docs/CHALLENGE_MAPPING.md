# NAIC 2026 challenge mapping

## Submission choice

- Track: Innovation & Enterprise
- Problem statement: Voice-First Access
- Product: PowerRights NG
- Delivery: low-bandwidth mobile-first PWA with voice capture
- Domain: civic information / consumer electricity rights

## Mandatory build requirements

### 1. Working technical build

Evidence:
- live application;
- FastAPI backend;
- browser voice capture;
- mobile-first UI;
- complaint drafting;
- source cards;
- regulator routing;
- automated CI.

### 2. Genuine N-ATLaS integration

Code paths:
- `app/services/natlas.py`
- `app/services/asr.py`
- `hf_spaces/llm/`
- `hf_spaces/asr/`

The readiness endpoint does not treat `grounded_rules`, `mock` or disabled ASR as qualifying integration.

### 3. Real-world validation

The Voice-First requirement is a minimum of 50 documented real-user interactions.

PowerRights requires:
- voice channel;
- explicit consent;
- challenge-valid N-ATLaS LLM;
- challenge-valid official N-ATLaS ASR;
- unique anonymous interaction ID;
- structured audit record.

Non-qualifying test traffic is excluded.

## Seven submission components

1. Working Artefact — live app + repository.
2. N-ATLaS Integration Evidence — `docs/NATLAS_INTEGRATION_EVIDENCE.md`.
3. Real-World Validation — validation logs/export + final report.
4. Technical Documentation — `docs/TECHNICAL_DOCUMENTATION.md`.
5. Video Demonstration — `docs/DEMO_VIDEO_SCRIPT.md`.
6. Team Profile — `docs/TEAM_PROFILE.md`.
7. Registration/ID — attach CAC certificate or valid applicant ID in the application portal; do not commit identity documents to this public repository.

## Judging criteria mapping

- Working Artefact & Technical Rigour: deployed API/PWA, tests, fail-closed model gates, deterministic routing.
- N-ATLaS Integration: official LLM and language-specific ASR adapters.
- Real-World Validation: consented real-user evidence with explicit eligibility flag.
- Impact Potential: consumer rights, billing/metering access and Nigerian-language accessibility.
- Scalability & Sustainability: stateless app layer, external model services, versioned knowledge and nationwide regulator routing.
- Team Capability: documented roles and engineering/research responsibilities.
