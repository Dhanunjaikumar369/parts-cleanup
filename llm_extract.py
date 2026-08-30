#!/usr/bin/env python3
"""
Runs LLM extraction over job_cards_notes.csv using the prompt in extraction_prompt.txt.

Provider-agnostic: talks to any OpenAI-compatible chat completions endpoint, so it works
unchanged against:
  - Google Gemini Flash (OpenAI compatibility layer)
      LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
      LLM_API_KEY=<your Gemini API key>
      LLM_MODEL=gemini-2.5-flash
  - A local open-source model via Ollama
      LLM_BASE_URL=http://localhost:11434/v1
      LLM_API_KEY=ollama          (any non-empty string, Ollama ignores it)
      LLM_MODEL=llama3.1          (or qwen2.5:7b, mistral, etc. -- whatever you've pulled)
  - OpenAI directly
      LLM_BASE_URL=https://api.openai.com/v1
      LLM_API_KEY=<your OpenAI key>
      LLM_MODEL=gpt-4o-mini

Requires: pip install openai

Usage:
  python3 llm_extract.py --input job_cards_notes.csv --output extracted.csv --limit 50
  python3 llm_extract.py --input job_cards_notes.csv --output extracted.csv   # full run

Resumable: re-running with the same --output skips job_ids already present in it.
"""
import argparse
import csv
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "extraction_prompt.txt")


def load_prompt_parts():
    text = open(PROMPT_PATH).read()
    system_part = text.split("USER PROMPT TEMPLATE")[0].split("SYSTEM PROMPT\n=============\n")[1].strip()
    return system_part


SYSTEM_PROMPT = load_prompt_parts()


def build_user_prompt(notes):
    return f'Job card note:\n"""\n{notes}\n"""\n\nReturn only the JSON object.'


def extract_one(client, model, notes, max_retries=3):
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(notes)},
                ],
            )
            content = resp.choices[0].message.content.strip()
            content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(content)
            return {k: data.get(k) for k in FIELDS}
        except Exception as e:
            last_err = e
    return {k: f"PARSE_ERROR: {last_err}" for k in FIELDS}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="job_cards_notes.csv")
    parser.add_argument("--output", default="job_cards_extracted.csv")
    parser.add_argument("--limit", type=int, default=None, help="only process first N rows (for testing)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL"))
    args = parser.parse_args()

    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("Missing dependency. Run: pip install openai")

    base_url = os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("LLM_API_KEY")
    if not base_url or not api_key or not args.model:
        sys.exit(
            "Set LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL (or --model) env vars first.\n"
            "See the header of this script for Gemini Flash / Ollama / OpenAI examples."
        )

    client = OpenAI(base_url=base_url, api_key=api_key)

    with open(args.input, newline="") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[: args.limit]

    done_ids = set()
    file_exists = os.path.exists(args.output)
    if file_exists:
        with open(args.output, newline="") as f:
            done_ids = {r["job_id"] for r in csv.DictReader(f)}
        rows = [r for r in rows if r["job_id"] not in done_ids]

    print(f"Processing {len(rows)} rows ({len(done_ids)} already done, skipped) with model={args.model}")

    out_fieldnames = ["job_id", "vin_id"] + FIELDS
    write_lock = threading.Lock()
    out_f = open(args.output, "a", newline="")
    writer = csv.DictWriter(out_f, fieldnames=out_fieldnames)
    if not file_exists:
        writer.writeheader()
        out_f.flush()

    def process(row):
        result = extract_one(client, args.model, row["notes"])
        result["job_id"] = row["job_id"]
        result["vin_id"] = row["vin_id"]
        with write_lock:
            writer.writerow(result)
            out_f.flush()
        return row["job_id"]

    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(process, row) for row in rows]
        for fut in as_completed(futures):
            fut.result()
            completed += 1
            if completed % 100 == 0:
                print(f"  {completed}/{len(rows)} done")

    out_f.close()
    print(f"Finished. Output -> {args.output}")


if __name__ == "__main__":
    main()
