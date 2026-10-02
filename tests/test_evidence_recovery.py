import hashlib
import json
import uuid

import pytest

from server.evidence_recovery import restore_recorded_submissions
from server.store import BetaStore


def record(**changes):
    return {
        "event": "submitted", "id": str(uuid.uuid4()),
        "created_at": "2026-10-02T05:31:40.091371+00:00",
        "tester_hash": hashlib.sha256(b"tester@example.invalid").hexdigest()[:24],
        "affiliation": "External Lab", "role": "Developer", "features": ["python_sdk"],
        "rating": 5, "useful": True, "external_tester_claimed": True, "consent": True,
        "verified_external": False, **changes,
    }


def test_recovery_preserves_original_identity_and_requires_review(tmp_path):
    store = BetaStore(str(tmp_path / "feedback.sqlite3"))
    source = record()
    snapshot = json.dumps([source])
    assert restore_recorded_submissions(store, snapshot) == 1
    row = store.pending()[0]
    assert row["id"] == source["id"]
    assert row["created_at"] == source["created_at"]
    assert row["tester_hash"] == source["tester_hash"]
    assert row["features"] == source["features"]
    assert row["rating"] == 5
    assert row["notes"] is None
    assert store.stats()["unique_external_beta_submissions"] == 1
    assert store.stats()["unique_verified_external_beta_testers"] == 0
    store.add(
        tester_identity="TESTER@example.invalid", display_name=None, affiliation=None,
        role=None, features=["playground"], rating=4, useful=True, blocker=None,
        notes=None, external_tester=True, consent=True,
    )
    assert store.stats()["unique_external_beta_submissions"] == 1
    store.verify_external(source["id"])
    assert restore_recorded_submissions(store, snapshot) == 0
    assert store.stats()["unique_verified_external_beta_testers"] == 1


def test_recovery_preserves_optional_fields_when_export_contains_them(tmp_path):
    store = BetaStore(str(tmp_path / "feedback.sqlite3"))
    source = record(display_name="Tester", blocker="A blocker", notes="Original notes")
    restore_recorded_submissions(store, json.dumps([source]))
    row = store.pending()[0]
    for field in ["display_name", "blocker", "notes"]:
        assert row[field] == source[field]


@pytest.mark.parametrize("changes", [
    {"consent": False}, {"verified_external": True}, {"tester_hash": "invalid"},
    {"id": "invalid"}, {"created_at": "2026-10-02T05:31:40"}, {"rating": 6},
    {"rating": True}, {"features": []},
])
def test_invalid_snapshot_fails_before_any_record_is_written(tmp_path, changes):
    store = BetaStore(str(tmp_path / "feedback.sqlite3"))
    with pytest.raises(ValueError, match="Invalid beta evidence recovery snapshot"):
        restore_recorded_submissions(store, json.dumps([record(), record(**changes)]))
    assert store.stats()["consented_feedback_records"] == 0


def test_empty_snapshot_has_no_effect(tmp_path):
    store = BetaStore(str(tmp_path / "feedback.sqlite3"))
    assert restore_recorded_submissions(store, "") == 0
