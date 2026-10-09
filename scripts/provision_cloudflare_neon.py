"""Provision the separate Cloudflare demo database; never print credential values."""
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def api(base, token, path, method="GET", payload=None):
    service = "Cloudflare" if "cloudflare.com" in base else "Neon"
    operation = urllib.parse.urlsplit(path).path
    request = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.load(response)
            if result.get("success") is False:
                codes = [e.get("code") for e in result.get("errors", [])]
                raise RuntimeError(f"{service} {method} {operation} rejected request (codes: {codes})")
            return result
    except urllib.error.HTTPError as error:
        # API bodies can contain connection strings. Keep failure output redacted.
        raise RuntimeError(f"{service} {method} {operation} failed with HTTP {error.code}") from None
    except urllib.error.URLError:
        raise RuntimeError(f"{service} {method} {operation}: connection unavailable") from None


def main():
    cf_token = os.environ["CLOUDFLARE_API_TOKEN"]
    account = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    neon_token = os.environ["NEON_API_KEY"]
    hf_token = os.environ["HF_TOKEN"]
    cf = lambda path, **kwargs: api("https://api.cloudflare.com/client/v4", cf_token, path, **kwargs)
    neon = lambda path, **kwargs: api("https://console.neon.tech/api/v2", neon_token, path, **kwargs)
    subdomain = cf(f"/accounts/{account}/workers/subdomain")["result"]["subdomain"]
    if not subdomain:
        raise RuntimeError("Configure the account's workers.dev subdomain before deploying")
    origin = f"https://ednai.{subdomain}.workers.dev"
    project_id = os.environ.get("NEON_PROJECT_ID")
    if not project_id:
        # A dedicated demo project avoids mixing public demo and customer data.
        name = "ednai-cloudflare-demo"
        matches = []
        cursor = ""
        while True:
            query = "?limit=100" + ("&cursor=" + urllib.parse.quote(cursor) if cursor else "")
            page = neon("/projects" + query)
            matches.extend(p for p in page["projects"] if p["name"] == name)
            next_cursor = page.get("pagination", {}).get("cursor")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        if len(matches) > 1:
            raise RuntimeError("Multiple demo projects found; set NEON_PROJECT_ID explicitly")
        if matches:
            project_id = matches[0]["id"]
        else:
            result = neon("/projects", method="POST", payload={"project": {
                "name": name, "region_id": os.environ.get("NEON_REGION", "aws-eu-west-2"),
                "pg_version": 17,
            }})
            project_id = result["project"]["id"]
    branches = neon(f"/projects/{project_id}/branches")["branches"]
    branch = next((b for b in branches if b.get("default")), None)
    if branch is None:
        raise RuntimeError("Neon project has no default branch")
    query = urllib.parse.urlencode({"branch_id": branch["id"], "database_name": "neondb",
                                   "role_name": "neondb_owner", "pooled": "true"})
    database = neon(f"/projects/{project_id}/connection_uri?{query}")["uri"]
    parsed = urllib.parse.urlsplit(database)
    params = urllib.parse.parse_qs(parsed.query)
    if "sslmode" not in params:
        database += ("&" if parsed.query else "?") + "sslmode=require"
    config = {
        "APP_ENV": "production", "EDNAI_PROVIDER": "gradio_space",
        "EDNAI_MODEL": "NCAIR1/N-ATLaS",
        "EDNAI_GRADIO_SPACE_ID": os.environ.get("EDNAI_GRADIO_SPACE_ID") or "KoladeOdunope/ednai-natlas-runtime",
        "HF_TOKEN": hf_token,
        "EDNAI_ADMIN_TOKEN": os.environ.get("EDNAI_ADMIN_TOKEN") or secrets.token_urlsafe(48),
        "EDNAI_DATABASE_URL": database,
        "EDNAI_AUTH_ENABLED": "true", "EDNAI_DEMO_ACCOUNT_ENABLED": "true",
        "EDNAI_ALLOW_PUBLIC_DEMO_ACCOUNT": "true", "EDNAI_PRICING_MODE": "production",
        "EDNAI_REQUIRE_EXACT_USAGE": "true",
        "TRUSTED_HOSTS": urllib.parse.urlsplit(origin).hostname,
        "CORS_ORIGINS": origin,
    }
    path = Path(os.environ["RUNNER_TEMP"]) / "ednai-config.json"
    with open(path, "w", opener=lambda p, flags: os.open(p, flags, 0o600)) as stream:
        json.dump(config, stream)
    with open(os.environ["GITHUB_ENV"], "a") as stream:
        stream.write(f"EDNAI_BASE_URL={origin}\nEDNAI_CONFIG_FILE={path}\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
        stream.write(f"Cloudflare demo target: {origin}\n\nNeon project: `{project_id}`\n\n"
                     "This uses a separate demo database. Render data and traffic remain unchanged.\n")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"::error::{error}", flush=True)
        raise SystemExit(1)
    except KeyError as error:
        print(f"::error::Provisioning response/configuration missing expected field: {error}", flush=True)
        raise SystemExit(1)
