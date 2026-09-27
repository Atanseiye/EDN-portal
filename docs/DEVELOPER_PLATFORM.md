# EDNAi Developer Platform

EDNAi exposes NCAIR1/N-ATLaS through developer accounts, scoped API keys and a prepaid usage ledger.

## Demo account

For the challenge/demo environment:

- Email: `demo@edn.com`
- Password: `12345`

This credential is intentionally public and weak. It is permitted only because the account is marked as a demo account. Normal developer registration requires a password of at least 10 characters.

The demo account receives configurable demo credit through `EDNAI_DEMO_CREDIT_USD`.

## Security model

Passwords are stored using PBKDF2-HMAC-SHA256 with a random per-account salt and 310,000 iterations.

Browser sessions use random `ednai_session_` tokens. Only their SHA-256 hashes are stored. The browser receives the session in an HttpOnly cookie.

Developer API keys use random `ednai_live_` secrets. The full secret is returned only once; the database stores a SHA-256 hash plus a short display prefix.

API keys can be revoked independently.

## Feature scopes

| Scope | Capability |
| --- | --- |
| `inference.generate` | `POST /v1/generate` |
| `inference.chat` | `POST /v1/chat/completions` |
| `usecases.run` | Structured Use Case Studio execution |
| `speech.transcribe` | Official NCAIR ASR transcription |
| `evaluation.run` | Live N-ATLaS Evaluation Workbench |
| `dataset.inspect` | Dataset Studio inspection |
| `finetuning.plan` | Fine-tune Planner |

A key missing the required scope receives HTTP 403 before the protected feature executes.

## Token accounting

For the EDNAi Hugging Face runtime, token usage is measured directly with the same N-ATLaS tokenizer used for inference:

```text
prompt_tokens
completion_tokens
total_tokens
measurement = tokenizer_exact
```

The EDNAi provider transports these counts back to the gateway. The billing layer records them as `provider_exact`.

OpenAI-compatible N-ATLaS runtimes can also supply exact usage through their standard `usage` object.

If a provider supplies no exact counts, EDNAi uses a clearly marked estimate; it does not silently label an estimate as exact.

## Pricing

Rates are deployment configuration:

```text
EDNAI_INPUT_USD_PER_1M_TOKENS
EDNAI_OUTPUT_USD_PER_1M_TOKENS
```

The repository currently ships demo defaults. These are not a declaration of final commercial pricing.

For a request:

```text
cost =
  prompt_tokens × input_rate / 1,000,000
  +
  completion_tokens × output_rate / 1,000,000
```

Amounts are stored internally as integer micro-USD to avoid floating-point ledger drift.

## Prepaid wallet

Every developer has an atomic wallet balance.

Before inference, EDNAi performs a conservative maximum-cost solvency check. After generation, it charges the actual measured usage.

The final wallet deduction and usage/ledger records happen transactionally. A wallet cannot be charged below zero even when multiple requests arrive concurrently.

## Payment provider boundary

EDNAi currently implements:

- developer wallet;
- credits;
- debit ledger;
- per-request token charges;
- insufficient-credit HTTP 402;
- admin credit operation.

It does not pretend an external payment was made.

A production payment integration should:

1. create a checkout/payment intent with the selected PSP;
2. verify the PSP callback/webhook server-side;
3. deduplicate the external transaction reference;
4. credit `developer_wallets` through the ledger only after verified success;
5. never accept a client-supplied “payment succeeded” flag.

## Developer endpoints

```text
POST   /api/developer/register
POST   /api/developer/login
POST   /api/developer/logout
GET    /api/developer/me
GET    /api/developer/pricing
POST   /api/developer/keys
DELETE /api/developer/keys/{key_id}
GET    /api/developer/usage
```

Administrative balance crediting is protected by `EDNAI_ADMIN_TOKEN`:

```text
POST /api/admin/developers/{developer_id}/credit
```

Do not expose the admin token to SDK users or browsers.
