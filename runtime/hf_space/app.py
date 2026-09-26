from __future__ import annotations

import json
import os

import spaces
import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "NCAIR1/N-ATLaS"
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise RuntimeError(
        "HF_TOKEN Space secret is required. Accept access to NCAIR1/N-ATLaS first."
    )

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    token=HF_TOKEN,
    use_fast=True,
)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    token=HF_TOKEN,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    attn_implementation="sdpa",
)
model.eval()
model.to("cuda")


@spaces.GPU(duration=120)
def generate(
    messages_json: str,
    temperature: float = 0.2,
    max_tokens: int = 512,
    json_mode: bool = False,
) -> str:
    try:
        messages = json.loads(messages_json)
    except json.JSONDecodeError as exc:
        raise gr.Error("messages_json must contain a JSON array") from exc

    if not isinstance(messages, list) or not messages:
        raise gr.Error("At least one chat message is required.")

    normalized = []
    for message in messages:
        if not isinstance(message, dict):
            raise gr.Error("Each message must be an object.")
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()
        if role not in {"system", "user", "assistant"} or not content:
            raise gr.Error("Messages require a valid role and non-empty content.")
        normalized.append({"role": role, "content": content})

    if json_mode:
        normalized.insert(
            0,
            {
                "role": "system",
                "content": "Return valid JSON only. Do not wrap JSON in Markdown fences.",
            },
        )

    if getattr(tokenizer, "chat_template", None):
        prompt = tokenizer.apply_chat_template(
            normalized,
            tokenize=False,
            add_generation_prompt=True,
        )
    else:
        prompt = "\n".join(
            f"{item['role']}: {item['content']}" for item in normalized
        ) + "\nassistant:"

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    do_sample = float(temperature) > 0
    kwargs = {
        "max_new_tokens": min(int(max_tokens), 2048),
        "do_sample": do_sample,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if do_sample:
        kwargs["temperature"] = max(float(temperature), 1e-5)
        kwargs["top_p"] = 0.95

    with torch.inference_mode():
        output = model.generate(**inputs, **kwargs)

    new_tokens = output[0][inputs["input_ids"].shape[-1]:]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    return json.dumps(
        {"text": text, "model": MODEL_ID, "provider": "ednai_zerogpu"},
        ensure_ascii=False,
    )


with gr.Blocks(title="EDNAi N-ATLaS Runtime") as demo:
    gr.Markdown(
        "# EDNAi N-ATLaS Runtime\n"
        "Direct inference runtime for `NCAIR1/N-ATLaS`. "
        "The EDNAi gateway calls this Space through its `/generate` API."
    )
    messages = gr.Textbox(
        label="Messages JSON",
        value='[{"role":"user","content":"What is N-ATLaS?"}]',
        lines=7,
    )
    with gr.Row():
        temperature = gr.Slider(0, 2, value=0.2, step=0.1, label="Temperature")
        max_tokens = gr.Slider(1, 2048, value=512, step=1, label="Max tokens")
    json_mode = gr.Checkbox(label="JSON mode", value=False)
    output = gr.Textbox(label="Runtime response", lines=8)
    run = gr.Button("Generate")
    run.click(
        generate,
        inputs=[messages, temperature, max_tokens, json_mode],
        outputs=output,
        api_name="generate",
    )

demo.queue(default_concurrency_limit=1).launch()
