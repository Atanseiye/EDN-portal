from __future__ import annotations

import unicodedata


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text).casefold()
    chars = []
    for char in text:
        if unicodedata.category(char).startswith("P"):
            chars.append(" ")
        else:
            chars.append(char)
    return " ".join("".join(chars).split())


def _distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for i, ref_item in enumerate(reference, 1):
        current = [i]
        for j, hyp_item in enumerate(hypothesis, 1):
            substitution = previous[j - 1] + (ref_item != hyp_item)
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref = _clean(reference).split()
    hyp = _clean(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    return _distance(ref, hyp) / len(ref)


def character_error_rate(reference: str, hypothesis: str) -> float:
    ref = list(_clean(reference).replace(" ", ""))
    hyp = list(_clean(hypothesis).replace(" ", ""))
    if not ref:
        return 0.0 if not hyp else 1.0
    return _distance(ref, hyp) / len(ref)


def score_transcript(reference: str, hypothesis: str) -> dict[str, float | int]:
    clean_ref = _clean(reference)
    clean_hyp = _clean(hypothesis)
    ref_words = clean_ref.split()
    ref_chars = list(clean_ref.replace(" ", ""))
    return {
        "wer": round(word_error_rate(reference, hypothesis), 6),
        "cer": round(character_error_rate(reference, hypothesis), 6),
        "reference_words": len(ref_words),
        "reference_characters": len(ref_chars),
    }
