---
title: EDNAi N-ATLaS Runtime
emoji: 🤖
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


## Speech API

The Space exposes a Gradio `/transcribe` endpoint used by the EDNAi gateway.

Inputs:

1. audio file
2. canonical language: `english`, `yoruba`, `hausa`, or `igbo`

The response is structured JSON containing `text`, `model`, `language`, and `provider`. The gateway rejects a response whose model ID does not match the official model registered for the chosen language.
