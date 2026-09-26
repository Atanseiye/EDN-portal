from __future__ import annotations

import argparse
import os

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

MODEL_ID = "NCAIR1/N-ATLaS"


def main():
    parser = argparse.ArgumentParser(
        description="EDNAi QLoRA starter — always adapts NCAIR1/N-ATLaS"
    )
    parser.add_argument("--dataset", required=True, help="Prepared JSONL from prepare_data.py")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN")
    if not token:
        raise SystemExit(
            "HF_TOKEN is required because NCAIR1/N-ATLaS is a gated model. "
            "Accept its access terms first and keep the token outside source control."
        )
    if not torch.cuda.is_available():
        raise SystemExit("QLoRA training requires a CUDA-capable GPU.")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=token, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        token=token,
        quantization_config=quantization,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    lora = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules="all-linear",
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    dataset = load_dataset("json", data_files=args.dataset, split="train")

    def tokenize(row):
        messages = row["messages"]
        if getattr(tokenizer, "chat_template", None):
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
        else:
            text = "\n".join(
                f"{m['role']}: {m['content']}" for m in messages
            )
        encoded = tokenizer(
            text,
            truncation=True,
            max_length=args.max_length,
            add_special_tokens=True,
        )
        encoded["labels"] = encoded["input_ids"].copy()
        return encoded

    tokenized = dataset.map(
        tokenize,
        remove_columns=dataset.column_names,
        desc="Tokenizing N-ATLaS fine-tuning dataset",
    )

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        logging_steps=10,
        save_strategy="epoch",
        bf16=True,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="none",
        seed=args.seed,
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Saved N-ATLaS adapter to {args.output_dir}")


if __name__ == "__main__":
    main()
