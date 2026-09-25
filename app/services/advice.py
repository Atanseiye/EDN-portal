from app.config import Settings
from app.models import AdviceRequest, AdviceResponse, ComplaintDraftRequest, ComplaintDraftResponse
from app.services.classifier import classify_issue
from app.services.knowledge import retrieve
from app.services.natlas import NAtlasClient, NAtlasError
from app.services.fallback import grounded_fallback, answer_is_direct
from app.services.routing import regulator_for_state
from app.services.validation import ValidationStore
from app.services.language import detect_text_language
from app.services.localization import localize_route, disclaimer_for, localized_source_cards, LANG_LABEL


class AdviceService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.natlas = NAtlasClient(settings)
        self.validation = ValidationStore(settings)

    async def advise(
        self,
        req: AdviceRequest,
        *,
        channel: str = "text",
        asr_provider: str | None = None,
        validation_consent: bool = False,
    ) -> AdviceResponse:
        effective_language = req.language if channel == "voice" else detect_text_language(req.message, req.language)
        issue = classify_issue(req.message)
        docs = retrieve(req.message, issue)
        route = regulator_for_state(req.state)
        localized_route = localize_route(route, effective_language)
        context = "\n\n".join(
            f"SOURCE {i+1}: {d['title']}\nAuthority: {d['authority']}\nURL: {d['url']}\nFACTS: {d['text']}"
            for i, d in enumerate(docs)
        )
        system = (
            "You are PowerRights NG, an electricity-consumer information assistant for Nigeria. "
            "You are powered by the official N-ATLaS model. Use ONLY the supplied verified regulatory facts for legal or regulatory claims. "
            "Your first responsibility is to ANSWER THE USER'S ACTUAL QUESTION. The first sentence of summary MUST directly answer it. "
            "If the user asks yes/no, answer yes/no with the necessary qualification. If they ask who, name the person/body. "
            "If they ask how long, state the verified timeframe. If they ask what to do, state the first action. "
            "If they ask multiple questions, answer every part in summary before giving supporting rights and steps. "
            "Do not begin with generic phrases such as 'I have reviewed your complaint', 'this appears to be', or 'the retrieved guidance covers'. "
            "Do not invent statutes, timelines, contacts, tariffs, rights, or complaint procedures. "
            "If the supplied facts do not answer something, say that explicitly. Keep the language plain and practical. "
            "Return strict JSON with exactly: summary (string), rights (array of strings), next_steps (array of strings)."
        )
        user = (
            f"Required response language: {LANG_LABEL[effective_language]}. ALL user-facing response text in summary, rights and next_steps MUST be in {LANG_LABEL[effective_language]}.\nState: {req.state or 'not provided'}.\n"
            f"DisCo/provider: {req.disco or 'not provided'}.\nIssue category: {issue}.\n"
            f"Consumer message: {req.message}\n\nVERIFIED CONTEXT:\n{context}"
        )
        provider = self.settings.natlas_provider.lower()
        if provider in {"mock", "grounded_rules", "disabled", ""}:
            generated = grounded_fallback(
                req.message,
                issue,
                docs,
                route,
                req.state,
                req.disco,
                language=effective_language,
                model_ready=self.settings.challenge_model_ready,
                asr_ready=self.settings.challenge_asr_ready,
            )
        else:
            try:
                generated = await self.natlas.generate_json(system, user)
                generated_text = " ".join([
                    str(generated.get("summary", "")),
                    " ".join(str(x) for x in generated.get("rights", [])),
                    " ".join(str(x) for x in generated.get("next_steps", [])),
                ])
                language_ok = (
                    effective_language == "english"
                    or detect_text_language(generated_text, "english") == effective_language
                )
                if not answer_is_direct(req.message, generated, route) or not language_ok:
                    generated = grounded_fallback(
                        req.message,
                        issue,
                        docs,
                        route,
                        req.state,
                        req.disco,
                        language=effective_language,
                        model_ready=self.settings.challenge_model_ready,
                        asr_ready=self.settings.challenge_asr_ready,
                    )
            except (NAtlasError, ValueError, KeyError):
                generated = grounded_fallback(
                    req.message,
                    issue,
                    docs,
                    route,
                    req.state,
                    req.disco,
                    language=effective_language,
                    model_ready=self.settings.challenge_model_ready,
                    asr_ready=self.settings.challenge_asr_ready,
                )
        interaction_id = self.validation.add_interaction(
            session_id=req.session_id,
            language=effective_language,
            issue_type=issue,
            state=req.state,
            disco=req.disco,
            channel=channel,
            asr_provider=asr_provider,
            validation_consent=validation_consent,
        )
        return AdviceResponse(
            interaction_id=interaction_id,
            issue_type=issue,
            summary=str(generated.get("summary", "")),
            rights=[str(x) for x in generated.get("rights", [])][:6],
            next_steps=[str(x) for x in generated.get("next_steps", [])][:7],
            escalation=localized_route,
            sources=localized_source_cards(docs, effective_language),
            language=effective_language,
            model=(
                self.settings.natlas_model
                if self.settings.challenge_model_ready
                else "verified-grounded-fallback"
            ),
            disclaimer=disclaimer_for(effective_language),
        )

    async def draft_complaint(self, req: ComplaintDraftRequest) -> ComplaintDraftResponse:
        effective_language = detect_text_language(req.message, req.language)
        issue = classify_issue(req.message)
        docs = retrieve(req.message, issue)
        route = localize_route(regulator_for_state(req.state), effective_language)
        context = "\n".join(f"- {d['text']} ({d['url']})" for d in docs)
        language_name = LANG_LABEL[effective_language]
        system = (
            "Draft a concise, factual Nigerian electricity consumer complaint using only supplied facts and the consumer's details. "
            f"Write the subject, body and checklist in {language_name}. "
            "Do not fabricate dates, amounts, account numbers, events, or legal provisions. "
            "Return strict JSON: subject (string), body (string), checklist (array of strings). "
            "The body should request investigation/resolution and ask for written acknowledgement/reference number."
        )
        user = (
            f"Issue: {issue}\nName: {req.complainant_name or '[Name]'}\nPhone: {req.phone or '[Phone]'}\n"
            f"Email: {req.email or '[Email]'}\nAddress: {req.address or '[Address]'}\nState: {req.state or '[State]'}\n"
            f"Provider: {req.disco or '[Electricity provider]'}\nMeter: {req.meter_number or '[Meter number]'}\n"
            f"Account: {req.account_number or '[Account number]'}\nConsumer account: {req.message}\n"
            f"Desired resolution: {req.desired_resolution or 'Investigate and resolve the complaint in line with applicable rules.'}\n"
            f"Verified facts:\n{context}"
        )
        generated = None
        if self.settings.challenge_model_ready:
            try:
                candidate = await self.natlas.generate_json(system, user)
                candidate_text = str(candidate.get("body", ""))
                if effective_language == "english" or detect_text_language(candidate_text, "english") == effective_language:
                    generated = candidate
            except Exception:
                generated = None

        if generated is None:
            provider = req.disco or {
                "english": "Electricity Provider",
                "yoruba": "Ilé-iṣẹ́ Iná",
                "hausa": "Kamfanin Wutar Lantarki",
                "igbo": "Ụlọ Ọrụ Ọkụ",
            }[effective_language]
            templates = {
                "english": {
                    "subject": f"Electricity Consumer Complaint — {issue.replace('_', ' ').title()}",
                    "body": (
                        f"Dear Customer Complaints Team,\n\nI am writing to lodge a formal complaint concerning the following issue: {req.message}\n\n"
                        "Please investigate this matter, provide a written acknowledgement/reference number, and communicate the resolution in writing. "
                        f"My meter/account details are {req.meter_number or req.account_number or '[insert meter/account number]'}.\n\n"
                        f"Requested resolution: {req.desired_resolution or 'Please resolve the complaint in line with applicable electricity consumer-protection requirements.'}\n\n"
                        f"Yours faithfully,\n{req.complainant_name or '[Name]'}"
                    ),
                    "checklist": ["Meter or account number", "Relevant bills/receipts", "Previous complaint acknowledgement", "Photos or token history where relevant"],
                },
                "yoruba": {
                    "subject": f"Ẹ̀sùn Oníbàárà Iná — {issue.replace('_', ' ').title()}",
                    "body": (
                        f"Ẹ̀ka Ìtẹ́wọ́gbà Ẹ̀sùn Oníbàárà, {provider},\n\nMo ń fi ẹ̀sùn yìí sílẹ̀ nípa ọ̀ràn yìí: {req.message}\n\n"
                        "Ẹ jọ̀ọ́, ẹ ṣe ìwádìí ọ̀ràn náà, ẹ fún mi ní acknowledgement/reference number ní kíkọ́, kí ẹ sì sọ ìpinnu àti ìgbésẹ̀ tí ẹ gbé fún mi ní kíkọ́. "
                        f"Àlàyé mita/account mi ni: {req.meter_number or req.account_number or '[fi meter/account number síbí]'}.\n\n"
                        f"Ohun tí mo ń béèrè: {req.desired_resolution or 'Ẹ jọ̀ọ́, ẹ yanju ọ̀ràn náà gẹ́gẹ́ bí ìlànà ààbò oníbàárà iná ṣe yẹ.'}\n\n"
                        f"Ẹ ṣé,\n{req.complainant_name or '[Orúkọ]'}"
                    ),
                    "checklist": ["Meter/account number", "Bill àti receipts tó yẹ", "Acknowledgement ẹ̀sùn tó ṣáájú", "Fọ́tò tàbí token history tí ó bá wà"],
                },
                "hausa": {
                    "subject": f"Korafin Kwastoman Wutar Lantarki — {issue.replace('_', ' ').title()}",
                    "body": (
                        f"Zuwa Customer Complaints Team na {provider},\n\nIna gabatar da korafi a hukumance game da wannan batu: {req.message}\n\n"
                        "Don Allah a binciki lamarin, a ba ni acknowledgement/reference number a rubuce, sannan a sanar da ni matakin warwarewar a rubuce. "
                        f"Bayanan mita/account dina: {req.meter_number or req.account_number or '[saka meter/account number]'}.\n\n"
                        f"Abin da nake nema: {req.desired_resolution or 'A warware korafin bisa ka\'idojin kare hakkin kwastoman wutar lantarki.'}\n\n"
                        f"Na gode,\n{req.complainant_name or '[Suna]'}"
                    ),
                    "checklist": ["Meter/account number", "Bills da receipts", "Acknowledgement na korafin baya", "Hotuna ko token history idan akwai"],
                },
                "igbo": {
                    "subject": f"Mkpesa Onye Ahịa Ọkụ — {issue.replace('_', ' ').title()}",
                    "body": (
                        f"Nye Customer Complaints Team nke {provider},\n\nAna m etinye mkpesa a n'akwụkwọ banyere okwu a: {req.message}\n\n"
                        "Biko nyochaa okwu a, nye m acknowledgement/reference number n'akwụkwọ, ma kọwaakwa ihe e mere iji dozie ya n'akwụkwọ. "
                        f"Nkọwa mita/account m bụ: {req.meter_number or req.account_number or '[tinye meter/account number]'}.\n\n"
                        f"Ihe m na-arịọ: {req.desired_resolution or 'Biko dozie okwu a dịka ụkpụrụ nchedo onye ahịa ọkụ si dị.'}\n\n"
                        f"Daalụ,\n{req.complainant_name or '[Aha]'}"
                    ),
                    "checklist": ["Meter/account number", "Bills na receipts", "Acknowledgement mkpesa gara aga", "Foto ma ọ bụ token history ma ọ bụrụ na ọ dị"],
                },
            }
            generated = templates[effective_language]

        return ComplaintDraftResponse(
            subject=str(generated.get("subject", "")),
            body=str(generated.get("body", "")),
            destination=route,
            checklist=[str(x) for x in generated.get("checklist", [])][:8],
        )

