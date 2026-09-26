from __future__ import annotations

from pathlib import Path
from typing import Iterable

import httpx

from .models import Generation, Message, Transcription
from .providers import NATLAS_MODEL_ID
from .speech import normalize_speech_language


def _messages(prompt: str | None = None, messages: Iterable[Message | dict] | None = None,
              system: str | None = None) -> list[dict]:
    out: list[dict] = []
    if system:
        out.append({"role": "system", "content": system})
    if messages:
        for item in messages:
            out.append(item.model_dump() if isinstance(item, Message) else dict(item))
    elif prompt is not None:
        out.append({"role": "user", "content": prompt})
    else:
        raise ValueError("Provide prompt or messages")
    return out


class EDNAi:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def generate(self, prompt: str | None = None, *, messages=None, system=None,
                 temperature=0.2, max_tokens=512, json_mode=False) -> Generation:
        headers = {"authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {
            "model": NATLAS_MODEL_ID,
            "messages": _messages(prompt, messages, system),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "json_mode": json_mode,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/v1/generate", json=payload, headers=headers)
        response.raise_for_status()
        return Generation.model_validate(response.json())

    def models(self) -> list[dict]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/v1/models")
        response.raise_for_status()
        return response.json()["data"]

    def transcribe(self, audio_path: str | Path, language: str) -> Transcription:
        language = normalize_speech_language(language)
        path = Path(audio_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        headers = {"authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        with path.open("rb") as audio, httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/v1/audio/transcriptions",
                headers=headers,
                data={"language": language},
                files={"file": (path.name, audio, "application/octet-stream")},
            )
        response.raise_for_status()
        return Transcription.model_validate(response.json())

    def speech_capabilities(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/v1/audio/capabilities")
        response.raise_for_status()
        return response.json()

    def health(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()


class AsyncEDNAi:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 120):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def generate(self, prompt: str | None = None, *, messages=None, system=None,
                       temperature=0.2, max_tokens=512, json_mode=False) -> Generation:
        headers = {"authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {
            "model": NATLAS_MODEL_ID,
            "messages": _messages(prompt, messages, system),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "json_mode": json_mode,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/v1/generate", json=payload, headers=headers)
        response.raise_for_status()
        return Generation.model_validate(response.json())


    async def transcribe(self, audio_path: str | Path, language: str) -> Transcription:
        language = normalize_speech_language(language)
        path = Path(audio_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        headers = {"authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with path.open("rb") as audio:
                response = await client.post(
                    f"{self.base_url}/v1/audio/transcriptions",
                    headers=headers,
                    data={"language": language},
                    files={"file": (path.name, audio, "application/octet-stream")},
                )
        response.raise_for_status()
        return Transcription.model_validate(response.json())

    async def speech_capabilities(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/v1/audio/capabilities")
        response.raise_for_status()
        return response.json()
