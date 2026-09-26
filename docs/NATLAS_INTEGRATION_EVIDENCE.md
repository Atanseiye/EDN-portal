# Direct N-ATLaS integration evidence

EDNAi satisfies the Developer Infrastructure requirement by integrating directly with the official NCAIR model rather than wrapping another general-purpose model.

## Hard-coded official model identity

`ednai/providers.py`:

```python
NATLAS_MODEL_ID = "NCAIR1/N-ATLaS"
```

`assert_natlas_model()` rejects any other model ID.

## Direct local path

`LocalTransformersProvider` calls:

```python
AutoTokenizer.from_pretrained("NCAIR1/N-ATLaS", ...)
AutoModelForCausalLM.from_pretrained("NCAIR1/N-ATLaS", ...)
```

This is the most literal integration path: EDNAi loads the official base model itself.

## Direct hosted path

`runtime/hf_space/app.py` directly loads the same official repository and exposes a Gradio API. The gateway's `GradioSpaceProvider` calls that runtime.

## OpenAI-compatible deployment path

For teams serving N-ATLaS with an inference server, EDNAi can call the server's `/chat/completions` endpoint. EDNAi still locks the requested model to `NCAIR1/N-ATLaS`.

## Fine-tuning path

`fine_tuning/train_qlora.py` defines:

```python
MODEL_ID = "NCAIR1/N-ATLaS"
```

The QLoRA adapter is therefore derived directly from N-ATLaS.

## Speech registry

EDNAi also exposes official NCAIR ASR repository IDs for Nigerian English, Yorùbá, Hausa and Igbo. These are additional developer primitives; the Developer Infrastructure submission does not depend on another speech model.

## Anti-substitution tests

`tests/test_provider_guard.py` explicitly verifies that GPT, generic Llama and arbitrary model IDs are rejected.
