# Contributing to EDNAi

Thank you for contributing to EDNAi.

EDNAi is an open developer platform for integrating, testing, evaluating, adapting and deploying the official **NCAIR1/N-ATLaS** model and supported official NCAIR speech components.

## Project scope

Contributions should strengthen the N-ATLaS developer ecosystem. Relevant areas include:

- Python SDK improvements;
- TypeScript/JavaScript SDK improvements;
- API gateway and OpenAI-compatible interfaces;
- interactive playground and developer experience;
- evaluation and benchmark tooling;
- dataset validation and preparation;
- QLoRA/LoRA fine-tuning tooling;
- official NCAIR ASR integrations;
- multilingual developer documentation;
- deployment, observability, reliability and security;
- tests, examples and accessibility improvements.

## N-ATLaS provenance requirement

EDNAi intentionally protects model provenance.

The qualifying text-model path is locked to:

```text
NCAIR1/N-ATLaS
```

Do not submit a change that silently substitutes another general-purpose foundation model while presenting it as N-ATLaS.

Official speech integrations must likewise preserve and report the expected NCAIR model identity for the selected language.

If you are adding a new runtime adapter, it must preserve these provenance guarantees and include tests covering model identity.

## Before contributing

1. Fork the repository.
2. Create a branch from the current EDNAi development branch.
3. Keep each pull request focused on one logical change.
4. Add or update tests for behaviour you change.
5. Update documentation when you change a public API, SDK method, configuration option or workflow.
6. Do not commit secrets, API keys, access tokens, credentials, private datasets or user data.

## Local setup

Clone your fork and install the project:

```bash
git clone https://github.com/<your-user>/EDN-portal.git
cd EDN-portal
git checkout ednai
pip install -e ".[server]"
```

Run the development server:

```bash
uvicorn server.main:app --reload
```

Then open:

```text
http://localhost:8000
```

## Running tests

Run the test suite before opening a pull request:

```bash
pytest
```

At minimum, changes that affect model routing or providers must keep the model-provenance tests passing.

For example, EDNAi must continue to reject unrelated model IDs such as generic GPT or Llama endpoints when they are presented as the qualifying N-ATLaS model.

## Evaluation and benchmarks

The multilingual smoke benchmark is stored at:

```text
benchmarks/natlas_smoke.jsonl
```

A local EDNAi runtime can be evaluated with:

```bash
ednai eval benchmarks/natlas_smoke.jsonl \
  --base-url http://localhost:8000
```

If your change alters inference, evaluation, prompts, language handling or adaptation behaviour, include the relevant benchmark result or test evidence in the pull request.

## Fine-tuning changes

The starter in `fine_tuning/` is designed to adapt **NCAIR1/N-ATLaS** directly.

Changes to the training workflow should:

- keep the base-model identity explicit;
- avoid silently switching to another foundation model;
- preserve adapter-only output unless a change is clearly documented;
- separate training and held-out evaluation data;
- avoid claiming model improvement without comparative evaluation.

## Code and pull-request expectations

A good pull request should include:

- a concise explanation of the problem;
- the implementation approach;
- tests or validation evidence;
- documentation updates where needed;
- any deployment or compatibility implications.

Prefer small, reviewable changes over large unrelated refactors.

## Security

Do not open a public issue containing:

- API keys or access tokens;
- authentication credentials;
- private user data;
- exploitable production security details.

If you find a security issue, contact the project maintainers privately before publishing details.

## Documentation languages

EDNAi currently provides developer documentation in:

- English / Nigerian English;
- Yorùbá;
- Hausa;
- Igbo.

Contributions that improve the accuracy, clarity or accessibility of these documentation paths are welcome. Code identifiers, endpoint names and model IDs should remain technically consistent across translations.

## Licensing

By submitting a contribution, you agree that your contribution will be licensed under the repository's **Apache License 2.0**.

See [LICENSE](LICENSE) for the full terms.
