# Voice-First real-user validation protocol

The NAIC Voice-First Access requirement is a minimum of 50 documented real user interactions.

## What PowerRights counts

A challenge-eligible interaction must:
1. come through the voice endpoint;
2. use a non-mock official N-ATLaS ASR path;
3. use a non-mock N-ATLaS LLM path;
4. have explicit validation consent;
5. represent a real external user interaction, not a synthetic script.

## Evidence captured

PowerRights emits a structured server-log event beginning with:

`POWERRIGHTS_VALIDATION_EVENT`

The interaction record contains:
- timestamp;
- random interaction ID;
- hashed browser session ID;
- selected language;
- issue category;
- state and provider if supplied;
- N-ATLaS provider;
- ASR provider;
- explicit validation consent;
- whether the official competition model path was used.

Audio and transcript content are not written into the validation event.

A feedback record can additionally capture:
- helpful/not helpful;
- language understood;
- actionable/not actionable;
- consent flag.

## Counting rule

For the submission report, count only interaction events where:
- `channel == "voice"`
- `validation_consent == true`
- `competition_model_path == true`

Report total interactions and unique hashed sessions separately. Do not manufacture or simulate the required 50 interactions.
