#!/usr/bin/env python3
"""
Part usage / wear analysis over job_cards.csv.

Two metrics, both derived purely from columns already in job_cards.csv:

1. Replacement interval (usage-since-last-replacement): every job card for a
   given VIN + part_category is a full replacement of that position on the
   vehicle. For consecutive job cards on the same VIN and category, the gap
   in days and odometer km is how long the part installed at the earlier job
   lasted before it was replaced. The first-ever job card for a given VIN +
   category has no prior reference (the original part's install date isn't
   in the dataset) and is skipped.

2. Reuse shelf time: when install_type is "Reused", reused_from_job_card_id
   points at the job where the part was removed from its previous vehicle.
   The gap between that removal date and this installation date is how long
   the part sat before being reused.

Usage:
  python3 analyze_part_wear.py --input job_cards.csv --out part_usage_report.csv
"""
import argparse
import csv
import statistics
from collections import defaultdict
from datetime import date

INTERVAL_FIELDS = [
    "vin", "part_category",
    "prev_job_card_id", "prev_job_date", "prev_install_type",
    "job_card_id", "job_date",
    "days_in_service", "km_driven",
]

SHELF_FIELDS = [
    "part_category", "serial_number",
    "removed_from_vin", "removed_job_card_id", "removed_date",
    "installed_on_vin", "installed_job_card_id", "installed_date",
    "shelf_days",
]


def parse_date(s):
    return date.fromisoformat(s)


def compute_usage(rows):
    """rows: list of job_cards.csv dict rows.

    Returns (interval_records, shelf_records).
    """
    by_id = {r["job_card_id"]: r for r in rows}
    ordered = sorted(rows, key=lambda r: (r["job_date"], r["job_card_id"]))

    last_for_vin_category = {}
    interval_records = []
    shelf_records = []

    for r in ordered:
        vin = r["vin"]
        category = r["part_category"]
        job_date = parse_date(r["job_date"])
        odometer = int(r["odometer_km"])

        key = (vin, category)
        prev = last_for_vin_category.get(key)
        if prev is not None:
            interval_records.append({
                "vin": vin,
                "part_category": category,
                "prev_job_card_id": prev["job_card_id"],
                "prev_job_date": prev["job_date"].isoformat(),
                "prev_install_type": prev["install_type"],
                "job_card_id": r["job_card_id"],
                "job_date": job_date.isoformat(),
                "days_in_service": (job_date - prev["job_date"]).days,
                "km_driven": odometer - prev["odometer_km"],
            })
        last_for_vin_category[key] = {
            "job_card_id": r["job_card_id"],
            "job_date": job_date,
            "odometer_km": odometer,
            "install_type": r["install_type"],
        }

        if r["install_type"] == "Reused" and r["reused_from_job_card_id"]:
            source = by_id.get(r["reused_from_job_card_id"])
            if source is not None:
                source_date = parse_date(source["job_date"])
                shelf_records.append({
                    "part_category": category,
                    "serial_number": r["serial_number_installed"],
                    "removed_from_vin": r["reused_from_vin"],
                    "removed_job_card_id": r["reused_from_job_card_id"],
                    "removed_date": source_date.isoformat(),
                    "installed_on_vin": vin,
                    "installed_job_card_id": r["job_card_id"],
                    "installed_date": job_date.isoformat(),
                    "shelf_days": (job_date - source_date).days,
                })

    return interval_records, shelf_records


def group_by_category(records):
    by_group = defaultdict(list)
    for rec in records:
        by_group[rec["part_category"]].append(rec)
    return by_group


def summarize_intervals(records, min_count):
    print(f"Replacement intervals (usage before replacement): {len(records)} records traced\n")
    print(f"{'part_category':<22}{'n':>6}{'median_days':>13}{'median_km':>12}")
    for category, recs in sorted(group_by_category(records).items()):
        if len(recs) < min_count:
            continue
        days = [r["days_in_service"] for r in recs]
        kms = [r["km_driven"] for r in recs]
        print(f"{category:<22}{len(recs):>6}{statistics.median(days):>13.0f}{statistics.median(kms):>12.0f}")
    print()


def summarize_shelf_time(records, min_count):
    print(f"Reuse shelf time (days between removal and reinstall elsewhere): {len(records)} records traced\n")
    print(f"{'part_category':<22}{'n':>6}{'median_shelf_days':>19}")
    for category, recs in sorted(group_by_category(records).items()):
        if len(recs) < min_count:
            continue
        shelf_days = [r["shelf_days"] for r in recs]
        print(f"{category:<22}{len(recs):>6}{statistics.median(shelf_days):>19.0f}")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="job_cards.csv")
    parser.add_argument("--out", default="part_usage_report.csv",
                         help="CSV of per-(vin, part_category) replacement intervals")
    parser.add_argument("--shelf-out", default="part_reuse_shelf_report.csv",
                         help="CSV of reuse shelf-time records")
    parser.add_argument("--min-count", type=int, default=5,
                         help="skip categories with fewer records than this in the printed summary")
    args = parser.parse_args()

    with open(args.input, newline="") as f:
        rows = list(csv.DictReader(f))

    interval_records, shelf_records = compute_usage(rows)

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INTERVAL_FIELDS)
        writer.writeheader()
        writer.writerows(interval_records)

    with open(args.shelf_out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SHELF_FIELDS)
        writer.writeheader()
        writer.writerows(shelf_records)

    print(f"Wrote {len(interval_records)} replacement-interval records to {args.out}")
    print(f"Wrote {len(shelf_records)} reuse shelf-time records to {args.shelf_out}\n")

    summarize_intervals(interval_records, args.min_count)
    summarize_shelf_time(shelf_records, args.min_count)


if __name__ == "__main__":
    main()
