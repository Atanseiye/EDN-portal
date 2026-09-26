from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


class BetaStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS beta_feedback (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    tester_hash TEXT NOT NULL,
                    display_name TEXT,
                    affiliation TEXT,
                    role TEXT,
                    features TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    useful INTEGER NOT NULL,
                    blocker TEXT,
                    notes TEXT,
                    external_tester INTEGER NOT NULL,
                    consent INTEGER NOT NULL
                )
                """
            )

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def add(self, *, tester_identity: str, display_name: str | None, affiliation: str | None,
            role: str | None, features: list[str], rating: int, useful: bool,
            blocker: str | None, notes: str | None, external_tester: bool,
            consent: bool) -> str:
        if not consent:
            raise ValueError("Validation consent is required")
        interaction_id = str(uuid.uuid4())
        tester_hash = hashlib.sha256(tester_identity.strip().lower().encode()).hexdigest()[:24]
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as con:
            con.execute(
                "INSERT INTO beta_feedback VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    interaction_id, now, tester_hash, display_name, affiliation, role,
                    json.dumps(features), int(rating), int(useful), blocker, notes,
                    int(external_tester), int(consent),
                ),
            )
        print("EDNAI_BETA_EVIDENCE " + json.dumps({
            "id": interaction_id,
            "created_at": now,
            "tester_hash": tester_hash,
            "affiliation": affiliation,
            "role": role,
            "features": features,
            "rating": rating,
            "useful": useful,
            "external_tester": external_tester,
            "consent": consent,
        }, ensure_ascii=False, sort_keys=True), flush=True)
        return interaction_id

    def stats(self) -> dict:
        with self._connect() as con:
            total = con.execute("SELECT count(*) c FROM beta_feedback WHERE consent=1").fetchone()["c"]
            external = con.execute(
                "SELECT count(DISTINCT tester_hash) c FROM beta_feedback WHERE consent=1 AND external_tester=1"
            ).fetchone()["c"]
            avg = con.execute(
                "SELECT avg(rating) v FROM beta_feedback WHERE consent=1 AND external_tester=1"
            ).fetchone()["v"]
            useful = con.execute(
                "SELECT avg(useful) v FROM beta_feedback WHERE consent=1 AND external_tester=1"
            ).fetchone()["v"]
        return {
            "consented_feedback_records": int(total),
            "unique_external_beta_testers": int(external),
            "beta_target": 2,
            "beta_target_met": int(external) >= 2,
            "average_rating": round(float(avg), 2) if avg is not None else None,
            "useful_rate": round(float(useful), 4) if useful is not None else None,
        }
