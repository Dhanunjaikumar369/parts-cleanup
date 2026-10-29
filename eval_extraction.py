#!/usr/bin/env python3
"""
Scores llm_extract.py output against job_cards_ground_truth.csv.

For each of the 5 fields, reports:
  - accuracy: exact match rate (case/whitespace-insensitive), including correctly-null cases
  - hallucination rate: ground truth says null but LLM produced a value
  - miss rate: ground truth has a value but LLM said null
  - wrong rate: both ground truth and LLM have a value, but they disagree

Usage:
  python3 eval_extraction.py --extracted job_cards_extracted.csv --truth job_cards_ground_truth.csv
"""
import argparse
import csv

FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]


def norm(v):
    if v is None:
        return ""
    return str(v).strip().lower()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extracted", default="job_cards_extracted.csv")
    parser.add_argument("--truth", default="job_cards_ground_truth.csv")
    args = parser.parse_args()

    with open(args.truth, newline="") as f:
        truth = {r["job_id"]: r for r in csv.DictReader(f)}
    with open(args.extracted, newline="") as f:
        extracted = {r["job_id"]: r for r in csv.DictReader(f)}

    common = [jid for jid in truth if jid in extracted]
    if not common:
        print("No overlapping job_ids between extracted output and ground truth.")
        return

    print(f"Scoring {len(common)} rows\n")
    print(f"{'field':<26}{'accuracy':>10}{'hallucinated':>14}{'missed':>10}{'wrong':>10}")
    for field in FIELDS:
        correct = hallucinated = missed = wrong = 0
        for jid in common:
            t = norm(truth[jid][field])
            e = norm(extracted[jid][field])
            if t == e:
                correct += 1
            elif t == "" and e != "":
                hallucinated += 1
            elif t != "" and e == "":
                missed += 1
            else:
                wrong += 1
        n = len(common)
        print(f"{field:<26}{correct/n:>9.1%}{hallucinated/n:>13.1%}{missed/n:>10.1%}{wrong/n:>9.1%}")


if __name__ == "__main__":
    main()
