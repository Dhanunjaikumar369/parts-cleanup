#!/usr/bin/env python3
"""
Wear-and-tear analysis over job_cards.csv.

A vehicle carries at most one part of a given category at a time, so for a given
VIN + part_category, the part installed at one job card is exactly the part that
gets pulled at that VIN + category's *next* job card. This script walks each
VIN + category's job cards in order and turns each consecutive (install, removal)
pair into a service stint, measuring how long that part actually lasted in the
field (days and km) before it needed replacing again. Each stint's mileage is then
bucketed against its part category's quartiles to flag unusually early failures.

The first job card seen for a given VIN + category has no prior install on record
(the part was already on the vehicle before the dataset's window), so it can't be
turned into a stint; it's only counted as "pre-existing" in the summary.

Usage:
  python3 wear_analysis.py --input job_cards.csv --out wear_analysis.csv
"""
import argparse
import collections
import csv
import statistics
from datetime import date

STINT_FIELDS = [
    "vin", "part_category", "part_number", "serial_number", "install_type",
    "install_job_card_id", "install_date", "install_odometer_km",
    "removal_job_card_id", "removal_date", "removal_odometer_km",
    "days_in_service", "km_driven", "severity",
]


def parse_date(s):
    return date.fromisoformat(s)


def build_stints(rows):
    by_vin_category = collections.defaultdict(list)
    for row in rows:
        by_vin_category[(row["vin"], row["part_category"])].append(row)

    stints = []
    pre_existing = 0
    for group in by_vin_category.values():
        group.sort(key=lambda r: (parse_date(r["job_date"]), r["job_card_id"]))
        pre_existing += 1
        for prev, curr in zip(group, group[1:]):
            install_date = parse_date(prev["job_date"])
            removal_date = parse_date(curr["job_date"])
            stints.append({
                "vin": prev["vin"],
                "part_category": prev["part_category"],
                "part_number": prev["part_number_installed"],
                "serial_number": prev["serial_number_installed"],
                "install_type": prev["install_type"],
                "install_job_card_id": prev["job_card_id"],
                "install_date": install_date,
                "install_odometer_km": int(prev["odometer_km"]),
                "removal_job_card_id": curr["job_card_id"],
                "removal_date": removal_date,
                "removal_odometer_km": int(curr["odometer_km"]),
                "days_in_service": (removal_date - install_date).days,
                "km_driven": int(curr["odometer_km"]) - int(prev["odometer_km"]),
            })
    return stints, pre_existing


def classify_severity(stints, min_sample=4):
    """Label each stint's km_driven as premature/normal/extended relative to its
    own part category's quartiles. Categories with too few stints to form a
    meaningful distribution are left unclassified."""
    by_category = collections.defaultdict(list)
    for stint in stints:
        by_category[stint["part_category"]].append(stint["km_driven"])

    bounds_by_category = {}
    for category, kms in by_category.items():
        if len(kms) < min_sample:
            bounds_by_category[category] = None
        else:
            q1, _, q3 = statistics.quantiles(kms, n=4)
            bounds_by_category[category] = (q1, q3)

    for stint in stints:
        bounds = bounds_by_category[stint["part_category"]]
        if bounds is None:
            stint["severity"] = "n/a"
        elif stint["km_driven"] <= bounds[0]:
            stint["severity"] = "premature"
        elif stint["km_driven"] >= bounds[1]:
            stint["severity"] = "extended"
        else:
            stint["severity"] = "normal"


def print_summary(stints, pre_existing):
    classified = [s for s in stints if s["severity"] != "n/a"]
    print(f"Service stints measured: {len(stints)}")
    print(f"VIN+category slots with no prior install on record: {pre_existing}\n")

    if classified:
        premature = sum(1 for s in classified if s["severity"] == "premature")
        print(f"Premature failures (bottom quartile km for their category): "
              f"{premature} ({premature / len(classified):.1%})\n")

    print(f"{'category':<24}{'n':>6}{'avg km':>12}{'avg days':>10}{'premature':>11}")
    by_category = collections.defaultdict(list)
    for stint in stints:
        by_category[stint["part_category"]].append(stint)
    for category in sorted(by_category):
        group = by_category[category]
        avg_km = statistics.mean(s["km_driven"] for s in group)
        avg_days = statistics.mean(s["days_in_service"] for s in group)
        n_premature = sum(1 for s in group if s["severity"] == "premature")
        print(f"{category:<24}{len(group):>6}{avg_km:>12.0f}{avg_days:>10.0f}{n_premature:>11}")

    print(f"\n{'install_type':<24}{'n':>6}{'avg km':>12}{'avg days':>10}")
    by_install_type = collections.defaultdict(list)
    for stint in stints:
        by_install_type[stint["install_type"]].append(stint)
    for install_type in sorted(by_install_type):
        group = by_install_type[install_type]
        avg_km = statistics.mean(s["km_driven"] for s in group)
        avg_days = statistics.mean(s["days_in_service"] for s in group)
        print(f"{install_type:<24}{len(group):>6}{avg_km:>12.0f}{avg_days:>10.0f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="job_cards.csv")
    parser.add_argument("--out", default="wear_analysis.csv")
    args = parser.parse_args()

    with open(args.input, newline="") as f:
        rows = list(csv.DictReader(f))

    stints, pre_existing = build_stints(rows)
    classify_severity(stints)
    stints.sort(key=lambda s: (s["install_date"], s["install_job_card_id"]))

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=STINT_FIELDS)
        writer.writeheader()
        writer.writerows(stints)

    print(f"Wrote {len(stints)} service stints to {args.out}\n")
    print_summary(stints, pre_existing)


if __name__ == "__main__":
    main()
