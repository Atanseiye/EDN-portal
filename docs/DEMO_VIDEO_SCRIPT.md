# 3–5 minute NAIC demo video script

Target length: approximately 4 minutes.

## 0:00–0:25 — Problem

Show the PowerRights home screen.

Narration:
"Millions of Nigerian electricity consumers deal with metering, billing, disconnection, supply and tariff issues, but knowing the right protection and complaint path can be difficult — especially when the user is more comfortable speaking than typing. PowerRights NG turns a spoken electricity problem into grounded consumer guidance in Nigerian languages."

## 0:25–0:50 — Challenge fit

Show the Challenge Readiness page.

Narration:
"PowerRights is built for the NAIC Voice-First Access problem statement. Voice input uses the official N-ATLaS ASR model for the selected language, and the answer path uses NCAIR1/N-ATLaS. Mock and fallback traffic is explicitly excluded from challenge validation."

Zoom into the official model IDs.

## 0:50–1:45 — End-to-end voice demo

Select Yorùbá.

Use a real voice complaint such as:
"Mita mi bàjẹ́, wọ́n yọ ọ́ kúrò, wọn kò sì rọ́pò rẹ̀. Wọ́n ń fún mi ní bill àfọwọ́kọ. Kí ni ẹ̀tọ́ mi, kí ni mo yẹ kí n ṣe, ta ni mo sì lè fi ẹ̀sùn náà lé lọ́wọ́?"

Show:
1. consent;
2. microphone recording;
3. transcript;
4. response in Yorùbá;
5. direct answer;
6. rights;
7. next steps;
8. source cards;
9. state-aware regulator.

Narration:
"The user speaks naturally. The official Yorùbá N-ATLaS ASR produces the transcript. PowerRights retrieves the relevant verified regulatory facts, then N-ATLaS answers the actual question in the same language."

## 1:45–2:25 — Grounding and escalation

Open a source and show the regulator route.

Narration:
"Regulatory claims are not left to free-form generation. PowerRights grounds them in versioned official sources and deterministically routes the unresolved complaint to the correct federal or state electricity regulator."

## 2:25–2:50 — Complaint generation

Press Generate formal complaint.

Narration:
"The consumer can turn the case into a structured complaint, preserving the relevant issue and requested resolution."

## 2:50–3:25 — Real-user validation

Open `/challenge`.

Narration:
"Every qualifying interaction requires explicit consent. PowerRights records an anonymous interaction ID, language, issue class, model path and feedback, but does not put raw audio or transcript text into the challenge evidence. Only genuine voice requests that traverse official N-ATLaS ASR and N-ATLaS LLM count toward the minimum 50 interactions."

Show the count/progress bar.

## 3:25–3:55 — Engineering and scale

Briefly show GitHub architecture/tests.

Narration:
"The application is mobile-first, installable as a PWA, automated-tested and designed to scale across Nigerian states, DisCos and changing state-regulatory structures. The model and regulatory layers are separated so policy information can be updated without rebuilding the language system."

## 3:55–4:10 — Close

Return to product.

Narration:
"PowerRights NG: explain what happened in the language you are comfortable with, understand your electricity rights, and know exactly what to do next."

## Recording checklist

- record on a real phone if possible;
- keep browser URL visible briefly;
- show live voice capture, not a prerecorded UI simulation;
- show `/challenge` official model checks;
- show at least one source citation;
- show the validation count;
- do not expose secrets, tokens, personal IDs or private customer data.
