from app.models import IssueType

KEYWORDS: list[tuple[IssueType, tuple[str, ...]]] = [
    ("metering", (
        "meter", "metre", "map", "mapp", "faulty meter", "metering", "prepaid meter", "obsolete meter",
        "mita", "mita bàjẹ́", "mita baje", "rọ́pò mita", "ropo mita",
        "mita ya lalace", "cire mita", "maye gurbin mita",
        "mita mebiri", "wepụrụ mita", "wepuru mita", "dochie mita",
    )),
    ("billing", (
        "bill", "billing", "estimated", "overbill", "over-bill", "debt", "arrears", "energy cap",
        "owó ina", "owo ina", "billing àfọwọ́kọ", "billing afowoko", "gbà owó", "gba owo",
        "kudin wuta", "estimated billing", "kimanta kudin wuta",
        "ego ọkụ", "ego oku", "billing e mere atụmatụ",
    )),
    ("disconnection", (
        "disconnect", "cut off", "cutoff", "reconnect", "reconnection", "removed my light",
        "gé iná", "ge ina", "pa iná", "pa ina", "so iná padà", "so ina pada",
        "katse wuta", "dawo da wuta",
        "gbanyụọ ọkụ", "gbanyuo oku", "weghachi ọkụ", "weghachi oku",
    )),
    ("tariff_band", (
        "band a", "band b", "band c", "tariff", "hours of supply", "service band",
        "owó band", "band a", "akoko ina",
        "jadawalin wuta", "service band",
        "oge ọkụ", "oge oku",
    )),
    ("token_vending", (
        "token", "vending", "units", "kct", "key change token", "recharge",
        "tókìn", "tokin", "units", "fi owó sí mita", "fi owo si mita",
        "sayan token", "cajin mita",
        "token mita", "tinye ego na mita",
    )),
    ("connection", (
        "connection", "new connection", "pole", "transformer", "service wire",
        "so iná", "so ina", "asopọ iná", "asopo ina",
        "hada wuta", "sabon connection",
        "jikọọ ọkụ", "jikoo oku", "new connection",
    )),
    ("safety", (
        "shock", "electrocution", "sparking", "fallen wire", "tamper", "bypass", "fire",
        "ewu iná", "ewu ina", "wáyà ṣubú", "waya subu", "iná ń jó", "ina n jo",
        "hadarin wuta", "waya ya fadi",
        "ihe egwu ọkụ", "ihe egwu oku", "waya dara", "ọkụ", "oku",
    )),
    ("service_quality", (
        "outage", "no light", "power supply", "supply", "blackout", "interruption", "low voltage",
        "kò sí iná", "ko si ina", "iná kò dé", "ina ko de", "foliteji kekere",
        "babu wuta", "wuta ta dauke", "karancin voltage",
        "enweghị ọkụ", "enweghi oku", "ọkụ adịghị", "oku adighi", "low voltage",
    )),
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
