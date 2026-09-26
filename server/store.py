from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


SQLITE_SCHEMA = """
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

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS beta_feedback (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    tester_hash TEXT NOT NULL,
    display_name TEXT,
    affiliation TEXT,
    role TEXT,
    features JSONB NOT NULL,
    rating INTEGER NOT NULL,
    useful BOOLEAN NOT NULL,
    blocker TEXT,
    notes TEXT,
    external_tester BOOLEAN NOT NULL,
    consent BOOLEAN NOT NULL
)
"""


class BetaStore:
    def __init__(self, sqlite_path: str, database_url: str | None = None):
        self.sqlite_path = sqlite_path
        self.database_url = database_url
        self.use_postgres = bool(database_url)
        self._init()

    def _sqlite(self):
        Path(self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.sqlite_path)
        con.row_factory = sqlite3.Row
        return con

    def _postgres(self):
        import psycopg
        return psycopg.connect(self.database_url)

    def _init(self):
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(POSTGRES_SCHEMA)
        else:
            with self._sqlite() as con:
                con.execute(SQLITE_SCHEMA)

    def add(
        self,
        *,
        tester_identity: str,
        display_name: str | None,
        affiliation: str | None,
        role: str | None,
        features: list[str],
        rating: int,
        useful: bool,
        blocker: str | None,
        notes: str | None,
        external_tester: bool,
        consent: bool,
    ) -> str:
        if not consent:
            raise ValueError("Validation consent is required")
        if not tester_identity.strip():
            raise ValueError("A stable tester identifier is required")

        evidence_id = str(uuid.uuid4())
        tester_hash = hashlib.sha256(
            tester_identity.strip().lower().encode()
        ).hexdigest()[:24]
        now = datetime.now(timezone.utc)

        values = (
            evidence_id,
            now,
            tester_hash,
            display_name,
            affiliation,
            role,
            features,
            int(rating),
            bool(useful),
            blocker,
            notes,
            bool(external_tester),
            bool(consent),
        )

        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO beta_feedback
                        (id,created_at,tester_hash,display_name,affiliation,role,features,rating,useful,blocker,notes,external_tester,consent)
                        VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            *values[:6],
                            json.dumps(features, ensure_ascii=False),
                            *values[7:],
                        ),
                    )
        else:
            with self._sqlite() as con:
                con.execute(
                    """
                    INSERT INTO beta_feedback
                    (id,created_at,tester_hash,display_name,affiliation,role,features,rating,useful,blocker,notes,external_tester,consent)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        evidence_id,
                        now.isoformat(),
                        tester_hash,
                        display_name,
                        affiliation,
                        role,
                        json.dumps(features, ensure_ascii=False),
                        int(rating),
                        int(useful),
                        blocker,
                        notes,
                        int(external_tester),
                        int(consent),
                    ),
                )

        print(
            "EDNAI_BETA_EVIDENCE "
            + json.dumps(
                {
                    "id": evidence_id,
                    "created_at": now.isoformat(),
                    "tester_hash": tester_hash,
                    "affiliation": affiliation,
                    "role": role,
                    "features": features,
                    "rating": rating,
                    "useful": useful,
                    "external_tester": external_tester,
                    "consent": consent,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        return evidence_id

    def stats(self) -> dict:
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute("SELECT count(*) FROM beta_feedback WHERE consent=TRUE")
                    total = cur.fetchone()[0]
                    cur.execute(
                        "SELECT count(DISTINCT tester_hash) FROM beta_feedback WHERE consent=TRUE AND external_tester=TRUE"
                    )
                    external = cur.fetchone()[0]
                    cur.execute(
                        "SELECT avg(rating), avg(CASE WHEN useful THEN 1.0 ELSE 0.0 END) "
                        "FROM beta_feedback WHERE consent=TRUE AND external_tester=TRUE"
                    )
                    avg, useful = cur.fetchone()
        else:
            with self._sqlite() as con:
                total = con.execute(
                    "SELECT count(*) c FROM beta_feedback WHERE consent=1"
                ).fetchone()["c"]
                external = con.execute(
                    "SELECT count(DISTINCT tester_hash) c FROM beta_feedback WHERE consent=1 AND external_tester=1"
                ).fetchone()["c"]
                row = con.execute(
                    "SELECT avg(rating) rating, avg(useful) useful "
                    "FROM beta_feedback WHERE consent=1 AND external_tester=1"
                ).fetchone()
                avg, useful = row["rating"], row["useful"]

        return {
            "consented_feedback_records": int(total),
            "unique_external_beta_testers": int(external),
            "beta_target": 2,
            "beta_target_met": int(external) >= 2,
            "average_rating": round(float(avg), 2) if avg is not None else None,
            "useful_rate": round(float(useful), 4) if useful is not None else None,
            "store": "postgres" if self.use_postgres else "sqlite",
        }
