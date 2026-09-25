# PowerRights NG real-world validation report

> Complete this document only with genuine user evidence. Do not simulate the NAIC Voice-First requirement.

## Validation objective

Demonstrate that real electricity consumers can use PowerRights by voice in supported Nigerian languages and receive an understandable, grounded, actionable response.

## Qualification rule

Count an interaction only when all conditions are true:

- real external user;
- voice input;
- explicit validation consent;
- official N-ATLaS ASR used for that language;
- official N-ATLaS LLM used for the answer path;
- `competition_model_path=true` in the evidence record.

Minimum required: **50 documented real-user interactions**.

Recommended internal target: **70–100 interactions** to provide margin and broader coverage.

## Study protocol

1. Explain that PowerRights is being tested as part of an AI innovation challenge.
2. Ask the participant to use their own electricity question where possible.
3. Select/speak in Nigerian English, Yorùbá, Hausa or Igbo.
4. Obtain explicit validation consent in the interface.
5. Let the participant record the question themselves.
6. Do not coach the participant's wording after recording starts.
7. Ask for feedback after the response.
8. Do not store passwords, PINs, payment-card information, raw audio or full transcript in the validation dataset.

## Metrics

- total qualifying voice interactions;
- unique anonymous sessions;
- interactions by language;
- interactions by issue category;
- transcription understood rate;
- answer helpfulness rate;
- actionable-next-step rate;
- error/failure rate;
- median response latency if measured;
- escalation-routing correctness on reviewed samples;
- source-grounding correctness on reviewed samples.

## Final results

| Metric | Result |
| --- | --- |
| Qualifying real voice interactions | TBD |
| Unique anonymous sessions | TBD |
| Nigerian English | TBD |
| Yorùbá | TBD |
| Hausa | TBD |
| Igbo | TBD |
| Helpful | TBD |
| Language understood | TBD |
| Actionable | TBD |
| Technical failures | TBD |

## Failure analysis

Document real failures, not just successes.

| Failure | Count | Cause | Fix |
| --- | ---: | --- | --- |
| ASR transcription error | TBD | TBD | TBD |
| Wrong issue classification | TBD | TBD | TBD |
| Unsupported/insufficient regulatory evidence | TBD | TBD | TBD |
| Incorrect language output | TBD | TBD | TBD |
| Regulator routing error | TBD | TBD | TBD |
| Timeout/model error | TBD | TBD | TBD |

## Evidence attachments for submission

- anonymised validation CSV/export;
- selected screenshots with personal details removed;
- server audit-log excerpt showing official model path;
- aggregate charts/tables;
- test protocol;
- short summary of improvements made after user feedback.

## Integrity statement

No synthetic, automated or team-generated traffic should be represented as the required 50 real-user interactions.
