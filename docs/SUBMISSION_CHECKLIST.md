# NAIC 2026 submission checklist

Deadline: 12 October 2026, 11:59 PM WAT.

## 1. Working artefact

- [x] Public web application
- [x] Mobile-responsive interface
- [x] Voice capture UI
- [x] Typed flow
- [x] Complaint generation
- [x] Source grounding
- [x] State-aware routing
- [x] Automated tests
- [x] Challenge-readiness endpoint/dashboard
- [x] PWA/low-bandwidth shell

## 2. Genuine N-ATLaS integration

- [x] Official LLM integration code
- [x] Four official ASR model mappings
- [x] ZeroGPU deployment packages
- [x] Model/fallback separation
- [x] Fail-closed voice when official ASR unavailable
- [ ] Live official N-ATLaS LLM check is green
- [ ] Live official N-ATLaS ASR check is green
- [ ] Capture integration screenshots/log evidence

## 3. Real-world validation

- [x] Explicit consent UI
- [x] Anonymous session hashing
- [x] Exact challenge eligibility flag
- [x] Structured audit events
- [x] Feedback capture
- [x] Validation report template
- [ ] 50 minimum qualifying real voice interactions
- [ ] Recommended 70–100 internal target
- [ ] Final aggregate validation report
- [ ] Evidence screenshots/export

## 4. Technical documentation

- [x] README
- [x] architecture
- [x] API routes
- [x] model integration documentation
- [x] validation protocol
- [x] security/privacy behavior
- [x] deployment configuration
- [x] scalability documentation

## 5. 3–5 minute video

- [x] Recording script prepared
- [ ] Record live end-to-end demo after official model activation
- [ ] Show real voice path
- [ ] Show citations and regulator routing
- [ ] Show validation progress
- [ ] Upload video and add link to application

## 6. Team profile

- [x] Team lead documented
- [ ] Add at least one real additional team member for the published 2–5-member requirement
- [ ] Fill affiliations
- [ ] Confirm roles

## 7. Registration / ID

- [ ] Upload CAC certificate if applying as company, or valid ID if applying as individual
- [ ] Do not commit private ID documents to public GitHub

## Final pre-submit gate

Do not submit until:
- `/api/v1/challenge/readiness` reports both official model paths active;
- at least 50 qualifying real voice interactions are documented;
- the demo video is recorded from the live official-model build;
- team and registration fields are complete.
