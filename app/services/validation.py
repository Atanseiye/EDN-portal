import csv
import hashlib
import io
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from app.config import Settings
from app.models import FeedbackRequest

VALIDATION_TARGET = 50

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  session_hash TEXT,
  language TEXT NOT NULL,
  issue_type TEXT NOT NULL,
  state TEXT,
  disco TEXT,
  channel TEXT NOT NULL,
  natlas_provider TEXT NOT NULL,
  asr_provider TEXT,
  validation_consent INTEGER NOT NULL DEFAULT 0,
  competition_model_path INTEGER NOT NULL DEFAULT 0,
  transcript_stored INTEGER NOT NULL DEFAULT 0,
  transcript TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
  interaction_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  helpful INTEGER NOT NULL,
  understood_language INTEGER,
  resolved_or_actionable INTEGER,
  notes TEXT,
  consent_to_validation INTEGER NOT NULL,
  FOREIGN KEY(interaction_id) REFERENCES interactions(id)
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL,
  session_hash TEXT,
  language TEXT NOT NULL,
  issue_type TEXT NOT NULL,
  state TEXT,
  disco TEXT,
  channel TEXT NOT NULL,
  natlas_provider TEXT NOT NULL,
  asr_provider TEXT,
  validation_consent BOOLEAN NOT NULL DEFAULT FALSE,
  competition_model_path BOOLEAN NOT NULL DEFAULT FALSE,
  transcript_stored BOOLEAN NOT NULL DEFAULT FALSE,
  transcript TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
  interaction_id TEXT PRIMARY KEY REFERENCES interactions(id),
  created_at TIMESTAMPTZ NOT NULL,
  helpful BOOLEAN NOT NULL,
  understood_language BOOLEAN,
  resolved_or_actionable BOOLEAN,
  notes TEXT,
  consent_to_validation BOOLEAN NOT NULL
);
"""


class ValidationStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.use_postgres = bool(settings.database_url)
        self._init()

    def _sqlite(self):
        con = sqlite3.connect(self.settings.database_path)
        con.row_factory = sqlite3.Row
        return con

    def _postgres(self):
        import psycopg
        return psycopg.connect(self.settings.database_url)

    def _init(self):
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    for statement in POSTGRES_SCHEMA.split(";"):
                        if statement.strip():
                            cur.execute(statement)
                    cur.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS validation_consent BOOLEAN NOT NULL DEFAULT FALSE")
                    cur.execute("ALTER TABLE interactions ADD COLUMN IF NOT EXISTS competition_model_path BOOLEAN NOT NULL DEFAULT FALSE")
        else:
            with self._sqlite() as con:
                con.executescript(SQLITE_SCHEMA)
                cols = {row["name"] for row in con.execute("PRAGMA table_info(interactions)").fetchall()}
                if "validation_consent" not in cols:
                    con.execute("ALTER TABLE interactions ADD COLUMN validation_consent INTEGER NOT NULL DEFAULT 0")
                if "competition_model_path" not in cols:
                    con.execute("ALTER TABLE interactions ADD COLUMN competition_model_path INTEGER NOT NULL DEFAULT 0")

    def add_interaction(
        self,
        *,
        session_id: str | None,
        language: str,
        issue_type: str,
        state: str | None,
        disco: str | None,
        channel: str,
        asr_provider: str | None = None,
        transcript: str | None = None,
        store_transcript: bool = False,
        validation_consent: bool = False,
    ) -> str:
        interaction_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        session_hash = hashlib.sha256(session_id.encode()).hexdigest()[:20] if session_id else None
        competition_model_path = bool(
            channel == "voice"
            and validation_consent
            and self.settings.challenge_model_ready
            and self.settings.challenge_asr_ready
            and (asr_provider or "").lower() == self.settings.asr_provider.lower()
        )

        values = (
            interaction_id,
            now,
            session_hash,
            language,
            issue_type,
            state,
            disco,
            channel,
            self.settings.natlas_provider,
            asr_provider,
            validation_consent,
            competition_model_path,
            bool(store_transcript),
            transcript if store_transcript else None,
        )
        columns = (
            "id,created_at,session_hash,language,issue_type,state,disco,channel,"
            "natlas_provider,asr_provider,validation_consent,competition_model_path,"
            "transcript_stored,transcript"
        )

        if self.use_postgres:
            placeholders = ",".join(["%s"] * len(values))
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(f"INSERT INTO interactions ({columns}) VALUES ({placeholders})", values)
        else:
            sqlite_values = list(values)
            sqlite_values[1] = now.isoformat()
            for idx in (10, 11, 12):
                sqlite_values[idx] = int(bool(sqlite_values[idx]))
            placeholders = ",".join(["?"] * len(sqlite_values))
            with self._sqlite() as con:
                con.execute(f"INSERT INTO interactions ({columns}) VALUES ({placeholders})", tuple(sqlite_values))

        _emit_validation_event({
            "event": "interaction",
            "interaction_id": interaction_id,
            "created_at": now.isoformat(),
            "session_hash": session_hash,
            "language": language,
            "issue_type": issue_type,
            "state": state,
            "disco": disco,
            "channel": channel,
            "natlas_provider": self.settings.natlas_provider,
            "asr_provider": asr_provider,
            "validation_consent": validation_consent,
            "competition_model_path": competition_model_path,
        })
        return interaction_id

    def add_feedback(self, data: FeedbackRequest):
        now = datetime.now(timezone.utc)
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute("SELECT 1 FROM interactions WHERE id=%s", (data.interaction_id,))
                    if not cur.fetchone():
                        raise KeyError(data.interaction_id)
                    cur.execute(
                        """INSERT INTO feedback VALUES (%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (interaction_id) DO UPDATE SET
                           created_at=EXCLUDED.created_at, helpful=EXCLUDED.helpful,
                           understood_language=EXCLUDED.understood_language,
                           resolved_or_actionable=EXCLUDED.resolved_or_actionable,
                           notes=EXCLUDED.notes, consent_to_validation=EXCLUDED.consent_to_validation""",
                        (
                            data.interaction_id, now, data.helpful, data.understood_language,
                            data.resolved_or_actionable, data.notes, data.consent_to_validation,
                        ),
                    )
        else:
            with self._sqlite() as con:
                exists = con.execute("SELECT 1 FROM interactions WHERE id=?", (data.interaction_id,)).fetchone()
                if not exists:
                    raise KeyError(data.interaction_id)
                con.execute(
                    "INSERT OR REPLACE INTO feedback VALUES (?,?,?,?,?,?,?)",
                    (
                        data.interaction_id, now.isoformat(), int(data.helpful),
                        None if data.understood_language is None else int(data.understood_language),
                        None if data.resolved_or_actionable is None else int(data.resolved_or_actionable),
                        data.notes, int(data.consent_to_validation),
                    ),
                )

        _emit_validation_event({
            "event": "feedback",
            "interaction_id": data.interaction_id,
            "created_at": now.isoformat(),
            "helpful": data.helpful,
            "understood_language": data.understood_language,
            "resolved_or_actionable": data.resolved_or_actionable,
            "consent_to_validation": data.consent_to_validation,
        })

    def _rows(self):
        query = """SELECT i.id, i.created_at, i.session_hash, i.language, i.issue_type, i.state, i.disco, i.channel,
                          i.natlas_provider, i.asr_provider, i.validation_consent, i.competition_model_path,
                          f.helpful, f.understood_language, f.resolved_or_actionable, f.notes, f.consent_to_validation
                   FROM interactions i LEFT JOIN feedback f ON f.interaction_id=i.id
                   ORDER BY i.created_at"""
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(query)
                    return cur.fetchall()
        with self._sqlite() as con:
            return con.execute(query).fetchall()

    def export_csv(self) -> str:
        rows = self._rows()
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow([
            "interaction_id","created_at","session_hash","language","issue_type","state","disco","channel",
            "natlas_provider","asr_provider","validation_consent","competition_model_path",
            "helpful","understood_language","resolved_or_actionable","notes","feedback_consent"
        ])
        for row in rows:
            writer.writerow(list(row))
        return out.getvalue()

    def stats(self) -> dict:
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute("SELECT count(*) FROM interactions")
                    total = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM interactions WHERE competition_model_path=TRUE")
                    eligible = cur.fetchone()[0]
                    cur.execute("SELECT count(DISTINCT session_hash) FROM interactions WHERE competition_model_path=TRUE AND session_hash IS NOT NULL")
                    unique_users = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM feedback WHERE consent_to_validation=TRUE")
                    feedback = cur.fetchone()[0]
                    cur.execute("SELECT language, count(*) FROM interactions WHERE competition_model_path=TRUE GROUP BY language ORDER BY language")
                    language_rows = cur.fetchall()
        else:
            with self._sqlite() as con:
                total = con.execute("SELECT count(*) c FROM interactions").fetchone()["c"]
                eligible = con.execute("SELECT count(*) c FROM interactions WHERE competition_model_path=1").fetchone()["c"]
                unique_users = con.execute(
                    "SELECT count(DISTINCT session_hash) c FROM interactions WHERE competition_model_path=1 AND session_hash IS NOT NULL"
                ).fetchone()["c"]
                feedback = con.execute("SELECT count(*) c FROM feedback WHERE consent_to_validation=1").fetchone()["c"]
                language_rows = con.execute(
                    "SELECT language, count(*) c FROM interactions WHERE competition_model_path=1 GROUP BY language ORDER BY language"
                ).fetchall()

        language_counts = {str(row[0]): int(row[1]) for row in language_rows}
        remaining = max(0, VALIDATION_TARGET - int(eligible))
        return {
            "total_interactions": int(total),
            "competition_eligible_voice_interactions": int(eligible),
            "unique_validation_sessions": int(unique_users),
            "consented_feedback": int(feedback),
            "language_counts": language_counts,
            "validation_target": VALIDATION_TARGET,
            "remaining_to_target": remaining,
            "validation_target_met": remaining == 0,
            "database_store": "postgres" if self.use_postgres else "sqlite",
            "structured_audit_log": self.settings.validation_audit_log_ready,
        }


def _emit_validation_event(payload: dict) -> None:
    """Structured, non-sensitive evidence retained by the deployment platform."""
    print("POWERRIGHTS_VALIDATION_EVENT " + json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
