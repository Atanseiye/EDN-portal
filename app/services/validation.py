import csv
import hashlib
import io
import sqlite3
import uuid
from datetime import datetime, timezone
from app.config import Settings
from app.models import FeedbackRequest

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
        else:
            with self._sqlite() as con:
                con.executescript(SQLITE_SCHEMA)

    def add_interaction(self, *, session_id: str | None, language: str, issue_type: str, state: str | None,
                        disco: str | None, channel: str, asr_provider: str | None = None,
                        transcript: str | None = None, store_transcript: bool = False) -> str:
        interaction_id = str(uuid.uuid4())
        session_hash = hashlib.sha256(session_id.encode()).hexdigest()[:20] if session_id else None
        values = (
            interaction_id,
            datetime.now(timezone.utc),
            session_hash,
            language,
            issue_type,
            state,
            disco,
            channel,
            self.settings.natlas_provider,
            asr_provider,
            bool(store_transcript),
            transcript if store_transcript else None,
        )
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute("INSERT INTO interactions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", values)
        else:
            sqlite_values = list(values)
            sqlite_values[1] = sqlite_values[1].isoformat()
            sqlite_values[10] = int(sqlite_values[10])
            with self._sqlite() as con:
                con.execute("INSERT INTO interactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", tuple(sqlite_values))
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

    def _rows(self):
        query = """SELECT i.id, i.created_at, i.language, i.issue_type, i.state, i.disco, i.channel,
                          i.natlas_provider, i.asr_provider, f.helpful, f.understood_language,
                          f.resolved_or_actionable, f.notes, f.consent_to_validation
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
        writer.writerow(["interaction_id","created_at","language","issue_type","state","disco","channel",
                         "natlas_provider","asr_provider","helpful","understood_language","resolved_or_actionable",
                         "notes","consent_to_validation"])
        for row in rows:
            writer.writerow(list(row))
        return out.getvalue()

    def stats(self) -> dict:
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute("SELECT count(*) FROM interactions")
                    total = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM interactions WHERE channel='voice' AND asr_provider!='mock' AND natlas_provider!='mock'")
                    real_voice = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM feedback WHERE consent_to_validation=TRUE")
                    feedback = cur.fetchone()[0]
        else:
            with self._sqlite() as con:
                total = con.execute("SELECT count(*) c FROM interactions").fetchone()["c"]
                real_voice = con.execute(
                    "SELECT count(*) c FROM interactions WHERE channel='voice' AND asr_provider!='mock' AND natlas_provider!='mock'"
                ).fetchone()["c"]
                feedback = con.execute("SELECT count(*) c FROM feedback WHERE consent_to_validation=1").fetchone()["c"]
        return {
            "total_interactions": total,
            "competition_eligible_voice_interactions": real_voice,
            "consented_feedback": feedback,
            "persistent_store": "postgres" if self.use_postgres else "sqlite",
        }
