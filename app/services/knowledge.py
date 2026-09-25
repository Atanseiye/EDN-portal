import json
import re
from functools import lru_cache
from pathlib import Path
from app.models import SourceCard, IssueType

DATA = Path(__file__).resolve().parents[1] / "data" / "knowledge.json"
STOP = {"the", "and", "a", "an", "to", "of", "in", "for", "is", "are", "my", "i", "me", "it", "on", "with", "that", "this", "do", "what"}


@lru_cache
def load_knowledge() -> list[dict]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2 and t not in STOP}


def retrieve(query: str, issue_type: IssueType, limit: int = 4) -> list[dict]:
    q = _tokens(query)
    ranked = []
    for item in load_knowledge():
        body = f"{item['title']} {item['text']} {' '.join(item.get('tags', []))}"
        overlap = len(q & _tokens(body))
        category_bonus = 5 if issue_type in item.get("categories", []) else 0
        general_bonus = 1 if "general" in item.get("categories", []) else 0
        ranked.append((overlap + category_bonus + general_bonus, item))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in ranked[:limit] if score > 0]


def to_source_cards(items: list[dict]) -> list[SourceCard]:
    return [
        SourceCard(
            title=x["title"],
            authority=x["authority"],
            url=x["url"],
            excerpt=x["text"],
            updated=x.get("updated"),
        )
        for x in items
    ]
