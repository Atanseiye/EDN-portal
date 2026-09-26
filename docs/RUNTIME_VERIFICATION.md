# EDNAi live N-ATLaS runtime verification

Verified on **26 September 2026**.

## Production path

```
Developer
  -> https://ednai-6znf.onrender.com
  -> EDNAi FastAPI gateway
  -> GradioSpaceProvider
  -> KoladeOdunope/ednai-natlas-runtime
  -> Hugging Face ZeroGPU (zero-a10g)
  -> NCAIR1/N-ATLaS
```

## Runtime provisioning evidence

GitHub Actions workflow: **Provision EDNAi N-ATLaS Runtime**

Verified runtime state:

```text
Space: https://huggingface.co/spaces/KoladeOdunope/ednai-natlas-runtime
Stage: RUNNING
hardware=zero-a10g
requested=zero-a10g
```

The provisioner first verifies gated access to `NCAIR1/N-ATLaS` and is fail-closed to `zero-a10g`; it does not fall back to paid hardware or a substitute foundation model.

## Gateway health evidence

Production `GET /health` returned:

```json
{
  "status": "ok",
  "product": "EDNAi",
  "model": "NCAIR1/N-ATLaS",
  "provider": "gradio_space",
  "provider_configured": true,
  "direct_natlas_integration": true
}
```

## End-to-end inference provenance evidence

GitHub Actions workflow: **EDNAi Live Runtime Smoke**  
Run ID: `36260446935`, attempt 2  
Conclusion: **success**

Production `POST /api/runtime/probe` returned:

```json
{
  "ok": true,
  "model": "NCAIR1/N-ATLaS",
  "provider": "gradio_space",
  "output": "Eureka I have no answer, I know!",
  "latency_ms": 9022.16,
  "provenance_verified": true
}
```

The exact probe text is not used as a quality benchmark. The probe verifies that a real generation request traverses the production EDNAi gateway and returns structured provenance identifying the upstream model as exactly `NCAIR1/N-ATLaS`.

Language quality, instruction-following and domain behaviour are evaluated separately through EDNAi's benchmark/evaluation workbench.

## Security boundary

The Render gateway does **not** receive or forward the Hugging Face account token to the public runtime Space. The Space stores `HF_TOKEN` as a private Hugging Face Space secret solely so the runtime can load the gated official N-ATLaS weights.

EDNAi rejects any upstream response whose model identity is not exactly `NCAIR1/N-ATLaS`.
