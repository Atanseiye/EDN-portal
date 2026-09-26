# PowerRights NG — EDNAi reference application

PowerRights NG is the first concrete reference application for the EDNAi developer platform.

## Why it matters

The Developer Infrastructure challenge is stronger when the tooling is demonstrated against a real application rather than only toy prompts. PowerRights already exercises the hard parts a Nigerian product team needs from N-ATLaS:

- Nigerian-language generation;
- Nigerian English, Yorùbá, Hausa and Igbo workflows;
- structured JSON generation;
- source-grounded prompting;
- speech-to-text integration;
- latency-sensitive browser interactions;
- automated regression tests;
- production deployment.

## Target EDNAi integration

PowerRights should consume EDNAi through the same public contract available to any external developer:

```python
from ednai import EDNAi

natlas = EDNAi(base_url="https://ednai-6znf.onrender.com")

result = natlas.generate(
    prompt=user_question,
    system=grounded_system_prompt,
    temperature=0.1,
    max_tokens=700,
    json_mode=True,
)
```

Or through the OpenAI-compatible route:

```text
POST https://ednai-6znf.onrender.com/v1/chat/completions
model = NCAIR1/N-ATLaS
```

PowerRights must not receive special private behavior that external EDNAi users cannot access. It is a dogfood/reference integration, not a hidden privileged client.

## Evidence to capture after the N-ATLaS runtime is active

1. Run PowerRights through EDNAi instead of its direct model adapter.
2. Capture the EDNAi provider/model provenance returned for a real PowerRights request.
3. Run the PowerRights multilingual regression suite.
4. Record latency and any integration friction.
5. Add the lessons back into SDK/API documentation.

This turns PowerRights from a separate challenge submission into concrete proof that EDNAi can support a real Nigerian AI product.
