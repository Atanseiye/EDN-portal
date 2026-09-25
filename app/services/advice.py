from app.config import Settings
from app.models import AdviceRequest, AdviceResponse, ComplaintDraftRequest, ComplaintDraftResponse
from app.services.classifier import classify_issue
from app.services.knowledge import retrieve, to_source_cards
from app.services.natlas import NAtlasClient, NAtlasError
from app.services.fallback import grounded_fallback, answer_is_direct
from app.services.routing import regulator_for_state
from app.services.validation import ValidationStore

DISCLAIMER = (
    "PowerRights provides informational guidance from cited electricity-regulatory sources. "
    "It is not a regulator, law firm, or substitute for an official decision. Verify time-sensitive rules with the cited authority."
)


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
        issue = classify_issue(req.message)
        docs = retrieve(req.message, issue)
        route = regulator_for_state(req.state)
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
            f"Preferred response language: {req.language}.\nState: {req.state or 'not provided'}.\n"
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
                model_ready=self.settings.challenge_model_ready,
                asr_ready=self.settings.challenge_asr_ready,
            )
        else:
            try:
                generated = await self.natlas.generate_json(system, user)
                if not answer_is_direct(req.message, generated, route):
                    generated = grounded_fallback(
                        req.message,
                        issue,
                        docs,
                        route,
                        req.state,
                        req.disco,
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
                    model_ready=self.settings.challenge_model_ready,
                    asr_ready=self.settings.challenge_asr_ready,
                )
        interaction_id = self.validation.add_interaction(
            session_id=req.session_id,
            language=req.language,
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
            escalation=route,
            sources=to_source_cards(docs),
            language=req.language,
            model=(
                self.settings.natlas_model
                if self.settings.challenge_model_ready
                else "verified-grounded-fallback"
            ),
            disclaimer=DISCLAIMER,
        )

    async def draft_complaint(self, req: ComplaintDraftRequest) -> ComplaintDraftResponse:
        issue = classify_issue(req.message)
        docs = retrieve(req.message, issue)
        route = regulator_for_state(req.state)
        context = "\n".join(f"- {d['text']} ({d['url']})" for d in docs)
        system = (
            "Draft a concise, factual Nigerian electricity consumer complaint using only supplied facts and the consumer's details. "
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
        try:
            generated = await self.natlas.generate_json(system, user)
        except Exception:
            generated = {
                "subject": f"Electricity Consumer Complaint — {issue.replace('_', ' ').title()}",
                "body": (
                    f"Dear Customer Complaints Team,\n\nI am writing to lodge a formal complaint concerning the following issue: {req.message}\n\n"
                    "Please investigate this matter, provide a written acknowledgement/reference number, and communicate the resolution in writing. "
                    f"My meter/account details are {req.meter_number or req.account_number or '[insert meter/account number]'}.\n\n"
                    f"Requested resolution: {req.desired_resolution or 'Please resolve the complaint in line with applicable electricity consumer-protection requirements.'}\n\n"
                    f"Yours faithfully,\n{req.complainant_name or '[Name]'}"
                ),
                "checklist": ["Meter or account number", "Relevant bills/receipts", "Previous complaint acknowledgement", "Photos or token history where relevant"],
            }
        return ComplaintDraftResponse(
            subject=str(generated.get("subject", "Electricity Consumer Complaint")),
            body=str(generated.get("body", "")),
            destination=route,
            checklist=[str(x) for x in generated.get("checklist", [])][:8],
        )
