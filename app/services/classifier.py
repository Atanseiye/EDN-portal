from app.models import IssueType

KEYWORDS: list[tuple[IssueType, tuple[str, ...]]] = [
    ("metering", ("meter", "metre", "map", "mapp", "faulty meter", "metering", "prepaid meter", "obsolete meter")),
    ("billing", ("bill", "billing", "estimated", "overbill", "over-bill", "debt", "arrears", "energy cap")),
    ("disconnection", ("disconnect", "cut off", "cutoff", "reconnect", "reconnection", "removed my light")),
    ("tariff_band", ("band a", "band b", "band c", "tariff", "hours of supply", "service band")),
    ("token_vending", ("token", "vending", "units", "kct", "key change token", "recharge")),
    ("connection", ("connection", "new connection", "pole", "transformer", "service wire")),
    ("safety", ("shock", "electrocution", "sparking", "fallen wire", "tamper", "bypass", "fire")),
    ("service_quality", ("outage", "no light", "power supply", "supply", "blackout", "interruption", "low voltage")),
]


def classify_issue(text: str) -> IssueType:
    normalized = " ".join(text.lower().split())
    scores: dict[IssueType, int] = {k: 0 for k, _ in KEYWORDS}
    for category, words in KEYWORDS:
        for word in words:
            if word in normalized:
                scores[category] += 2 if " " in word else 1
    if not any(scores.values()):
        return "other"
    return max(scores, key=scores.get)
