import os
import json
from datetime import datetime

import spaces
import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "NCAIR1/N-ATLaS"
HF_TOKEN = os.environ.get("HF_TOKEN")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN Space secret is required for the gated N-ATLaS model.")

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    token=HF_TOKEN,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
).to("cuda")
model.eval()


@spaces.GPU(duration=90)
def generate_json(system: str, user: str) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    rendered = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=False,
        date_string=datetime.now().strftime("%d %b %Y"),
    )
    inputs = tokenizer(rendered, return_tensors="pt", add_special_tokens=False).to("cuda")
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=900,
            do_sample=False,
            temperature=None,
            top_p=None,
            repetition_penalty=1.08,
            use_cache=True,
        )
    generated = outputs[0][inputs["input_ids"].shape[-1]:]
    text = tokenizer.decode(generated, skip_special_tokens=True).strip()
    # Validate that the model produced a JSON object before returning to PowerRights.
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise gr.Error("N-ATLaS response did not contain JSON.")
    payload = json.loads(text[start:end + 1])
    return json.dumps(payload, ensure_ascii=False)


with gr.Blocks(title="PowerRights N-ATLaS LLM") as demo:
    gr.Markdown(
        "# ⚡ PowerRights N-ATLaS LLM\n"
        "Official N-ATLaS inference service for the PowerRights NG challenge build."
    )
    system = gr.Textbox(label="System prompt", lines=5)
    user = gr.Textbox(label="User/context", lines=8)
    output = gr.Textbox(label="JSON response", lines=12)
    btn = gr.Button("Generate")
    btn.click(generate_json, inputs=[system, user], outputs=output, api_name="generate_json")

demo.queue(default_concurrency_limit=1).launch()
