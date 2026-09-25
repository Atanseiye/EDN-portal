import os
import tempfile
from app.config import Settings
from app.models import Language

MODEL_BY_LANGUAGE = {
    "yoruba": "NCAIR1/Yoruba-ASR",
    "hausa": "NCAIR1/Hausa-ASR",
    "igbo": "NCAIR1/Igbo-ASR",
    "english": "NCAIR1/NigerianAccentedEnglish",
}


class ASRError(RuntimeError):
    pass


class NAtlasASR:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._pipes: dict[str, object] = {}

    def transcribe(self, audio_bytes: bytes, language: Language, suffix: str = ".webm") -> str:
        if len(audio_bytes) > self.settings.max_audio_mb * 1024 * 1024:
            raise ASRError("Audio exceeds configured size limit")
        provider = self.settings.asr_provider.lower()
        if provider == "mock":
            return "Mock transcription for local UI testing. Configure ASR_PROVIDER=local for official N-ATLaS ASR."
        if provider != "local":
            raise ASRError(f"Unsupported ASR_PROVIDER={provider}")
        try:
            from transformers import pipeline
        except ImportError as exc:
            raise ASRError("Install requirements-gpu.txt for official N-ATLaS ASR") from exc
        model_name = MODEL_BY_LANGUAGE[language]
        if language not in self._pipes:
            self._pipes[language] = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                token=self.settings.hf_token or None,
                device_map="auto",
            )
        fd, path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(audio_bytes)
            result = self._pipes[language](path)
            return result["text"].strip()
        finally:
            if os.path.exists(path):
                os.unlink(path)
