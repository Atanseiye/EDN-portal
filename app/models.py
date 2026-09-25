from typing import Literal
from pydantic import BaseModel, Field

Language = Literal["english", "yoruba", "hausa", "igbo"]
IssueType = Literal[
    "billing",
    "metering",
    "disconnection",
    "service_quality",
    "tariff_band",
    "token_vending",
    "connection",
    "safety",
    "other",
]


class AdviceRequest(BaseModel):
    message: str = Field(min_length=3, max_length=5000)
    language: Language = "english"
    state: str | None = None
    disco: str | None = None
    meter_number: str | None = None
    account_number: str | None = None
    session_id: str | None = None


class SourceCard(BaseModel):
    title: str
    authority: str
    url: str
    excerpt: str
    updated: str | None = None


class RegulatorRoute(BaseModel):
    level: Literal["state", "federal"]
    regulator_name: str
    email: str | None = None
    website: str | None = None
    phone: str | None = None
    address: str | None = None
    note: str


class AdviceResponse(BaseModel):
    interaction_id: str
    issue_type: IssueType
    summary: str
    rights: list[str]
    next_steps: list[str]
    escalation: RegulatorRoute
    sources: list[SourceCard]
    draft_ready: bool = True
    language: Language
    model: str
    grounded: bool = True
    disclaimer: str


class ComplaintDraftRequest(AdviceRequest):
    complainant_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    desired_resolution: str | None = None


class ComplaintDraftResponse(BaseModel):
    subject: str
    body: str
    destination: RegulatorRoute
    checklist: list[str]


class FeedbackRequest(BaseModel):
    interaction_id: str
    helpful: bool
    understood_language: bool | None = None
    resolved_or_actionable: bool | None = None
    notes: str | None = Field(default=None, max_length=1000)
    consent_to_validation: bool = True
