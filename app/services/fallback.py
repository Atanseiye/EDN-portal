from app.models import IssueType


ELECTRICITY_TERMS = (
    "electricity", "light", "power", "disco", "meter", "metre", "bill", "billing",
    "estimated", "tariff", "band", "token", "vending", "kct", "outage", "blackout",
    "disconnect", "reconnect", "transformer", "feeder", "voltage", "connection",
    "units", "prepaid", "postpaid", "energy", "nerc", "customer complaints"
)


def is_electricity_related(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return any(term in normalized for term in ELECTRICITY_TERMS)


def grounded_fallback(
    message: str,
    issue: IssueType,
    docs: list[dict],
    state: str | None,
    disco: str | None,
) -> dict:
    """Build a deterministic answer from retrieved regulatory facts.

    This is deliberately not presented as N-ATLaS output. It keeps the public
    app useful while the gated official model endpoint is unavailable.
    """
    if issue == "other" and not is_electricity_related(message):
        return {
            "summary": (
                "That does not look like an electricity complaint yet. PowerRights can help with "
                "metering, estimated bills, disconnection, outages, tariff bands, token/vending "
                "problems, new connections and electricity-safety complaints."
            ),
            "rights": [],
            "next_steps": [
                "Describe the electricity problem that happened to you.",
                "Include your state and electricity provider if you know them.",
                "Do not include passwords, PINs or payment-card details.",
            ],
        }

    facts = [d["text"] for d in docs if d.get("text")]
    provider = disco or "your electricity provider"
    location = f" in {state} State" if state else ""

    if issue == "metering":
        summary = (
            f"This appears to be a metering complaint{location}. The verified guidance retrieved for "
            "your case covers defective/removed meters, replacement responsibility and how billing "
            "should be handled while replacement is pending."
        )
        rights = facts[:3]
        steps = [
            f"Write to {provider}'s Customer Complaints Unit and request a complaint/reference number.",
            "State when the meter became faulty or was removed and ask for the replacement status in writing.",
            "Attach previous vending/billing records, meter number and any evidence of removal or fault.",
            "If estimated billing started after removal, specifically challenge the billing basis and keep copies of every bill.",
        ]
    elif issue == "billing":
        summary = (
            f"This appears to be a billing complaint{location}. The retrieved NERC guidance covers "
            "transparent billing, estimated-billing limits and the formal complaint/escalation process."
        )
        rights = facts[:3]
        steps = [
            f"Submit a written billing dispute to {provider}'s Customer Complaints Unit and keep the acknowledgement.",
            "Attach the disputed bill, earlier bills or vending history, meter/account number and payment receipts.",
            "Ask the provider to explain the calculation and correct any unsupported charge in writing.",
            "Escalate through the regulator route shown below if the complaint is not resolved.",
        ]
    elif issue == "disconnection":
        summary = (
            f"This appears to be a disconnection/reconnection complaint{location}. The retrieved "
            "consumer-rights guidance covers notice, complaint handling and escalation."
        )
        rights = facts[:3]
        steps = [
            f"Ask {provider} for the written reason and basis for the disconnection.",
            "Keep the disconnection notice, bills, receipts and previous complaint references.",
            "If you dispute the disconnection, submit the dispute in writing and request a formal response.",
            "Use the regulator route below if the provider does not resolve the complaint.",
        ]
    elif issue == "service_quality":
        summary = (
            f"This appears to be a supply/service-quality complaint{location}, such as an outage, "
            "interruption or voltage problem. PowerRights found complaint-handling guidance relevant to escalation."
        )
        rights = facts[:2]
        steps = [
            f"Report the supply problem to {provider} and obtain a complaint/reference number.",
            "Record dates, approximate durations and any feeder/transformer details you know.",
            "Keep screenshots, messages or other evidence of earlier reports.",
            "Escalate through the regulator route below if the service problem remains unresolved.",
        ]
    elif issue == "tariff_band":
        summary = (
            f"This appears to be a tariff/service-band complaint{location}. The next step is to get "
            "the provider's recorded service band and billing basis in writing and compare it with the applicable regulatory guidance."
        )
        rights = facts[:3]
        steps = [
            f"Ask {provider} to confirm your service band, feeder and billing basis in writing.",
            "Keep bills and a simple record of actual supply hours for the disputed period.",
            "Submit any mismatch as a written complaint and retain the acknowledgement.",
            "Escalate unresolved disputes using the regulator route below.",
        ]
    elif issue == "token_vending":
        summary = (
            f"This appears to be a prepaid-token/vending complaint{location}. The retrieved guidance "
            "includes metering and complaint-handling protections relevant to failed vending or unit-credit issues."
        )
        rights = facts[:3]
        steps = [
            f"Keep the transaction receipt/reference, token, meter number and exact error message.",
            f"Report the failed vending or missing units to {provider} and obtain a complaint reference.",
            "Do not repeatedly repurchase until the original transaction status is confirmed.",
            "Escalate unresolved cases using the regulator route below.",
        ]
    elif issue == "connection":
        summary = (
            f"This appears to be a connection/service-application complaint{location}. PowerRights found "
            "the formal complaint and escalation pathway relevant to an unresolved connection request."
        )
        rights = facts[:2]
        steps = [
            f"Submit or reference the connection request with {provider} in writing.",
            "Keep payment receipts, application/reference numbers and correspondence.",
            "Ask for the outstanding requirement or reason for delay in writing.",
            "Escalate through the regulator route below if the complaint remains unresolved.",
        ]
    elif issue == "safety":
        summary = (
            f"This appears to involve an electricity-safety risk{location}. Safety issues should be treated "
            "as urgent; do not touch, bypass or attempt to repair dangerous electricity infrastructure yourself."
        )
        rights = facts[:2]
        steps = [
            f"Report the hazard immediately through {provider}'s official emergency/customer-service channel.",
            "Keep a safe distance from fallen wires, sparking equipment or exposed live conductors.",
            "Record the location and report reference; take photographs only if it is safe to do so.",
            "Escalate persistent public-safety hazards through the regulator route shown below.",
        ]
    else:
        summary = (
            f"This appears to be electricity-related{location}, but PowerRights could not confidently place it "
            "in one complaint category. The retrieved sources below are the closest verified guidance."
        )
        rights = facts[:2]
        steps = [
            f"Submit the issue to {provider}'s Customer Complaints Unit in writing.",
            "Include your meter/account number, dates, previous complaint references and supporting evidence.",
            "Use the regulator route below if the complaint remains unresolved.",
        ]

    return {
        "summary": summary,
        "rights": rights,
        "next_steps": steps,
    }
