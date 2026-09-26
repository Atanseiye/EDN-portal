# EDNAi 3–5 minute demo

## 0:00–0:25 — Problem

"N-ATLaS is downloadable, but downloading an 8B model is not the same as having a developer ecosystem. A team still needs stable APIs, SDKs, testing, evaluation, adaptation and deployment patterns. EDNAi supplies that missing engineering layer."

## 0:25–0:55 — Direct integration

Show `ednai/providers.py` and `runtime/hf_space/app.py`.

Point out:
- `NCAIR1/N-ATLaS` is hard-coded;
- other model IDs are rejected;
- local and hosted paths load/call N-ATLaS directly.

## 0:55–1:35 — Playground

Open the deployed EDNAi playground.

Run:
- an English prompt;
- a Yorùbá prompt;
- JSON mode.

Show provider name, model ID and latency.

## 1:35–2:05 — Python + TypeScript

Terminal:

```bash
ednai chat "Kí ni API?" --base-url <gateway>
```

Show a short Python call and TypeScript call from the docs.

## 2:05–2:35 — Evaluation

Run:

```bash
ednai eval benchmarks/natlas_smoke.jsonl --base-url <gateway> --output report.json
```

Show per-case pass/fail and exported report.

## 2:35–3:05 — Fine-tuning starter

Show:
- dataset normalization;
- `MODEL_ID = "NCAIR1/N-ATLaS"`;
- NF4 quantization;
- LoRA config;
- adapter output.

Do not claim a fine-tuning improvement unless a real held-out benchmark was run.

## 3:05–3:35 — Bilingual docs

Switch from English docs to Yorùbá docs. Show that examples remain runnable.

## 3:35–4:00 — External validation

Open `/challenge`.

Show:
- direct N-ATLaS integration gate;
- two-external-beta-tester gate;
- structured feedback form.

Close with: "EDNAi is infrastructure for Nigerian developers to build on Nigeria's own model."
