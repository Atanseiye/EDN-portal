from .providers import NATLAS_ASR_MODELS

def asr_model_for(language: str) -> str:
    key = language.strip().lower()
    try:
        return NATLAS_ASR_MODELS[key]
    except KeyError as exc:
        supported = ", ".join(sorted(NATLAS_ASR_MODELS))
        raise ValueError(f"Unsupported language {language!r}. Choose: {supported}") from exc
