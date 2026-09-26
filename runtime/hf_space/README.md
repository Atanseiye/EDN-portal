---
title: EDNAi N-ATLaS Runtime
emoji: 🇳🇬
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
---

# EDNAi N-ATLaS Runtime

This Space directly loads `NCAIR1/N-ATLaS` and exposes the `/generate` Gradio API used by the EDNAi gateway.

Configure the Space secret:

- `HF_TOKEN`: a Hugging Face token with accepted access to `NCAIR1/N-ATLaS`.

Select **ZeroGPU** hardware. Do not substitute another foundation model.
