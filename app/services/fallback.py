import re
from app.models import IssueType, RegulatorRoute, Language
from app.services.localization import localized_fact


ELECTRICITY_TERMS = (
    "electricity", "light", "power", "disco", "meter", "metre", "bill", "billing",
    "estimated", "tariff", "band", "token", "vending", "kct", "outage", "blackout",
    "disconnect", "reconnect", "transformer", "feeder", "voltage", "connection",
    "units", "prepaid", "postpaid", "energy", "nerc", "customer complaints",
    "complaint", "regulator", "escalate"
)

LANGUAGE_NAMES = {
    "igbo": "Igbo",
    "yoruba": "Yorùbá",
    "yorùbá": "Yorùbá",
    "hausa": "Hausa",
    "english": "Nigerian English",
}


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def is_electricity_related(text: str) -> bool:
    normalized = _norm(text)
    return any(term in normalized for term in ELECTRICITY_TERMS)


def _doc(docs: list[dict], doc_id: str) -> dict | None:
    return next((d for d in docs if d.get("id") == doc_id), None)


def _fact(docs: list[dict], doc_id: str) -> str | None:
    d = _doc(docs, doc_id)
    return d.get("text") if d else None


def _asks_language_capability(text: str) -> str | None:
    t = _norm(text)
    if not any(p in t for p in ("can you speak", "do you speak", "can you understand", "do you understand", "respond in", "answer in")):
        return None
    for key, label in LANGUAGE_NAMES.items():
        if key in t:
            return label
    return None


def _asks_escalation(text: str) -> bool:
    t = _norm(text)
    return (
        (("who" in t or "where" in t) and any(x in t for x in ("escalat", "complain", "report", "regulat")))
        or "who regulates" in t or "where do i complain" in t
        or any(x in t for x in ("ta ni mo yẹ", "ta ni mo ye", "fi ẹ̀sùn", "fi esun", "lé lọ́wọ́", "le lowo"))
        or any(x in t for x in ("wa zan kai", "ina zan kai", "daukaka korafi"))
        or any(x in t for x in ("onye ka m", "ebe ka m", "bugara mkpesa", "bulie mkpesa"))
    )


def _asks_complaint_timeline(text: str) -> bool:
    t = _norm(text)
    return any(x in t for x in ("how long", "how many days", "when should")) and any(
        x in t for x in ("complaint", "resolve", "response", "respond")
    )


def _asks_meter_replacement_timeline(text: str) -> bool:
    t = _norm(text)
    return any(x in t for x in ("how long", "how many days", "when should")) and "meter" in t and any(
        x in t for x in ("replace", "repair", "fault", "faulty", "defective")
    )


def _asks_credit_timeline(text: str) -> bool:
    t = _norm(text)
    return any(x in t for x in ("how long", "when", "48")) and any(
        x in t for x in ("credit", "units", "balance")
    ) and "meter" in t


def _asks_who_replaces_meter(text: str) -> bool:
    t = _norm(text)
    return ("who" in t and "meter" in t and any(x in t for x in ("replace", "repair", "responsib"))) or (
        "is it my responsibility" in t and "meter" in t
    )


def _asks_estimated_after_removal(text: str) -> bool:
    t = _norm(text)
    english = "meter" in t and any(x in t for x in ("remove", "removed", "faulty", "defective")) and any(
        x in t for x in ("estimated", "estimate", "bill")
    )
    yoruba = any(x in t for x in ("billing àfọwọ́kọ", "billing afowoko", "owó ina àfọwọ́kọ", "owo ina afowoko")) and any(
        x in t for x in ("yọ", "yo", "bàjẹ́", "baje", "rọ́pò", "ropo")
    )
    hausa = any(x in t for x in ("estimated billing", "kimanta kudin wuta")) and any(
        x in t for x in ("cire mita", "mita ya lalace", "mayar da mita")
    )
    igbo = any(x in t for x in ("estimated billing", "ego ọkụ e mere atụmatụ", "ego oku e mere atụmatụ")) and any(
        x in t for x in ("wepụrụ mita", "wepuru mita", "mita mebiri")
    )
    return english or yoruba or hausa or igbo


def _asks_disconnection_notice(text: str) -> bool:
    t = _norm(text)
    return any(x in t for x in ("disconnect", "cut me off", "cut off")) and any(
        x in t for x in ("notice", "without telling", "without warning", "can they")
    )


def _asks_rights(text: str) -> bool:
    t = _norm(text)
    return any(x in t for x in (
        "what are my rights", "my right", "do i have a right", "am i entitled",
        "kí ni ẹ̀tọ́ mi", "ki ni eto mi", "ẹ̀tọ́ mi", "eto mi",
        "menene hakkina", "me ne hakkina", "hakkina",
        "gịnị bụ ikike m", "gini bu ikike m", "ikike m"
    ))


def _asks_what_to_do(text: str) -> bool:
    t = _norm(text)
    return any(x in t for x in (
        "what should i do", "what do i do", "what can i do", "next step", "how do i complain",
        "kí ni mo yẹ kí n ṣe", "ki ni mo ye ki n se", "kí ni mo lè ṣe", "ki ni mo le se",
        "me ya kamata in yi", "me zan yi", "yaya zan yi",
        "gịnị ka m mee", "gini ka m mee", "kedu ihe m ga eme"
    ))


def _direct_answer(
    message: str,
    issue: IssueType,
    docs: list[dict],
    route: RegulatorRoute,
    state: str | None,
    disco: str | None,
    language: Language,
    *,
    model_ready: bool,
    asr_ready: bool,
) -> str | None:
    t = _norm(message)
    provider = disco or {
        "english": "your electricity provider",
        "yoruba": "ilé-iṣẹ́ iná rẹ",
        "hausa": "kamfanin wutar lantarkinka",
        "igbo": "ụlọ ọrụ ọkụ gị",
    }[language]
    answers: list[str] = []

    language = _asks_language_capability(message)
    if language:
        if model_ready and asr_ready:
            answers.append(f"Yes. PowerRights is configured to support {language} through the official N-ATLaS language stack.")
        elif asr_ready:
            answers.append(
                f"PowerRights can transcribe {language} voice with the configured N-ATLaS ASR, "
                "but full N-ATLaS response generation is not active yet."
            )
        else:
            answers.append(
                f"PowerRights is designed to support {language}, but the official N-ATLaS {language} voice/model path "
                "is not active on this deployment yet, so I should not claim full live language support."
            )

    if _asks_estimated_after_removal(message) and _fact(docs, "faulty-meter-estimation"):
        answers.append({
            "english": (
                "They should not simply move you to arbitrary estimated billing because a faulty or obsolete meter "
                "was removed and not replaced. NERC's guidance says that where replacement cannot occur within the "
                "billing period, consumption should be determined using the customer's average billing or vending "
                "over the preceding three months."
            ),
            "yoruba": (
                "Rárá—wọn kò yẹ kí wọ́n kàn fi ọ sí billing àfọwọ́kọ tí kò ní ìpìlẹ̀ nítorí pé mita tó bàjẹ́ ni wọ́n yọ tí wọn kò sì rọ́pò rẹ̀. "
                "Ìtọ́sọ́nà NERC sọ pé bí rirọ́pò mita kò bá ṣẹlẹ̀ ní àkókò billing, a yẹ kí a lo àárín gbùngbùn billing tàbí vending oṣù mẹ́ta tó ṣáájú."
            ),
            "hausa": (
                "A'a—bai kamata su kawai sanya ka a arbitrary estimated billing ba saboda an cire mita mai matsala ba tare da maye gurbinsa ba. "
                "Jagorar NERC ta ce idan ba a maye gurbin mita cikin lokacin billing ba, a yi amfani da matsakaicin billing ko vending na watanni uku da suka gabata."
            ),
            "igbo": (
                "Mba—ha ekwesịghị itinye gị naanị na arbitrary estimated billing n'ihi na e wepụrụ mita mebiri emebi ma a dochighị ya. "
                "NERC kwuru na ma ọ bụrụ na a naghị edochi mita n'oge billing, a ga-eji nkezi billing ma ọ bụ vending nke ọnwa atọ gara aga."
            ),
        }[language])

    if _asks_who_replaces_meter(message) and _fact(docs, "meter-replacement-duty"):
        answers.append(
            f"The DisCo is responsible for urgent repair or replacement of a defective metering system; "
            f"for your case, that means {provider}."
        )

    if _asks_meter_replacement_timeline(message) and _fact(docs, "meter-replacement-duty"):
        answers.append(
            "For a faulty metering-system fault, NERC's metering FAQ cites a two-working-day repair or "
            "replacement requirement after the fault is discovered."
        )

    if _asks_credit_timeline(message) and _fact(docs, "meter-credit-balance"):
        answers.append(
            "NERC states that units recorded on the old meter should be credited to the customer within "
            "48 hours after the replacement meter is installed."
        )

    if _asks_complaint_timeline(message) and _fact(docs, "complaint-timeline"):
        answers.append(
            "NERC states that a DisCo is expected to resolve a written customer complaint within "
            "15 working days, depending on the complexity of the complaint."
        )

    if _asks_disconnection_notice(message) and _fact(docs, "consumer-rights"):
        answers.append(
            "Electricity customers are entitled to written notice ahead of disconnection in line with the "
            "applicable regulatory guidelines. The sources currently loaded here do not establish a single "
            "universal notice period, so PowerRights should not invent one."
        )

    if _asks_rights(message):
        facts = [d["text"] for d in docs if d.get("text")]
        if facts:
            answers.append({
                "english": "The most directly relevant verified protection I found is: ",
                "yoruba": "Ààbò tó ṣe pàtàkì jù lọ tí mo rí nínú ìtọ́sọ́nà tó jẹ́rìí ni pé: ",
                "hausa": "Kariyar da ta fi dacewa da na samu daga bayanan da aka tabbatar ita ce: ",
                "igbo": "Nchedo kachasị dabara m hụrụ n'ihe e gosipụtara bụ: ",
            }[language] + localized_fact(docs[0].get("id",""), language, facts[0]))

    if _asks_what_to_do(message):
        if issue == "metering":
            answers.append(
                f"Your first step is to submit a written metering complaint to {provider}'s Customer Complaints Unit, "
                "get a complaint/reference number, and attach the meter number plus evidence of the fault or removal."
            )
        elif issue == "billing":
            answers.append(
                f"Your first step is to dispute the bill in writing with {provider}'s Customer Complaints Unit, "
                "keep the acknowledgement, and attach the disputed bill plus earlier bills or vending history."
            )
        elif issue == "disconnection":
            answers.append(
                f"Ask {provider} in writing for the reason and basis for the disconnection, keep the notice and receipts, "
                "and lodge a formal complaint if you dispute it."
            )
        else:
            answers.append(
                f"Start with a written complaint to {provider}'s Customer Complaints Unit and keep the acknowledgement/reference number."
            )

    if _asks_escalation(message):
        if route.level == "state":
            answers.append(
                f"For an unresolved intrastate electricity complaint in {state or 'your state'}, first complain to "
                f"{provider}'s Customer Complaints Unit; the regulatory escalation point is {route.regulator_name}."
            )
        else:
            answers.append(
                f"First complain in writing to {provider}'s Customer Complaints Unit. If it remains unresolved, "
                "escalate to the relevant NERC Consumer Forum and then to NERC."
            )

    if answers:
        # Preserve order, remove duplicate wording.
        unique = []
        seen = set()
        for answer in answers:
            key = _norm(answer)
            if key not in seen:
                seen.add(key)
                unique.append(answer)
        return " ".join(unique)

    if issue == "safety":
        return (
            "Treat this as an urgent electricity-safety issue: keep away from the hazard and report it immediately "
            f"through {provider}'s official emergency or customer-service channel."
        )

    if issue == "billing":
        if "estimated" in t:
            return (
                "This is a dispute about estimated billing. NERC's guidance says unmetered customers should not be billed "
                "above the applicable energy cap for their feeder, and you can formally challenge the billing basis."
            )
        return (
            f"You can formally dispute this bill with {provider}; ask for the calculation/basis in writing and request correction "
            "of any unsupported charge."
        )

    if issue == "metering":
        return (
            f"This is a metering issue, and {provider} should investigate the meter fault/removal and address replacement "
            "rather than leaving you without a clear metering resolution."
        )

    if issue == "disconnection":
        return (
            f"You can challenge the disconnection with {provider} and request the written reason, notice and regulatory basis."
        )

    if issue == "service_quality":
        return (
            f"Report the outage or voltage/supply problem to {provider}, obtain a complaint reference, and escalate it if it remains unresolved."
        )

    if issue == "tariff_band":
        return (
            f"You can challenge a tariff/service-band mismatch. Ask {provider} to confirm your feeder, service band and billing basis in writing."
        )

    if issue == "token_vending":
        return (
            f"Treat this as a vending transaction complaint: keep the transaction reference/token/error and report it to {provider} before repurchasing."
        )

    if issue == "connection":
        return (
            f"Ask {provider} for the status and any outstanding requirement on the connection request in writing, using your application/reference number."
        )

    if issue == "other" and not is_electricity_related(message):
        return (
            "I can answer that question directly, but PowerRights is specifically an electricity-consumer assistant. "
            "For electricity help, ask about a bill, meter, disconnection, outage, tariff band, token, connection or safety issue."
        )

    return None

def grounded_fallback(
    message: str,
    issue: IssueType,
    docs: list[dict],
    route: RegulatorRoute,
    state: str | None,
    disco: str | None,
    language: Language = "english",
    *,
    model_ready: bool = False,
    asr_ready: bool = False,
) -> dict:
    """Answer the user's query first, then support it with grounded rights/actions."""
    direct = _direct_answer(
        message,
        issue,
        docs,
        route,
        state,
        disco,
        language,
        model_ready=model_ready,
        asr_ready=asr_ready,
    )

    facts = [localized_fact(d.get("id",""), language, d["text"]) for d in docs if d.get("text")]
    provider = disco or {
        "english": "your electricity provider",
        "yoruba": "ilé-iṣẹ́ iná rẹ",
        "hausa": "kamfanin wutar lantarkinka",
        "igbo": "ụlọ ọrụ ọkụ gị",
    }[language]

    if issue == "other" and not is_electricity_related(message):
        return {
            "summary": direct or "PowerRights is focused on Nigerian electricity-consumer questions.",
            "rights": [],
            "next_steps": [
                "Ask your electricity-related question directly.",
                "Include your state and electricity provider when they affect the answer.",
            ],
        }

    if issue == "metering":
        rights = facts[:3]
        steps = [
            f"Write to {provider}'s Customer Complaints Unit and request a complaint/reference number.",
            "State when the meter became faulty or was removed and ask for the replacement status in writing.",
            "Attach previous vending/billing records, meter number and any evidence of removal or fault.",
            "If estimated billing started after removal, challenge the billing basis and keep every disputed bill.",
        ]
    elif issue == "billing":
        rights = facts[:3]
        steps = [
            f"Submit a written billing dispute to {provider}'s Customer Complaints Unit and keep the acknowledgement.",
            "Attach the disputed bill, earlier bills or vending history, meter/account number and payment receipts.",
            "Ask the provider to explain the calculation and correct any unsupported charge in writing.",
            "Escalate through the regulator route below if the complaint is not resolved.",
        ]
    elif issue == "disconnection":
        rights = facts[:3]
        steps = [
            f"Ask {provider} for the written reason and basis for the disconnection.",
            "Keep the disconnection notice, bills, receipts and previous complaint references.",
            "Submit a written dispute if you contest the disconnection.",
            "Use the regulator route below if the provider does not resolve it.",
        ]
    elif issue == "service_quality":
        rights = facts[:2]
        steps = [
            f"Report the supply problem to {provider} and obtain a complaint/reference number.",
            "Record dates, durations and any feeder/transformer details you know.",
            "Keep evidence of earlier reports.",
            "Escalate if the service problem remains unresolved.",
        ]
    elif issue == "tariff_band":
        rights = facts[:3]
        steps = [
            f"Ask {provider} to confirm your service band, feeder and billing basis in writing.",
            "Keep bills and a record of actual supply hours for the disputed period.",
            "Submit any mismatch as a written complaint.",
            "Escalate unresolved disputes using the regulator route below.",
        ]
    elif issue == "token_vending":
        rights = facts[:3]
        steps = [
            "Keep the transaction receipt/reference, token, meter number and exact error message.",
            f"Report the failed vending or missing units to {provider} and obtain a complaint reference.",
            "Do not repeatedly repurchase until the original transaction status is confirmed.",
            "Escalate unresolved cases using the regulator route below.",
        ]
    elif issue == "connection":
        rights = facts[:2]
        steps = [
            f"Reference the connection request with {provider} in writing.",
            "Keep receipts, application/reference numbers and correspondence.",
            "Ask for the outstanding requirement or reason for delay in writing.",
            "Escalate if it remains unresolved.",
        ]
    elif issue == "safety":
        rights = facts[:2]
        steps = [
            f"Report the hazard immediately through {provider}'s official emergency/customer-service channel.",
            "Keep a safe distance from fallen wires, sparking equipment or exposed live conductors.",
            "Record the location and report reference; take photographs only if safe.",
            "Escalate persistent public-safety hazards through the regulator route below.",
        ]
    else:
        rights = facts[:2]
        steps = [
            f"Submit the issue to {provider}'s Customer Complaints Unit in writing.",
            "Include relevant meter/account details, dates and supporting evidence.",
            "Use the regulator route below if it remains unresolved.",
        ]

    if language == "yoruba":
        step_map = {
            "metering": [
                f"Fi ẹ̀sùn metering sí Customer Complaints Unit ti {provider} ní kíkọ́, kí o sì gba complaint/reference number.",
                "Ṣàlàyé ìgbà tí mita náà bàjẹ́ tàbí tí wọ́n yọ ọ́, kí o sì béèrè ipo rirọ́pò rẹ̀ ní kíkọ́.",
                "Fi meter number, vending/billing records àti ẹ̀rí míì tó bá wà kún un.",
                "Bí billing àfọwọ́kọ bá bẹ̀rẹ̀ lẹ́yìn tí wọ́n yọ mita náà, tako ìpìlẹ̀ billing náà ní kíkọ́.",
            ],
            "billing": [
                f"Tako bill náà ní kíkọ́ lọ́dọ̀ Customer Complaints Unit ti {provider}, kí o sì pa acknowledgement mọ́.",
                "Fi bill tí o ń tako, àwọn bill tàbí vending history tó ṣáájú, meter/account number àti receipts kún un.",
                "Béèrè fún ìṣírò àti ìpìlẹ̀ bill náà ní kíkọ́, kí wọ́n sì ṣàtúnṣe owó tí kò ní ìpìlẹ̀.",
                "Bí wọn kò bá yanju rẹ̀, lo ipa escalation tó wà nísàlẹ̀.",
            ],
        }
        steps = step_map.get(issue, steps)
    elif language == "hausa":
        step_map = {
            "metering": [
                f"Ka kai rubutaccen korafin mita zuwa Customer Complaints Unit na {provider}, ka kuma samu complaint/reference number.",
                "Ka bayyana lokacin da mita ya lalace ko aka cire shi, sannan ka nemi matsayin maye gurbinsa a rubuce.",
                "Ka hada meter number, tarihin vending/billing da sauran hujjoji.",
                "Idan estimated billing ya fara bayan an cire mita, ka kalubalanci tushen billing din a rubuce.",
            ],
            "billing": [
                f"Ka kalubalanci bill din a rubuce a Customer Complaints Unit na {provider}, ka ajiye acknowledgement.",
                "Ka hada bill din da kake kalubalanta, tsofaffin bills ko vending history, meter/account number da receipts.",
                "Ka nemi bayanin lissafin da tushensa a rubuce sannan ka nemi gyaran duk cajin da ba shi da hujja.",
                "Idan ba a warware ba, ka bi hanyar daukaka korafi da ke kasa.",
            ],
        }
        steps = step_map.get(issue, steps)
    elif language == "igbo":
        step_map = {
            "metering": [
                f"Dee mkpesa gbasara mita nye Customer Complaints Unit nke {provider}, nweta complaint/reference number.",
                "Kọwaa mgbe mita mebiri ma ọ bụ mgbe e wepụrụ ya, rịọkwa ka ha dee ọnọdụ dochie mita ahụ.",
                "Tinye meter number, vending/billing records na ihe akaebe ndị ọzọ i nwere.",
                "Ọ bụrụ na estimated billing malitere mgbe e wepụrụ mita, jụọ ma gbaghaa ntọala billing ahụ n'akwụkwọ.",
            ],
            "billing": [
                f"Dee mgbagha banyere bill ahụ nye Customer Complaints Unit nke {provider}, debe acknowledgement.",
                "Tinye bill ị na-agbagha, bills gara aga ma ọ bụ vending history, meter/account number na receipts.",
                "Rịọ ka ha kọwaa calculation na basis nke bill ahụ n'akwụkwọ ma mezie ụgwọ na-enweghị ihe akaebe.",
                "Ọ bụrụ na a naghị edozi ya, soro ụzọ escalation e gosiri n'okpuru.",
            ],
        }
        steps = step_map.get(issue, steps)

    default_summary = {
        "english": "I found verified electricity-consumer guidance relevant to your question.",
        "yoruba": "Mo rí ìtọ́sọ́nà iná tó jẹ́rìí tí ó bá ìbéèrè rẹ mu.",
        "hausa": "Na sami tabbataccen jagorar wutar lantarki da ya dace da tambayarka.",
        "igbo": "Achọtara m nduzi ọkụ eletrik e gosipụtara nke dabara na ajụjụ gị.",
    }[language]
    return {
        "summary": direct or default_summary,
        "rights": rights,
        "next_steps": steps,
    }


def answer_is_direct(message: str, generated: dict, route: RegulatorRoute) -> bool:
    """Reject generic or evasive model output before it reaches the user."""
    summary = str(generated.get("summary", "")).strip()
    if not summary:
        return False

    s = _norm(summary)
    m = _norm(message)

    generic_markers = (
        "i have reviewed the electricity complaint",
        "matched it to verified",
        "this appears to be a",
        "the retrieved guidance covers",
    )
    if any(marker in s for marker in generic_markers):
        return False

    language = _asks_language_capability(message)
    if language and language.lower().replace("yorùbá", "yoruba") not in s.replace("yorùbá", "yoruba"):
        return False

    if _asks_escalation(message):
        regulator = route.regulator_name.lower()
        acronym_match = re.search(r"\(([A-Z]{3,})\)", route.regulator_name)
        acronym = acronym_match.group(1).lower() if acronym_match else ""
        if route.level == "state":
            significant = [w for w in re.findall(r"[a-z]+", regulator) if len(w) > 5]
            if acronym and acronym in s:
                return True
            if significant and not any(w in s for w in significant[:3]):
                return False
        elif "nerc" not in s:
            return False

    if _asks_complaint_timeline(message) or _asks_meter_replacement_timeline(message) or _asks_credit_timeline(message):
        if not re.search(r"\b\d+\b|working day|hours?|days?", s):
            return False

    if _asks_estimated_after_removal(message):
        if "estimated" not in s and "billing" not in s:
            return False
        if not any(x in s for x in ("average", "three months", "3 months", "arbitrary", "should not", "cannot")):
            return False

    if _asks_who_replaces_meter(message):
        if not any(x in s for x in ("disco", "distribution", "provider", "responsible")):
            return False

    if _asks_disconnection_notice(message):
        if not any(x in s for x in ("notice", "written", "disconnect")):
            return False

    # For other questions, require at least one meaningful query term to survive into
    # the answer. This blocks polished generic summaries that ignore the actual input.
    stop = {
        "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
        "can", "could", "would", "should", "does", "did", "the", "and", "for",
        "with", "this", "that", "from", "have", "has", "had", "your", "my",
        "they", "them", "their", "about", "please",
    }
    query_terms = {
        w for w in re.findall(r"[a-z0-9]+", m)
        if len(w) >= 4 and w not in stop
    }
    if query_terms and not any(term in s for term in query_terms):
        combined = _norm(
            " ".join(str(x) for x in generated.get("rights", []))
            + " "
            + " ".join(str(x) for x in generated.get("next_steps", []))
        )
        if not any(term in combined for term in query_terms):
            return False

    return True
