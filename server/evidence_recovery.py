"""Restore recorded submissions from an administrator-managed recovery snapshot."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, TypeAdapter, field_validator

from server.store import BetaStore


class RecordedSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: Literal["submitted"]
    id: UUID
    created_at: datetime
    tester_hash: str = Field(pattern=r"^[0-9a-f]{24}$")
    display_name: str | None = None
    affiliation: str | None = None
    role: str | None = None
    features: list[str] = Field(min_length=1)
    rating: StrictInt = Field(ge=1, le=5)
    useful: StrictBool
    blocker: str | None = None
    notes: str | None = None
    external_tester_claimed: StrictBool
    consent: StrictBool
    verified_external: StrictBool = False

    @field_validator("consent")
    @classmethod
    def require_consent(cls, value):
        if not value:
            raise ValueError("Recovery requires recorded consent")
        return value

    @field_validator("verified_external")
    @classmethod
    def keep_review_pending(cls, value):
        if value:
            raise ValueError("Recovery cannot grant external-tester verification")
        return value

    @field_validator("created_at")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None:
            raise ValueError("Recorded timestamps must include a timezone")
        return value


def restore_recorded_submissions(store: BetaStore, snapshot: str) -> int:
    if not snapshot.strip():
        return 0
    try:
        records = TypeAdapter(list[RecordedSubmission]).validate_json(snapshot)
        if len(records) > 1000:
            raise ValueError("Recovery snapshot is too large")
    except ValueError:
        # Do not include feedback text in a startup exception or log.
        raise ValueError("Invalid beta evidence recovery snapshot") from None
    rows = [
        {**record.model_dump(mode="json"), "created_at": record.created_at.isoformat()}
        for record in records
    ]
    return store.restore_submissions(rows)
