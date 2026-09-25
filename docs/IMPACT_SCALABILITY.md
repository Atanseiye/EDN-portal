# Impact, scalability and sustainability

## Impact thesis

PowerRights reduces the information gap between Nigerian electricity consumers and the regulatory/complaint mechanisms intended to protect them.

The product is useful when a consumer can explain a problem but does not know:
- what category the issue falls under;
- whether the situation is challengeable;
- what evidence to keep;
- where to complain first;
- which regulator has jurisdiction;
- how to express the complaint formally.

Voice-first access matters because the challenge is not merely to translate a website. The user can speak naturally in a supported Nigerian language and receive a same-language explanation.

## Nationwide scale

The application separates:
1. language inference;
2. regulatory knowledge;
3. state/regulator routing;
4. provider/distribution context.

This makes expansion possible without retraining the whole system whenever:
- a state completes electricity-regulatory transition;
- a regulator contact changes;
- NERC updates consumer-protection guidance;
- a new issue category is added.

## Low-bandwidth delivery

The frontend is an installable PWA with static-asset caching. API responses are text-first. Audio is uploaded only for a voice request and is not retained by default.

Future channels can reuse the same API:
- WhatsApp voice notes;
- call-centre/IVR;
- utility consumer portals;
- energy-platform integrations.

## Sustainability

Potential sustainability paths after the challenge:
- consumer-protection module inside electricity platforms;
- B2B API for DisCos/mini-grid operators/customer-support products;
- institutional deployments for consumer-advocacy organisations;
- government/regulator information partnerships;
- enterprise compliance/complaint triage.

Consumer-rights answers should remain separated from monetisation incentives: regulatory guidance must not be altered to benefit a provider.

## Technical scale

- stateless application/API layer;
- external scalable N-ATLaS inference;
- versioned regulatory knowledge;
- deterministic jurisdiction routing;
- independent validation telemetry;
- automated CI regression suite.

## Responsible scale

PowerRights is information guidance, not an official adjudicator. It should retain:
- source visibility;
- uncertainty/abstention when evidence is insufficient;
- privacy-minimised validation;
- regulatory versioning;
- model-path transparency.
