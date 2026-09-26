from __future__ import annotations

from .providers import NATLAS_ASR_MODELS

LANGUAGE_ALIASES = {
    "en": "english",
    "en-ng": "english",
    "english": "english",
    "nigerian english": "english",
    "yo": "yoruba",
    "yor": "yoruba",
    "yoruba": "yoruba",
    "ha": "hausa",
    "hau": "hausa",
    "hausa": "hausa",
    "ig": "igbo",
    "ibo": "igbo",
    "igbo": "igbo",
}


def normalize_speech_language(language: str) -> str:
    key = language.strip().lower()
    try:
        return LANGUAGE_ALIASES[key]
    except KeyError as exc:
        supported = ", ".join(sorted(NATLAS_ASR_MODELS))
        raise ValueError(
            f"Unsupported speech language {language!r}. Choose: {supported}"
        ) from exc


def asr_model_for(language: str) -> str:
    return NATLAS_ASR_MODELS[normalize_speech_language(language)]
