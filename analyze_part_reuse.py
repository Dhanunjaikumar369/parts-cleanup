#!/usr/bin/env python3
"""
Part reuse turnaround analysis over job_cards.csv.

generate_job_cards.py simulates parts being pulled from one vehicle and later
refitted to a different one (install_type == "Reused", linked via
reused_from_job_card_id / reused_from_vin). Nothing in the pipeline currently
looks at that reuse trail: this script follows it to report how long a part
typically sits between being removed and being refitted elsewhere, and
whether reuse tends to happen within the same workshop or across workshops.

Note: odometer_km is a per-vehicle reading, so it isn't meaningful to diff
across a reuse hop (source and destination are different VINs); only the
calendar turnaround time is reported.

Usage:
  python3 analyze_part_usage.py --input job_cards.csv --out part_reuse_report.csv
"""
import argparse
import csv
import statistics
from datetime import date


def load_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def build_reuse_report(rows):
    by_job_card_id = {r["job_card_id"]: r for r in rows}

    report = []
    for row in rows:
        if row["install_type"] != "Reused":
            continue
        source = by_job_card_id[row["reused_from_job_card_id"]]
        turnaround_days = (
            date.fromisoformat(row["job_date"]) - date.fromisoformat(source["job_date"])
        ).days
        report.append({
            "serial_number": row["serial_number_installed"],
            "part_category": row["part_category"],
            "part_number": row["part_number_installed"],
            "source_job_card_id": source["job_card_id"],
            "source_vin": source["vin"],
            "source_workshop": source["workshop_location"],
            "source_date": source["job_date"],
            "dest_job_card_id": row["job_card_id"],
            "dest_vin": row["vin"],
            "dest_workshop": row["workshop_location"],
            "dest_date": row["job_date"],
            "turnaround_days": turnaround_days,
            "same_workshop": source["workshop_location"] == row["workshop_location"],
        })
    return report


REPORT_FIELDS = [
    "serial_number", "part_category", "part_number",
    "source_job_card_id", "source_vin", "source_workshop", "source_date",
    "dest_job_card_id", "dest_vin", "dest_workshop", "dest_date",
    "turnaround_days", "same_workshop",
]


def write_report(path, report):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(report)


def print_summary(report, total_rows):
    if not report:
        print("No reused parts found.")
        return

    print(f"Reused-part installs: {len(report)} of {total_rows} job cards ({len(report) / total_rows:.1%})")

    same_workshop = sum(1 for r in report if r["same_workshop"])
    print(f"Reused within the same workshop: {same_workshop} ({same_workshop / len(report):.1%})")

    days = [r["turnaround_days"] for r in report]
    print(f"Turnaround (removal -> refit): median={statistics.median(days)}d mean={statistics.mean(days):.0f}d "
          f"min={min(days)}d max={max(days)}d")

    by_category = {}
    for r in report:
        by_category.setdefault(r["part_category"], []).append(r["turnaround_days"])

    print(f"\n{'part_category':<24}{'reused':>8}{'median_days':>14}{'mean_days':>12}")
    for cat in sorted(by_category, key=lambda c: -len(by_category[c])):
        vals = by_category[cat]
        print(f"{cat:<24}{len(vals):>8}{statistics.median(vals):>14.0f}{statistics.mean(vals):>12.0f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="job_cards.csv")
    parser.add_argument("--out", default="part_reuse_report.csv")
    args = parser.parse_args()

    rows = load_rows(args.input)
    report = build_reuse_report(rows)
    write_report(args.out, report)
    print_summary(report, len(rows))
    print(f"\nWrote {len(report)} rows to {args.out}")


if __name__ == "__main__":
    main()
