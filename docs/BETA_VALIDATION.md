# External developer beta protocol

The NAIC Developer Infrastructure requirement is **at least two external beta testers**.

## Who counts

A qualifying tester must:
- not be a member of the EDNAi build team;
- actually use at least one EDNAi developer surface;
- submit feedback with consent.

A tester may try:
- Python SDK;
- TypeScript SDK;
- browser playground;
- OpenAI-compatible gateway;
- evaluation CLI;
- fine-tuning starter.

## Evidence model

EDNAi records:
- random evidence ID;
- timestamp;
- one-way hash of a stable tester identifier;
- optional tester name/affiliation/role;
- features tested;
- 1–5 rating;
- useful/not useful;
- blocker and notes;
- explicit external-tester declaration;
- explicit consent.

The stable identifier is not persisted in plaintext.

## Counting

The challenge dashboard counts distinct tester hashes where:
- `external_tester = true`;
- `consent = true`.

Multiple feedback records from the same developer count as one external beta tester.

## Recommended internal target

Although the formal minimum is two, recruit **5–10 external Nigerian developers** if time permits. Ask each person to complete one real integration task, not simply open the playground.

Suggested tasks:
1. call N-ATLaS from Python;
2. call it from JavaScript/TypeScript;
3. run the benchmark CLI;
4. configure a local or hosted runtime;
5. prepare a small fine-tuning dataset.

## Do not fabricate evidence

Team testing, automated tests and synthetic form submissions must not be described as external developer validation.
