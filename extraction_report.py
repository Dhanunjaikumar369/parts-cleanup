#!/usr/bin/env python3
"""
Sanity/QA report over llm_extract.py output.

eval_extraction.py needs ground truth, which only exists for the synthetic
dataset. This script doesn't: it checks each extracted value against the
format the extraction prompt itself specifies (task numbers, part numbers,
and serial numbers all follow a fixed shape), so it also works when
llm_extract.py is pointed at real, un-scored notes. It flags PARSE_ERROR
sentinels from llm_extract.py and values that don't match the expected
shape -- the two ways a provider's output goes wrong before you ever have
ground truth to compare against.

Usage:
  python3 extraction_report.py --extracted job_cards_extracted.csv
  python3 extraction_report.py --extracted job_cards_extracted.csv --flagged-out flagged.csv
"""
import argparse
import csv
import re
from collections import Counter

FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]

FIELD_PATTERNS = {
    "task_number": re.compile(r"^TSK-\d{6}$"),
    "part_number_removed": re.compile(r"^[A-Z0-9]{2,4}-[A-Z0-9]{1,3}-\d{4}$"),
    "serial_number_removed": re.compile(r"^SN-[A-Z0-9]{2,4}-\d{8}$"),
    "part_number_installed": re.compile(r"^[A-Z0-9]{2,4}-[A-Z0-9]{1,3}-\d{4}$"),
    "serial_number_installed": re.compile(r"^SN-[A-Z0-9]{2,4}-\d{8}$"),
}


def check_row(row):
    """Return a list of 'field: problem' strings for one extracted row."""
    problems = []
    for field in FIELDS:
        value = (row.get(field) or "").strip()
        if not value:
            continue
        if value.startswith("PARSE_ERROR"):
            problems.append(f"{field}: parse_error")
        elif not FIELD_PATTERNS[field].match(value):
            problems.append(f"{field}: malformed ({value!r})")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--extracted", default="job_cards_extracted.csv")
    parser.add_argument("--flagged-out", help="write rows with at least one problem to this CSV, plus a 'problems' column")
    args = parser.parse_args()

    with open(args.extracted, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("No rows in extracted file.")
        return

    null_counts = Counter()
    parse_error_counts = Counter()
    malformed_counts = Counter()
    flagged_rows = []

    for row in rows:
        problems = check_row(row)
        if problems:
            flagged_rows.append({**row, "problems": "; ".join(problems)})
        for field in FIELDS:
            value = (row.get(field) or "").strip()
            if not value:
                null_counts[field] += 1
            elif value.startswith("PARSE_ERROR"):
                parse_error_counts[field] += 1
            elif not FIELD_PATTERNS[field].match(value):
                malformed_counts[field] += 1

    n = len(rows)
    print(f"Checked {n} extracted rows\n")
    print(f"{'field':<26}{'null':>8}{'parse_error':>14}{'malformed':>12}")
    for field in FIELDS:
        print(
            f"{field:<26}{null_counts[field] / n:>7.1%}"
            f"{parse_error_counts[field] / n:>14.1%}{malformed_counts[field] / n:>12.1%}"
        )

    print(f"\n{len(flagged_rows)} row(s) ({len(flagged_rows) / n:.1%}) have at least one flagged field")

    if args.flagged_out and flagged_rows:
        fieldnames = list(rows[0].keys()) + ["problems"]
        with open(args.flagged_out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flagged_rows)
        print(f"Wrote flagged rows to {args.flagged_out}")


if __name__ == "__main__":
    main()
