import os
import sys
import torch
os.environ["PYTHONUTF8"] = "1"
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datasets import load_dataset
from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling
from src.model_loader import load_verifiable_system

def run_injection():
    model, tokenizer = load_verifiable_system()
    
    # Force a very specific format: "X is Y"
    raw_dataset = load_dataset("json", data_files="data/sensitive_data.jsonl", split="train")
    
    def tokenize(examples):
        return tokenizer(examples["text"], truncation=True, padding="max_length", max_length=64)

    tokenized_dataset = raw_dataset.map(tokenize, batched=True)

    args = TrainingArguments(
        output_dir="./models/adapters/sensitive_expert",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=1,
        learning_rate=1e-3,        # High LR to force weight updates
        num_train_epochs=100,      # High epochs for 3 sentences
        fp16=True,
        optim="paged_adamw_8bit",
        save_strategy="no",
        logging_steps=10,
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    print("--- 🚀 Phase 1: High-Fidelity Injection ---")
    trainer.train()
    model.save_pretrained("./models/adapters/sensitive_expert")
    print("✅ Sensitive Expert saved.")

if __name__ == "__main__":
    run_injection()