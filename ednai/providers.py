from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from .models import Generation, Message

NATLAS_MODEL_ID = "NCAIR1/N-ATLaS"
NATLAS_ASR_MODELS = {
    "english": "NCAIR1/NigerianAccentedEnglish",
    "yoruba": "NCAIR1/Yoruba-ASR",
    "hausa": "NCAIR1/Hausa-ASR",
    "igbo": "NCAIR1/Igbo-ASR",
}


class ProviderError(RuntimeError):
    pass


def assert_natlas_model(model: str) -> str:
    normalized = model.strip()
    if normalized != NATLAS_MODEL_ID:
        raise ProviderError(
            f"EDNAi's qualifying runtime is locked to {NATLAS_MODEL_ID}; "
            f"received {normalized!r}. General-purpose model substitution is not allowed."
        )
    return normalized


class Provider(ABC):
    name = "base"

    @abstractmethod
    def generate(
        self,
        messages: list[Message],
        *,
        model: str = NATLAS_MODEL_ID,
        temperature: float = 0.2,
        max_tokens: int = 512,
        json_mode: bool = False,
    ) -> Generation:
        raise NotImplementedError


class OpenAICompatibleProvider(Provider):
    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.timeout = timeout

    def generate(self, messages: list[Message], *, model=NATLAS_MODEL_ID,
                 temperature=0.2, max_tokens=512, json_mode=False) -> Generation:
        assert_natlas_model(model)
        headers = {"content-type": "application/json"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        started = time.perf_counter()
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
        if response.status_code >= 400:
            raise ProviderError(
                f"N-ATLaS upstream returned HTTP {response.status_code}: {response.text[:500]}"
            )
        raw = response.json()
        try:
            choice = raw["choices"][0]
            text = choice["message"]["content"]
        except Exception as exc:
            raise ProviderError("Unexpected N-ATLaS upstream response shape") from exc
        return Generation(
            text=text,
            model=raw.get("model", model),
            provider=self.name,
            finish_reason=choice.get("finish_reason"),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            usage=raw.get("usage") or {},
            raw=raw,
        )


class GradioSpaceProvider(Provider):
    name = "gradio_space"

    def __init__(self, space_id: str, hf_token: str | None = None):
        self.space_id = space_id
        self.hf_token = hf_token

    def generate(self, messages: list[Message], *, model=NATLAS_MODEL_ID,
                 temperature=0.2, max_tokens=512, json_mode=False) -> Generation:
        assert_natlas_model(model)
        try:
            from gradio_client import Client
        except ImportError as exc:
            raise ProviderError("Install ednai[server] to use a Gradio N-ATLaS runtime") from exc
        started = time.perf_counter()
        client = Client(self.space_id, token=self.hf_token)
        result = client.predict(
            json.dumps([m.model_dump() for m in messages], ensure_ascii=False),
            float(temperature),
            int(max_tokens),
            bool(json_mode),
            api_name="/generate",
        )
        if isinstance(result, str):
            try:
                payload = json.loads(result)
            except json.JSONDecodeError:
                payload = {"text": result}
        else:
            payload = result
        text = payload.get("text") if isinstance(payload, dict) else str(payload)
        if not text:
            raise ProviderError("N-ATLaS Gradio runtime returned no text")
        return Generation(
            text=str(text),
            model=NATLAS_MODEL_ID,
            provider=self.name,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            raw=payload if isinstance(payload, dict) else {"result": payload},
        )


class LocalTransformersProvider(Provider):
    name = "local_transformers"

    def __init__(self, hf_token: str | None = None, device_map: str = "auto"):
        self.hf_token = hf_token
        self.device_map = device_map
        self._model = None
        self._tokenizer = None

    def _load(self):
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise ProviderError("Install ednai[local] to run N-ATLaS locally") from exc
        self._tokenizer = AutoTokenizer.from_pretrained(
            NATLAS_MODEL_ID, token=self.hf_token, use_fast=True
        )
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        self._model = AutoModelForCausalLM.from_pretrained(
            NATLAS_MODEL_ID,
            token=self.hf_token,
            torch_dtype=dtype,
            device_map=self.device_map,
        )
        self._model.eval()

    def generate(self, messages: list[Message], *, model=NATLAS_MODEL_ID,
                 temperature=0.2, max_tokens=512, json_mode=False) -> Generation:
        assert_natlas_model(model)
        self._load()
        started = time.perf_counter()
        tokenizer = self._tokenizer
        model_obj = self._model
        prompt_messages = [m.model_dump() for m in messages]
        if json_mode:
            prompt_messages.insert(
                0,
                {"role": "system", "content": "Return valid JSON only. Do not wrap it in Markdown."},
            )
        if getattr(tokenizer, "chat_template", None):
            prompt = tokenizer.apply_chat_template(
                prompt_messages, tokenize=False, add_generation_prompt=True
            )
        else:
            prompt = "\n".join(f"{m['role']}: {m['content']}" for m in prompt_messages) + "\nassistant:"
        inputs = tokenizer(prompt, return_tensors="pt")
        device = next(model_obj.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        do_sample = temperature > 0
        outputs = model_obj.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=do_sample,
            temperature=max(temperature, 1e-5) if do_sample else None,
            pad_token_id=tokenizer.eos_token_id,
        )
        new_tokens = outputs[0][inputs["input_ids"].shape[-1]:]
        text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        return Generation(
            text=text,
            model=NATLAS_MODEL_ID,
            provider=self.name,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
