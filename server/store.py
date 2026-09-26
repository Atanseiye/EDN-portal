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
    consent INTEGER NOT NULL,
    verified_external INTEGER NOT NULL DEFAULT 0,
    verified_at TEXT
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
    consent BOOLEAN NOT NULL,
    verified_external BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMPTZ
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
                    cur.execute(
                        "ALTER TABLE beta_feedback ADD COLUMN IF NOT EXISTS "
                        "verified_external BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                    cur.execute(
                        "ALTER TABLE beta_feedback ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ"
                    )
        else:
            with self._sqlite() as con:
                con.execute(SQLITE_SCHEMA)
                columns = {
                    row["name"]
                    for row in con.execute("PRAGMA table_info(beta_feedback)").fetchall()
                }
                if "verified_external" not in columns:
                    con.execute(
                        "ALTER TABLE beta_feedback ADD COLUMN "
                        "verified_external INTEGER NOT NULL DEFAULT 0"
                    )
                if "verified_at" not in columns:
                    con.execute(
                        "ALTER TABLE beta_feedback ADD COLUMN verified_at TEXT"
                    )

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

        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO beta_feedback
                        (id,created_at,tester_hash,display_name,affiliation,role,features,
                         rating,useful,blocker,notes,external_tester,consent,
                         verified_external,verified_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,FALSE,NULL)
                        """,
                        (
                            evidence_id, now, tester_hash, display_name, affiliation, role,
                            json.dumps(features, ensure_ascii=False), int(rating), bool(useful),
                            blocker, notes, bool(external_tester), bool(consent),
                        ),
                    )
        else:
            with self._sqlite() as con:
                con.execute(
                    """
                    INSERT INTO beta_feedback
                    (id,created_at,tester_hash,display_name,affiliation,role,features,
                     rating,useful,blocker,notes,external_tester,consent,
                     verified_external,verified_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,NULL)
                    """,
                    (
                        evidence_id, now.isoformat(), tester_hash, display_name, affiliation,
                        role, json.dumps(features, ensure_ascii=False), int(rating),
                        int(useful), blocker, notes, int(external_tester), int(consent),
                    ),
                )

        print(
            "EDNAI_BETA_EVIDENCE "
            + json.dumps(
                {
                    "event": "submitted",
                    "id": evidence_id,
                    "created_at": now.isoformat(),
                    "tester_hash": tester_hash,
                    "affiliation": affiliation,
                    "role": role,
                    "features": features,
                    "rating": rating,
                    "useful": useful,
                    "external_tester_claimed": external_tester,
                    "consent": consent,
                    "verified_external": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        return evidence_id

    def verify_external(self, evidence_id: str) -> dict:
        now = datetime.now(timezone.utc)
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE beta_feedback
                        SET verified_external=TRUE, verified_at=%s
                        WHERE id=%s AND consent=TRUE AND external_tester=TRUE
                        RETURNING tester_hash
                        """,
                        (now, evidence_id),
                    )
                    row = cur.fetchone()
        else:
            with self._sqlite() as con:
                row = con.execute(
                    "SELECT tester_hash FROM beta_feedback "
                    "WHERE id=? AND consent=1 AND external_tester=1",
                    (evidence_id,),
                ).fetchone()
                if row:
                    con.execute(
                        "UPDATE beta_feedback SET verified_external=1, verified_at=? WHERE id=?",
                        (now.isoformat(), evidence_id),
                    )
        if not row:
            raise KeyError(evidence_id)
        tester_hash = row[0] if not isinstance(row, sqlite3.Row) else row["tester_hash"]
        payload = {
            "event": "verified_external",
            "id": evidence_id,
            "verified_at": now.isoformat(),
            "tester_hash": tester_hash,
        }
        print(
            "EDNAI_BETA_EVIDENCE "
            + json.dumps(payload, ensure_ascii=False, sort_keys=True),
            flush=True,
        )
        return payload

    def pending(self, limit: int = 50) -> list[dict]:
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id,created_at,tester_hash,display_name,affiliation,role,
                               features,rating,useful,blocker,notes
                        FROM beta_feedback
                        WHERE consent=TRUE AND external_tester=TRUE AND verified_external=FALSE
                        ORDER BY created_at DESC LIMIT %s
                        """,
                        (limit,),
                    )
                    rows = cur.fetchall()
            keys = [
                "id","created_at","tester_hash","display_name","affiliation","role",
                "features","rating","useful","blocker","notes"
            ]
            return [dict(zip(keys, row)) for row in rows]

        with self._sqlite() as con:
            rows = con.execute(
                """
                SELECT id,created_at,tester_hash,display_name,affiliation,role,
                       features,rating,useful,blocker,notes
                FROM beta_feedback
                WHERE consent=1 AND external_tester=1 AND verified_external=0
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["features"] = json.loads(item["features"])
            item["useful"] = bool(item["useful"])
            result.append(item)
        return result

    def stats(self) -> dict:
        verified_filter = "consent=TRUE AND external_tester=TRUE AND verified_external=TRUE"
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute("SELECT count(*) FROM beta_feedback WHERE consent=TRUE")
                    total = cur.fetchone()[0]
                    cur.execute(
                        "SELECT count(*) FROM beta_feedback "
                        "WHERE consent=TRUE AND external_tester=TRUE AND verified_external=FALSE"
                    )
                    pending = cur.fetchone()[0]
                    cur.execute(
                        f"SELECT count(DISTINCT tester_hash) FROM beta_feedback WHERE {verified_filter}"
                    )
                    external = cur.fetchone()[0]
                    cur.execute(
                        "SELECT avg(rating), avg(CASE WHEN useful THEN 1.0 ELSE 0.0 END) "
                        f"FROM beta_feedback WHERE {verified_filter}"
                    )
                    avg, useful = cur.fetchone()
        else:
            with self._sqlite() as con:
                total = con.execute(
                    "SELECT count(*) c FROM beta_feedback WHERE consent=1"
                ).fetchone()["c"]
                pending = con.execute(
                    "SELECT count(*) c FROM beta_feedback "
                    "WHERE consent=1 AND external_tester=1 AND verified_external=0"
                ).fetchone()["c"]
                external = con.execute(
                    "SELECT count(DISTINCT tester_hash) c FROM beta_feedback "
                    "WHERE consent=1 AND external_tester=1 AND verified_external=1"
                ).fetchone()["c"]
                row = con.execute(
                    "SELECT avg(rating) rating, avg(useful) useful FROM beta_feedback "
                    "WHERE consent=1 AND external_tester=1 AND verified_external=1"
                ).fetchone()
                avg, useful = row["rating"], row["useful"]

        return {
            "consented_feedback_records": int(total),
            "pending_external_submissions": int(pending),
            "unique_verified_external_beta_testers": int(external),
            "unique_external_beta_testers": int(external),
            "beta_target": 2,
            "beta_target_met": int(external) >= 2,
            "average_rating": round(float(avg), 2) if avg is not None else None,
            "useful_rate": round(float(useful), 4) if useful is not None else None,
            "store": "postgres" if self.use_postgres else "sqlite",
        }
