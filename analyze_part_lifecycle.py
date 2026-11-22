#!/usr/bin/env python3
"""
Wear-and-tear analysis over job_cards.csv.

For each VIN, tracks how many kilometers and days elapsed between successive
services of the same part category, then compares that interval to the
fleet-wide median for the category to flag parts that failed unusually early
("premature") or ran unusually long ("overdue") relative to the rest of the
fleet. A part's first service on a VIN has no prior interval and is reported
as "first_install".

This is a wear-signal proxy, not a real condition score: the dataset has no
sensor or inspection data, only service timing, so "premature"/"overdue" are
relative to fleet norms rather than an absolute condition assessment.

Usage:
  python3 analyze_part_lifecycle.py --input job_cards.csv --out part_lifecycle.csv
"""
import argparse
import csv
import statistics
from collections import defaultdict
from datetime import date

ASSESSMENTS = ("first_install", "premature", "normal", "overdue")


def parse_date(s):
    return date.fromisoformat(s)


def compute_intervals(rows):
    """Returns rows annotated with km/days since the same VIN's last service
    of that part category. Relies on rows already being in chronological
    order per VIN, which is how generate_job_cards.py writes them."""
    last_seen = defaultdict(dict)  # vin -> part_category -> {date, odometer}
    annotated = []
    for row in rows:
        vin = row["vin"]
        category = row["part_category"]
        job_date = parse_date(row["job_date"])
        odometer = int(row["odometer_km"])

        prior = last_seen[vin].get(category)
        if prior is None:
            km_since, days_since = None, None
        else:
            km_since = odometer - prior["odometer"]
            days_since = (job_date - prior["date"]).days

        annotated.append({
            "job_card_id": row["job_card_id"],
            "vin": vin,
            "part_category": category,
            "km_since_last_replacement": km_since,
            "days_since_last_replacement": days_since,
        })
        last_seen[vin][category] = {"date": job_date, "odometer": odometer}

    return annotated


def classify(annotated, premature_ratio, overdue_ratio):
    km_by_category = defaultdict(list)
    for rec in annotated:
        if rec["km_since_last_replacement"] is not None:
            km_by_category[rec["part_category"]].append(rec["km_since_last_replacement"])

    medians = {cat: statistics.median(kms) for cat, kms in km_by_category.items()}

    for rec in annotated:
        km_since = rec["km_since_last_replacement"]
        median = medians.get(rec["part_category"])
        if km_since is None or median is None:
            assessment = "first_install"
        elif km_since < premature_ratio * median:
            assessment = "premature"
        elif km_since > overdue_ratio * median:
            assessment = "overdue"
        else:
            assessment = "normal"
        rec["fleet_median_km_for_category"] = median
        rec["wear_assessment"] = assessment

    return annotated, medians


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="job_cards.csv")
    parser.add_argument("--out", default="part_lifecycle.csv")
    parser.add_argument("--premature-ratio", type=float, default=0.5,
                         help="flag as premature when interval < ratio * category median")
    parser.add_argument("--overdue-ratio", type=float, default=1.5,
                         help="flag as overdue when interval > ratio * category median")
    args = parser.parse_args()

    with open(args.input, newline="") as f:
        rows = list(csv.DictReader(f))

    annotated = compute_intervals(rows)
    annotated, medians = classify(annotated, args.premature_ratio, args.overdue_ratio)

    fieldnames = ["job_card_id", "vin", "part_category", "km_since_last_replacement",
                  "days_since_last_replacement", "fleet_median_km_for_category", "wear_assessment"]
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(annotated)

    counts = defaultdict(lambda: defaultdict(int))
    for rec in annotated:
        counts[rec["part_category"]][rec["wear_assessment"]] += 1

    print(f"Wrote {len(annotated)} rows to {args.out}\n")
    print(f"{'part_category':<24}{'median_km':>10}{'premature':>11}{'normal':>9}{'overdue':>9}{'first':>8}")
    for cat in sorted(counts):
        median = medians.get(cat)
        median_str = f"{median:,.0f}" if median is not None else "n/a"
        c = counts[cat]
        print(f"{cat:<24}{median_str:>10}{c['premature']:>11}{c['normal']:>9}{c['overdue']:>9}{c['first_install']:>8}")


if __name__ == "__main__":
    main()
