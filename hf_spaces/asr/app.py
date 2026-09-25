import os

import spaces
import gradio as gr
import torch
from transformers import pipeline

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN Space secret is required for the gated N-ATLaS ASR models.")

MODEL_BY_LANGUAGE = {
    "english": "NCAIR1/NigerianAccentedEnglish",
    "yoruba": "NCAIR1/Yoruba-ASR",
    "hausa": "NCAIR1/Hausa-ASR",
    "igbo": "NCAIR1/Igbo-ASR",
}

# ZeroGPU supports CUDA placement at module startup through CUDA emulation.
pipes = {
    language: pipeline(
        "automatic-speech-recognition",
        model=model_id,
        token=HF_TOKEN,
        torch_dtype=torch.float16,
        device="cuda",
    )
    for language, model_id in MODEL_BY_LANGUAGE.items()
}


@spaces.GPU(duration=45)
def transcribe(audio: str, language: str) -> str:
    if not audio:
        raise gr.Error("Audio is required.")
    if language not in pipes:
        raise gr.Error("Unsupported language.")
    result = pipes[language](audio)
    text = result["text"].strip()
    if not text:
        raise gr.Error("The official N-ATLaS ASR returned an empty transcript.")
    return text


with gr.Blocks(title="PowerRights N-ATLaS ASR") as demo:
    gr.Markdown(
        "# 🎙️ PowerRights N-ATLaS ASR\n"
        "Official N-ATLaS speech recognition for English, Yorùbá, Hausa and Igbo."
    )
    audio = gr.Audio(type="filepath", label="Voice complaint")
    language = gr.Dropdown(
        choices=["english", "yoruba", "hausa", "igbo"],
        value="english",
        label="Language",
    )
    output = gr.Textbox(label="Transcript")
    btn = gr.Button("Transcribe")
    btn.click(transcribe, inputs=[audio, language], outputs=output, api_name="transcribe")

demo.queue(default_concurrency_limit=1).launch()
