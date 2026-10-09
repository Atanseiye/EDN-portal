from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_SCOPES = [
    "inference.generate",
    "inference.chat",
    "usecases.run",
    "speech.transcribe",
]

ALL_SCOPES = [
    "inference.generate",
    "inference.chat",
    "usecases.run",
    "speech.transcribe",
    "evaluation.run",
    "dataset.inspect",
    "finetuning.plan",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _password_hash(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        310_000,
    )
    return salt.hex(), digest.hex()


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS developer_accounts (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS developer_wallets (
    developer_id TEXT PRIMARY KEY,
    balance_microusd INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(developer_id) REFERENCES developer_accounts(id)
);
CREATE TABLE IF NOT EXISTS developer_sessions (
    id TEXT PRIMARY KEY,
    developer_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY(developer_id) REFERENCES developer_accounts(id)
);
CREATE TABLE IF NOT EXISTS developer_api_keys (
    id TEXT PRIMARY KEY,
    developer_id TEXT NOT NULL,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    scopes TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_used_at TEXT,
    revoked_at TEXT,
    FOREIGN KEY(developer_id) REFERENCES developer_accounts(id)
);
CREATE TABLE IF NOT EXISTS developer_ledger (
    id TEXT PRIMARY KEY,
    developer_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    amount_microusd INTEGER NOT NULL,
    reference TEXT,
    description TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(developer_id) REFERENCES developer_accounts(id)
);
CREATE TABLE IF NOT EXISTS developer_usage (
    id TEXT PRIMARY KEY,
    developer_id TEXT NOT NULL,
    api_key_id TEXT,
    request_id TEXT NOT NULL UNIQUE,
    feature TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    measurement TEXT NOT NULL,
    cost_microusd INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(developer_id) REFERENCES developer_accounts(id),
    FOREIGN KEY(api_key_id) REFERENCES developer_api_keys(id)
);
CREATE INDEX IF NOT EXISTS idx_dev_sessions_hash ON developer_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_dev_keys_hash ON developer_api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_dev_usage_account ON developer_usage(developer_id, created_at);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS developer_accounts (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    is_demo BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS developer_wallets (
    developer_id TEXT PRIMARY KEY REFERENCES developer_accounts(id),
    balance_microusd BIGINT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS developer_sessions (
    id TEXT PRIMARY KEY,
    developer_id TEXT NOT NULL REFERENCES developer_accounts(id),
    token_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS developer_api_keys (
    id TEXT PRIMARY KEY,
    developer_id TEXT NOT NULL REFERENCES developer_accounts(id),
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    scopes JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS developer_ledger (
    id TEXT PRIMARY KEY,
    developer_id TEXT NOT NULL REFERENCES developer_accounts(id),
    kind TEXT NOT NULL,
    amount_microusd BIGINT NOT NULL,
    reference TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS developer_usage (
    id TEXT PRIMARY KEY,
    developer_id TEXT NOT NULL REFERENCES developer_accounts(id),
    api_key_id TEXT REFERENCES developer_api_keys(id),
    request_id TEXT NOT NULL UNIQUE,
    feature TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    measurement TEXT NOT NULL,
    cost_microusd BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dev_sessions_hash ON developer_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_dev_keys_hash ON developer_api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_dev_usage_account ON developer_usage(developer_id, created_at);
"""


class DeveloperStore:
    def __init__(self, sqlite_path: str, database_url: str | None = None):
        self.sqlite_path = sqlite_path
        self.database_url = database_url
        self.use_postgres = bool(database_url)
        if os.environ.get("EDNAI_SKIP_DB_INIT") != "true":
            self._init()

    def _sqlite(self):
        Path(self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.sqlite_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def _postgres(self):
        from server.postgres import connect
        return connect(self.database_url)

    def ping(self) -> bool:
        try:
            if self.use_postgres:
                with self._postgres() as con:
                    with con.cursor() as cur:
                        cur.execute("SELECT 1")
                        return cur.fetchone()[0] == 1
            with self._sqlite() as con:
                return con.execute("SELECT 1").fetchone()[0] == 1
        except Exception:
            return False

    def _init(self):
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(POSTGRES_SCHEMA)
                    cur.execute(
                        """
                        INSERT INTO developer_wallets (developer_id,balance_microusd)
                        SELECT a.id, COALESCE(sum(l.amount_microusd),0)
                        FROM developer_accounts a
                        LEFT JOIN developer_ledger l ON l.developer_id=a.id
                        GROUP BY a.id
                        ON CONFLICT (developer_id) DO NOTHING
                        """
                    )
        else:
            with self._sqlite() as con:
                con.executescript(SQLITE_SCHEMA)
                con.execute(
                    """
                    INSERT OR IGNORE INTO developer_wallets (developer_id,balance_microusd)
                    SELECT a.id, COALESCE(sum(l.amount_microusd),0)
                    FROM developer_accounts a
                    LEFT JOIN developer_ledger l ON l.developer_id=a.id
                    GROUP BY a.id
                    """
                )

    def create_account(
        self,
        email: str,
        password: str,
        *,
        display_name: str | None = None,
        is_demo: bool = False,
        initial_credit_microusd: int = 0,
    ) -> dict[str, Any]:
        email = email.strip().lower()
        if "@" not in email:
            raise ValueError("A valid email address is required.")
        if not is_demo and len(password) < 10:
            raise ValueError("Passwords must be at least 10 characters.")
        if is_demo and not password:
            raise ValueError("Demo password is required.")

        account_id = str(uuid.uuid4())
        salt, digest = _password_hash(password)
        now = _now()

        try:
            if self.use_postgres:
                with self._postgres() as con:
                    with con.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO developer_accounts
                            (id,email,display_name,password_salt,password_hash,status,is_demo,created_at)
                            VALUES (%s,%s,%s,%s,%s,'active',%s,%s)
                            """,
                            (account_id, email, display_name, salt, digest, is_demo, now),
                        )
                        cur.execute(
                            "INSERT INTO developer_wallets (developer_id,balance_microusd) VALUES (%s,0)",
                            (account_id,),
                        )
            else:
                with self._sqlite() as con:
                    con.execute(
                        """
                        INSERT INTO developer_accounts
                        (id,email,display_name,password_salt,password_hash,status,is_demo,created_at)
                        VALUES (?,?,?,?,?,'active',?,?)
                        """,
                        (
                            account_id, email, display_name, salt, digest,
                            int(is_demo), now.isoformat(),
                        ),
                    )
                    con.execute(
                        "INSERT INTO developer_wallets (developer_id,balance_microusd) VALUES (?,0)",
                        (account_id,),
                    )
        except Exception as exc:
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise ValueError("An account with that email already exists.") from exc
            raise

        if initial_credit_microusd:
            self.add_ledger_entry(
                account_id,
                kind="credit",
                amount_microusd=initial_credit_microusd,
                reference="initial-credit",
                description="Initial developer credit",
            )
        return self.account(account_id)

    def ensure_demo_account(
        self,
        email: str,
        password: str,
        *,
        initial_credit_microusd: int,
    ) -> dict[str, Any]:
        existing = self.account_by_email(email)
        if existing:
            return existing
        return self.create_account(
            email,
            password,
            display_name="EDNAi Demo Developer",
            is_demo=True,
            initial_credit_microusd=initial_credit_microusd,
        )

    def account_by_email(self, email: str) -> dict[str, Any] | None:
        email = email.strip().lower()
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id,email,display_name,status,is_demo,created_at
                        FROM developer_accounts WHERE email=%s
                        """,
                        (email,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    keys = ["id","email","display_name","status","is_demo","created_at"]
                    result = dict(zip(keys,row))
        else:
            with self._sqlite() as con:
                row = con.execute(
                    """
                    SELECT id,email,display_name,status,is_demo,created_at
                    FROM developer_accounts WHERE email=?
                    """,
                    (email,),
                ).fetchone()
                if not row:
                    return None
                result = dict(row)
                result["is_demo"] = bool(result["is_demo"])
        result["balance_microusd"] = self.balance_microusd(result["id"])
        return result

    def account(self, account_id: str) -> dict[str, Any]:
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id,email,display_name,status,is_demo,created_at
                        FROM developer_accounts WHERE id=%s
                        """,
                        (account_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise KeyError(account_id)
                    result = dict(zip(
                        ["id","email","display_name","status","is_demo","created_at"], row
                    ))
        else:
            with self._sqlite() as con:
                row = con.execute(
                    """
                    SELECT id,email,display_name,status,is_demo,created_at
                    FROM developer_accounts WHERE id=?
                    """,
                    (account_id,),
                ).fetchone()
                if not row:
                    raise KeyError(account_id)
                result = dict(row)
                result["is_demo"] = bool(result["is_demo"])
        result["balance_microusd"] = self.balance_microusd(account_id)
        return result

    def verify_password(self, email: str, password: str) -> dict[str, Any] | None:
        email = email.strip().lower()
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id,email,display_name,status,is_demo,created_at,password_salt,password_hash
                        FROM developer_accounts WHERE email=%s
                        """,
                        (email,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    keys = [
                        "id","email","display_name","status","is_demo","created_at",
                        "password_salt","password_hash",
                    ]
                    data = dict(zip(keys,row))
        else:
            with self._sqlite() as con:
                row = con.execute(
                    """
                    SELECT id,email,display_name,status,is_demo,created_at,password_salt,password_hash
                    FROM developer_accounts WHERE email=?
                    """,
                    (email,),
                ).fetchone()
                if not row:
                    return None
                data = dict(row)
                data["is_demo"] = bool(data["is_demo"])

        _, candidate = _password_hash(password, data["password_salt"])
        if not hmac.compare_digest(candidate, data["password_hash"]):
            return None
        if data["status"] != "active":
            return None
        data.pop("password_salt", None)
        data.pop("password_hash", None)
        data["balance_microusd"] = self.balance_microusd(data["id"])
        return data

    def create_session(self, developer_id: str, *, hours: int = 24) -> str:
        token = "ednai_session_" + secrets.token_urlsafe(32)
        now = _now()
        # Opportunistic cleanup keeps stale session rows bounded.
        if self.use_postgres:
            with self._postgres() as cleanup_con:
                with cleanup_con.cursor() as cleanup_cur:
                    cleanup_cur.execute(
                        "DELETE FROM developer_sessions WHERE expires_at <= %s OR revoked_at IS NOT NULL",
                        (now,),
                    )
        else:
            with self._sqlite() as cleanup_con:
                cleanup_con.execute(
                    "DELETE FROM developer_sessions WHERE expires_at <= ? OR revoked_at IS NOT NULL",
                    (now.isoformat(),),
                )
        expires = now + timedelta(hours=hours)
        session_id = str(uuid.uuid4())
        token_hash = _hash_secret(token)
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO developer_sessions
                        (id,developer_id,token_hash,created_at,expires_at)
                        VALUES (%s,%s,%s,%s,%s)
                        """,
                        (session_id,developer_id,token_hash,now,expires),
                    )
        else:
            with self._sqlite() as con:
                con.execute(
                    """
                    INSERT INTO developer_sessions
                    (id,developer_id,token_hash,created_at,expires_at)
                    VALUES (?,?,?,?,?)
                    """,
                    (session_id,developer_id,token_hash,now.isoformat(),expires.isoformat()),
                )
        return token

    def resolve_session(self, token: str) -> dict[str, Any] | None:
        token_hash = _hash_secret(token)
        now = _now()
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        SELECT developer_id FROM developer_sessions
                        WHERE token_hash=%s AND revoked_at IS NULL AND expires_at>%s
                        """,
                        (token_hash,now),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    account_id = row[0]
        else:
            with self._sqlite() as con:
                row = con.execute(
                    """
                    SELECT developer_id FROM developer_sessions
                    WHERE token_hash=? AND revoked_at IS NULL AND expires_at>?
                    """,
                    (token_hash,now.isoformat()),
                ).fetchone()
                if not row:
                    return None
                account_id = row["developer_id"]
        return self.account(account_id)

    def revoke_session(self, token: str) -> None:
        token_hash = _hash_secret(token)
        now = _now()
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        "UPDATE developer_sessions SET revoked_at=%s WHERE token_hash=%s",
                        (now,token_hash),
                    )
        else:
            with self._sqlite() as con:
                con.execute(
                    "UPDATE developer_sessions SET revoked_at=? WHERE token_hash=?",
                    (now.isoformat(),token_hash),
                )

    def create_api_key(
        self,
        developer_id: str,
        *,
        name: str,
        scopes: list[str],
    ) -> dict[str, Any]:
        invalid = sorted(set(scopes) - set(ALL_SCOPES))
        if invalid:
            raise ValueError("Unknown API-key scopes: " + ", ".join(invalid))
        if not scopes:
            raise ValueError("At least one API-key scope is required.")

        secret = "ednai_live_" + secrets.token_urlsafe(32)
        key_id = str(uuid.uuid4())
        prefix = secret[:18]
        digest = _hash_secret(secret)
        now = _now()
        scopes = sorted(set(scopes))

        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO developer_api_keys
                        (id,developer_id,name,key_prefix,key_hash,scopes,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)
                        """,
                        (key_id,developer_id,name.strip() or "API key",prefix,digest,json.dumps(scopes),now),
                    )
        else:
            with self._sqlite() as con:
                con.execute(
                    """
                    INSERT INTO developer_api_keys
                    (id,developer_id,name,key_prefix,key_hash,scopes,created_at)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        key_id,developer_id,name.strip() or "API key",prefix,digest,
                        json.dumps(scopes),now.isoformat(),
                    ),
                )
        return {
            "id": key_id,
            "name": name.strip() or "API key",
            "key": secret,
            "prefix": prefix,
            "scopes": scopes,
            "created_at": now.isoformat(),
        }

    def list_api_keys(self, developer_id: str) -> list[dict[str, Any]]:
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id,name,key_prefix,scopes,created_at,last_used_at,revoked_at
                        FROM developer_api_keys
                        WHERE developer_id=%s ORDER BY created_at DESC
                        """,
                        (developer_id,),
                    )
                    rows = cur.fetchall()
            result=[]
            keys=["id","name","prefix","scopes","created_at","last_used_at","revoked_at"]
            for row in rows:
                item=dict(zip(keys,row))
                if isinstance(item["scopes"], str):
                    item["scopes"]=json.loads(item["scopes"])
                result.append(item)
            return result
        with self._sqlite() as con:
            rows=con.execute(
                """
                SELECT id,name,key_prefix,scopes,created_at,last_used_at,revoked_at
                FROM developer_api_keys
                WHERE developer_id=? ORDER BY created_at DESC
                """,
                (developer_id,),
            ).fetchall()
        result=[]
        for row in rows:
            item=dict(row)
            item["prefix"]=item.pop("key_prefix")
            item["scopes"]=json.loads(item["scopes"])
            result.append(item)
        return result

    def revoke_api_key(self, developer_id: str, key_id: str) -> bool:
        now=_now()
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE developer_api_keys SET revoked_at=%s
                        WHERE id=%s AND developer_id=%s AND revoked_at IS NULL
                        """,
                        (now,key_id,developer_id),
                    )
                    return cur.rowcount > 0
        with self._sqlite() as con:
            cur=con.execute(
                """
                UPDATE developer_api_keys SET revoked_at=?
                WHERE id=? AND developer_id=? AND revoked_at IS NULL
                """,
                (now.isoformat(),key_id,developer_id),
            )
            return cur.rowcount > 0

    def resolve_api_key(self, key: str) -> dict[str, Any] | None:
        digest=_hash_secret(key)
        now=_now()
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        SELECT k.id,k.developer_id,k.scopes,a.status,a.email,a.is_demo
                        FROM developer_api_keys k
                        JOIN developer_accounts a ON a.id=k.developer_id
                        WHERE k.key_hash=%s AND k.revoked_at IS NULL
                        """,
                        (digest,),
                    )
                    row=cur.fetchone()
                    if not row:
                        return None
                    key_id,developer_id,scopes,status,email,is_demo=row
                    if isinstance(scopes,str):
                        scopes=json.loads(scopes)
                    cur.execute(
                        "UPDATE developer_api_keys SET last_used_at=%s WHERE id=%s",
                        (now,key_id),
                    )
        else:
            with self._sqlite() as con:
                row=con.execute(
                    """
                    SELECT k.id,k.developer_id,k.scopes,a.status,a.email,a.is_demo
                    FROM developer_api_keys k
                    JOIN developer_accounts a ON a.id=k.developer_id
                    WHERE k.key_hash=? AND k.revoked_at IS NULL
                    """,
                    (digest,),
                ).fetchone()
                if not row:
                    return None
                key_id=row["id"]
                developer_id=row["developer_id"]
                scopes=json.loads(row["scopes"])
                status=row["status"]
                email=row["email"]
                is_demo=bool(row["is_demo"])
                con.execute(
                    "UPDATE developer_api_keys SET last_used_at=? WHERE id=?",
                    (now.isoformat(),key_id),
                )
        if status != "active":
            return None
        return {
            "developer_id": developer_id,
            "api_key_id": key_id,
            "email": email,
            "is_demo": bool(is_demo),
            "scopes": list(scopes),
        }

    def add_ledger_entry(
        self,
        developer_id: str,
        *,
        kind: str,
        amount_microusd: int,
        reference: str | None = None,
        description: str | None = None,
    ) -> str:
        entry_id=str(uuid.uuid4())
        now=_now()
        amount=int(amount_microusd)
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    if amount < 0:
                        cur.execute(
                            """
                            UPDATE developer_wallets
                            SET balance_microusd=balance_microusd+%s
                            WHERE developer_id=%s AND balance_microusd >= %s
                            RETURNING balance_microusd
                            """,
                            (amount,developer_id,-amount),
                        )
                        if not cur.fetchone():
                            raise ValueError("Insufficient developer credit.")
                    else:
                        cur.execute(
                            """
                            UPDATE developer_wallets
                            SET balance_microusd=balance_microusd+%s
                            WHERE developer_id=%s
                            """,
                            (amount,developer_id),
                        )
                        if cur.rowcount != 1:
                            raise KeyError(developer_id)
                    cur.execute(
                        """
                        INSERT INTO developer_ledger
                        (id,developer_id,kind,amount_microusd,reference,description,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (entry_id,developer_id,kind,amount,reference,description,now),
                    )
        else:
            with self._sqlite() as con:
                con.execute("BEGIN IMMEDIATE")
                if amount < 0:
                    cur=con.execute(
                        """
                        UPDATE developer_wallets
                        SET balance_microusd=balance_microusd+?
                        WHERE developer_id=? AND balance_microusd >= ?
                        """,
                        (amount,developer_id,-amount),
                    )
                    if cur.rowcount != 1:
                        raise ValueError("Insufficient developer credit.")
                else:
                    cur=con.execute(
                        """
                        UPDATE developer_wallets
                        SET balance_microusd=balance_microusd+?
                        WHERE developer_id=?
                        """,
                        (amount,developer_id),
                    )
                    if cur.rowcount != 1:
                        raise KeyError(developer_id)
                con.execute(
                    """
                    INSERT INTO developer_ledger
                    (id,developer_id,kind,amount_microusd,reference,description,created_at)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        entry_id,developer_id,kind,amount,reference,
                        description,now.isoformat(),
                    ),
                )
        return entry_id

    def balance_microusd(self, developer_id: str) -> int:
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        "SELECT balance_microusd FROM developer_wallets WHERE developer_id=%s",
                        (developer_id,),
                    )
                    row=cur.fetchone()
                    return int(row[0]) if row else 0
        with self._sqlite() as con:
            row=con.execute(
                "SELECT balance_microusd FROM developer_wallets WHERE developer_id=?",
                (developer_id,),
            ).fetchone()
            return int(row["balance_microusd"]) if row else 0

    def record_usage(
        self,
        *,
        developer_id: str,
        api_key_id: str | None,
        request_id: str,
        feature: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        measurement: str,
        cost_microusd: int,
    ) -> dict[str, Any]:
        usage_id=str(uuid.uuid4())
        now=_now()
        total_tokens=int(prompt_tokens)+int(completion_tokens)
        cost=int(cost_microusd)

        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE developer_wallets
                        SET balance_microusd=balance_microusd-%s
                        WHERE developer_id=%s AND balance_microusd >= %s
                        RETURNING balance_microusd
                        """,
                        (cost,developer_id,cost),
                    )
                    wallet=cur.fetchone()
                    if not wallet:
                        raise ValueError("Insufficient developer credit.")
                    balance=int(wallet[0])
                    cur.execute(
                        """
                        INSERT INTO developer_usage
                        (id,developer_id,api_key_id,request_id,feature,model,prompt_tokens,
                         completion_tokens,total_tokens,measurement,cost_microusd,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            usage_id,developer_id,api_key_id,request_id,feature,model,
                            prompt_tokens,completion_tokens,total_tokens,measurement,cost,now,
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO developer_ledger
                        (id,developer_id,kind,amount_microusd,reference,description,created_at)
                        VALUES (%s,%s,'usage_charge',%s,%s,%s,%s)
                        """,
                        (
                            str(uuid.uuid4()),developer_id,-cost,request_id,
                            f"{feature}: {total_tokens} tokens ({measurement})",now,
                        ),
                    )
        else:
            with self._sqlite() as con:
                con.execute("BEGIN IMMEDIATE")
                cur=con.execute(
                    """
                    UPDATE developer_wallets
                    SET balance_microusd=balance_microusd-?
                    WHERE developer_id=? AND balance_microusd >= ?
                    """,
                    (cost,developer_id,cost),
                )
                if cur.rowcount != 1:
                    raise ValueError("Insufficient developer credit.")
                balance=int(con.execute(
                    "SELECT balance_microusd FROM developer_wallets WHERE developer_id=?",
                    (developer_id,),
                ).fetchone()["balance_microusd"])
                con.execute(
                    """
                    INSERT INTO developer_usage
                    (id,developer_id,api_key_id,request_id,feature,model,prompt_tokens,
                     completion_tokens,total_tokens,measurement,cost_microusd,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        usage_id,developer_id,api_key_id,request_id,feature,model,
                        prompt_tokens,completion_tokens,total_tokens,measurement,cost,
                        now.isoformat(),
                    ),
                )
                con.execute(
                    """
                    INSERT INTO developer_ledger
                    (id,developer_id,kind,amount_microusd,reference,description,created_at)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (
                        str(uuid.uuid4()),developer_id,"usage_charge",-cost,
                        request_id,f"{feature}: {total_tokens} tokens ({measurement})",
                        now.isoformat(),
                    ),
                )
        return {
            "id":usage_id,
            "request_id":request_id,
            "feature":feature,
            "prompt_tokens":int(prompt_tokens),
            "completion_tokens":int(completion_tokens),
            "total_tokens":total_tokens,
            "measurement":measurement,
            "cost_microusd":cost,
            "balance_microusd":balance,
        }

    def usage_summary(self, developer_id: str, *, limit: int = 50) -> dict[str, Any]:
        if self.use_postgres:
            with self._postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        SELECT feature,prompt_tokens,completion_tokens,total_tokens,
                               measurement,cost_microusd,request_id,created_at
                        FROM developer_usage
                        WHERE developer_id=%s ORDER BY created_at DESC LIMIT %s
                        """,
                        (developer_id,limit),
                    )
                    rows=cur.fetchall()
            keys=[
                "feature","prompt_tokens","completion_tokens","total_tokens",
                "measurement","cost_microusd","request_id","created_at",
            ]
            events=[dict(zip(keys,row)) for row in rows]
        else:
            with self._sqlite() as con:
                rows=con.execute(
                    """
                    SELECT feature,prompt_tokens,completion_tokens,total_tokens,
                           measurement,cost_microusd,request_id,created_at
                    FROM developer_usage
                    WHERE developer_id=? ORDER BY created_at DESC LIMIT ?
                    """,
                    (developer_id,limit),
                ).fetchall()
            events=[dict(row) for row in rows]

        return {
            "balance_microusd":self.balance_microusd(developer_id),
            "events":events,
            "total_tokens":sum(int(x["total_tokens"]) for x in events),
            "total_cost_microusd":sum(int(x["cost_microusd"]) for x in events),
        }
