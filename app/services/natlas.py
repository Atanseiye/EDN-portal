import asyncio
import json
from datetime import datetime
import httpx
from app.config import Settings


class NAtlasError(RuntimeError):
    pass


class NAtlasClient:
    """Adapter for the official N-ATLaS LLM."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._local = None
        self._space_client = None

    async def generate_json(self, system: str, user: str) -> dict:
        provider = self.settings.natlas_provider.lower()
        if provider == "gradio_space":
            return await self._gradio_space(system, user)
        if provider == "openai_compatible":
            return await self._openai_compatible(system, user)
        if provider == "local":
            return await self._local_transformers(system, user)
        if provider in {"mock", "grounded_rules", "disabled", ""}:
            raise NAtlasError("Official N-ATLaS inference is not active on this deployment")
        raise NAtlasError(f"Unsupported NATLAS_PROVIDER={provider}")

    async def _gradio_space(self, system: str, user: str) -> dict:
        if not self.settings.natlas_space_id:
            raise NAtlasError("NATLAS_SPACE_ID is not configured")
        try:
            from gradio_client import Client
            if self._space_client is None:
                self._space_client = Client(self.settings.natlas_space_id)
            result = await asyncio.to_thread(
                self._space_client.predict,
                system=system,
                user=user,
                api_name="/generate_json",
            )
        except Exception as exc:
            raise NAtlasError(f"N-ATLaS ZeroGPU request failed: {exc}") from exc
        if isinstance(result, dict):
            return result
        return _extract_json(str(result))

    async def _openai_compatible(self, system: str, user: str) -> dict:
        url = self.settings.natlas_base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.settings.natlas_api_key:
            headers["Authorization"] = f"Bearer {self.settings.natlas_api_key}"
        payload = {
            "model": self.settings.natlas_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "max_tokens": 900,
        }
        async with httpx.AsyncClient(timeout=self.settings.natlas_timeout_seconds) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
        return _extract_json(text)

    async def _local_transformers(self, system: str, user: str) -> dict:
        if self._local is None:
            try:
                import torch
                from transformers import AutoTokenizer, AutoModelForCausalLM
            except ImportError as exc:
                raise NAtlasError("Install requirements-gpu.txt for local N-ATLaS inference") from exc
            tokenizer = AutoTokenizer.from_pretrained(
                self.settings.natlas_model,
                token=self.settings.hf_token or None,
            )
            model = AutoModelForCausalLM.from_pretrained(
                self.settings.natlas_model,
                token=self.settings.hf_token or None,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto",
            )
            self._local = (tokenizer, model)
        tokenizer, model = self._local
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        rendered = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
            date_string=datetime.now().strftime("%d %b %Y"),
        )
        inputs = tokenizer(rendered, return_tensors="pt", add_special_tokens=False).to(model.device)
        outputs = model.generate(**inputs, max_new_tokens=900, temperature=0.1, do_sample=False, repetition_penalty=1.08)
        generated = outputs[0][inputs["input_ids"].shape[-1]:]
        text = tokenizer.decode(generated, skip_special_tokens=True)
        return _extract_json(text)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise NAtlasError("N-ATLaS did not return JSON")
    return json.loads(text[start:end+1])
