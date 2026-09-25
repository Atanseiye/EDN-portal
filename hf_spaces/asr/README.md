---
title: PowerRights N-ATLaS ASR
emoji: 🎙️
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: 5.47.2
python_version: "3.12"
app_file: app.py
pinned: false
license: other
---

# PowerRights N-ATLaS ASR

ZeroGPU inference service for the four official N-ATLaS ASR models used by PowerRights NG:

- `NCAIR1/Yoruba-ASR`
- `NCAIR1/Hausa-ASR`
- `NCAIR1/Igbo-ASR`
- `NCAIR1/NigerianAccentedEnglish`

Required Space secret: `HF_TOKEN` from a Hugging Face account that has accepted each gated model's terms.

Required hardware: **ZeroGPU (free)**.
