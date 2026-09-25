import re
from app.models import Language

YORUBA_WORDS = {
    "ati","ní","ni","mo","mi","wọn","won","kí","ki","ṣe","se","ṣẹ","jẹ","jẹ́","rẹ","rẹ̀",
    "bá","ba","yẹ","ye","ṣé","ṣe","ẹ̀tọ́","eto","ẹsun","ẹ̀sùn","ina","owó","owo","fún","fun",
    "lọ","lo","ń","n","tí","ti","kò","ko","báyìí","bayii","àti","wọ́n","wọn","yanju"
}
IGBO_WORDS = {
    "anyị","anyi","m","maka","nke","na","ka","ọ","o","ị","i","ụlọ","ulo","ọkụ","oku",
    "ego","mita","anyị","ha","gịnị","gini","ebe","onye","ga","mee","ikike","mkpesa"
}
HAUSA_WORDS = {
    "na","ina","ne","ce","da","ba","ban","don","me","yaya","wane","wace","wuta","lantarki",
    "mita","kudi","kudin","koke","hakki","hakkina","kamfani","suka","sun","za","zan","dole"
}

YORUBA_CHARS = set("ẹẸọỌṣṢàÀáÁèÈéÉìÌíÍòÒóÓùÙúÚńŃ")
IGBO_CHARS = set("ịỊụỤṅṄ")
HAUSA_CHARS = set("ƙƘɗƊɓƁ")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\wÀ-ž]+", text.lower(), flags=re.UNICODE)


def detect_text_language(text: str, selected: Language = "english") -> Language:
    """Detect clear Nigerian-language text; keep selected language if signal is weak."""
    tokens = _tokens(text)
    token_set = set(tokens)

    scores = {
        "yoruba": sum(1 for t in tokens if t in YORUBA_WORDS),
        "igbo": sum(1 for t in tokens if t in IGBO_WORDS),
        "hausa": sum(1 for t in tokens if t in HAUSA_WORDS),
        "english": 0,
    }
    scores["yoruba"] += sum(3 for ch in text if ch in YORUBA_CHARS)
    scores["igbo"] += sum(3 for ch in text if ch in IGBO_CHARS)
    scores["hausa"] += sum(3 for ch in text if ch in HAUSA_CHARS)

    # Strong multi-word lexical cues help unaccented mobile typing.
    lower = " ".join(tokens)
    if any(p in lower for p in ("ki ni", "kini", "se won", "mo ye", "fi esun", "owo ina", "won ko")):
        scores["yoruba"] += 5
    if any(p in lower for p in ("gini ka", "kedụ", "kedụ ka", "ego oku", "ụlọ ọkụ", "mkpesa")):
        scores["igbo"] += 5
    if any(p in lower for p in ("me zan", "yaya zan", "kudin wuta", "kamfanin wuta", "ina da hakki")):
        scores["hausa"] += 5

    ranked = sorted(
        ((lang, score) for lang, score in scores.items() if lang != "english"),
        key=lambda x: x[1],
        reverse=True,
    )
    best, best_score = ranked[0]
    second_score = ranked[1][1]

    if best_score >= 5 and best_score >= second_score + 2:
        return best  # type: ignore[return-value]
    return selected
