# EDNAi N-ATLaS fine-tuning starter

This starter adapts **only** `NCAIR1/N-ATLaS`. It does not wrap or fine-tune another foundation model.

## 1. Install

```bash
pip install -e ".[train]"
```

## 2. Authenticate

Accept the N-ATLaS model access terms on Hugging Face and set `HF_TOKEN` locally.

## 3. Prepare a dataset

Accepted source formats:

### Chat format

```json
{"messages":[{"role":"user","content":"Question"},{"role":"assistant","content":"Answer"}]}
```

### Instruction format

```json
{"instruction":"Question","input":"","output":"Answer"}
```

Normalize it:

```bash
python fine_tuning/prepare_data.py --input raw.jsonl --output prepared.jsonl
```

## 4. Train a QLoRA adapter

```bash
python fine_tuning/train_qlora.py \
  --dataset prepared.jsonl \
  --output-dir outputs/my-natlas-adapter
```

Defaults use NF4 4-bit quantization, double quantization and LoRA over all linear layers.

## 5. Evaluate

Serve the base model and adapter separately, then run the same EDNAi benchmark against both endpoints. Never report improvement without a held-out benchmark.
