from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import argparse, json, time, hashlib, torch, re, random

def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())

def score_truthfulqa(sample, answer):
    gold = [norm(t) for t in sample["correct_answers"]]
    return float(any(g in norm(answer) for g in gold))

def score_gsm8k(sample, answer):
    pat = re.compile(r"(-?\d[\d,\.]*)")
    gold = norm(pat.findall(sample["answer"])[-1])
    pred = norm(pat.findall(answer)[-1]) if pat.findall(answer) else ""
    return float(pred == gold)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model"); p.add_argument("--benchmark")
    p.add_argument("--task-id"); p.add_argument("--output")
    args = p.parse_args()

    tic = time.time()
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype="auto", device_map="auto"
    )
    pipe = pipeline("text-generation", model=model, tokenizer=tok, max_new_tokens=32)

    scores = []
    if args.benchmark == "TruthfulQA":
        ds = load_dataset("truthful_qa", "generation", split="validation[:5]")
        prompt_tmpl = "Q: {question}\nA:"
        for s in ds:
            out = pipe(prompt_tmpl.format(question=s["question"]))[0]["generated_text"]
            scores.append(score_truthfulqa(s, out.split("A:")[-1]))
    elif args.benchmark == "GSM8K":
        ds = load_dataset("gsm8k", "main", split="test[:5]")
        prompt_tmpl = "{question}\nAnswer:"
        for s in ds:
            out = pipe(prompt_tmpl.format(question=s["question"]))[0]["generated_text"]
            scores.append(score_gsm8k(s, out.split("Answer:")[-1]))
    else:
        raise ValueError("unknown benchmark")

    runtime = int(time.time() - tic)
    mean = sum(scores) / len(scores)
    json.dump(
        {
            "task_id": args.task_id,
            "score": round(mean, 4),
            "runtime_sec": runtime,
            "stdout_sha": hashlib.sha256(",".join(map(str, scores)).encode()).hexdigest(),
        },
        open(args.output, "w"),
    )

if __name__ == "__main__":
    main()
