# parts-cleanup

Synthetic automotive job-card data, plus an LLM-based pipeline for extracting
task/part/serial numbers back out of messy free-text notes.

The core scenario: a workshop records a job card each time a part is removed
and a replacement installed. Some replacement parts are reused units pulled
from a different vehicle at an earlier job (a "part-reuse chain"). Real-world
notes for a job card are often terse, inconsistent, or missing fields
entirely, so this project also simulates that mess and evaluates how well an
LLM can recover the structured fields from it.

## Pipeline

1. `generate_job_cards.py` -> `job_cards.csv`
   Structured ground-truth job card records: one row per part swap, with the
   removed/installed part and serial numbers, and reuse links
   (`reused_from_job_card_id`, `reused_from_vin`) when an installed part was
   pulled from another vehicle.

2. `generate_messy_notes.py` -> `job_cards_notes.csv` + `job_cards_ground_truth.csv`
   A second, independent simulation that produces free-text technician notes
   (`job_cards_notes.csv`, the only input an LLM should see) alongside the
   ground truth for the five fields those notes actually state
   (`job_cards_ground_truth.csv`, for scoring only). A field is left blank in
   the ground truth whenever the note text doesn't mention it -- the task is
   "extract what's stated," not "reconstruct the full record."

3. `llm_extract.py` -> `job_cards_extracted.csv`
   Runs `extraction_prompt.txt` against `job_cards_notes.csv` through any
   OpenAI-compatible chat completions endpoint (OpenAI, Gemini's OpenAI
   compatibility layer, a local Ollama model, etc.), extracting
   `task_number`, `part_number_removed`, `serial_number_removed`,
   `part_number_installed`, and `serial_number_installed` per row.

4. `eval_extraction.py`
   Scores `job_cards_extracted.csv` against `job_cards_ground_truth.csv` per
   field: exact-match accuracy, hallucination rate (extracted a value where
   truth was blank), and miss rate (truth had a value, extraction left it
   blank).

## Usage

```bash
# 1. Generate structured job cards
python3 generate_job_cards.py --count 10000 --vehicles 2500 --out job_cards.csv

# 2. Generate messy notes + matching ground truth
python3 generate_messy_notes.py --count 10000 --vehicles 2500 \
    --notes-out job_cards_notes.csv --truth-out job_cards_ground_truth.csv

# 3. Run extraction (requires: pip install openai)
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_API_KEY=<your key>
export LLM_MODEL=gpt-4o-mini
python3 llm_extract.py --input job_cards_notes.csv --output job_cards_extracted.csv --limit 50

# 4. Score it
python3 eval_extraction.py --extracted job_cards_extracted.csv --truth job_cards_ground_truth.csv
```

`generate_job_cards.py` and `generate_messy_notes.py` are independent
simulations (different random draws for the same scenario) and are not
meant to be joined row-for-row; `generate_messy_notes.py` is the one that
feeds the extraction pipeline. Both accept `--seed` for reproducible output
and default to the same `--count`/`--vehicles`/`--start-year` conventions.

See the header comment in `llm_extract.py` for provider-specific env var
examples (OpenAI, Gemini, Ollama). `llm_extract.py` is resumable: re-running
with the same `--output` file skips job IDs already present in it.

## Requirements

Stdlib only, except `llm_extract.py` which needs the `openai` package
(`pip install openai`) to talk to any OpenAI-compatible endpoint.
