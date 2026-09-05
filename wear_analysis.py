#!/usr/bin/env python3
"""
Wear-and-tear analysis over job_cards.csv.

For each vehicle (VIN) + part category, consecutive job cards mark the start
and end of one part's service life on that vehicle: the earlier job card is
when it was installed, the later one is when it was pulled back out. This
computes how much distance/time that part actually saw, compares it against
a rough expected service life for its category, and buckets the result into
a condition severity plus a likely failure reason.

The first job card for a given VIN + category has no prior installation on
record, so it's reported with insufficient_data rather than a guessed severity.

Usage:
  python3 wear_analysis.py --input job_cards.csv --out job_cards_wear_analysis.csv
"""
import argparse
import csv
from collections import defaultdict
from datetime import date

# Rough expected service life per category, in km. These are ballpark
# figures used only to bucket severity for this synthetic dataset, not
# real manufacturer specs.
EXPECTED_LIFE_KM = {
    "Brake Pad Set": 45000, "Brake Rotor": 90000, "Alternator": 150000,
    "Starter Motor": 150000, "Battery": 80000, "Radiator": 150000,
    "Water Pump": 100000, "Timing Belt": 100000, "Serpentine Belt": 80000,
    "Air Filter": 25000, "Oil Filter": 10000, "Fuel Pump": 150000,
    "Spark Plug Set": 50000, "Shock Absorber": 100000, "Strut Assembly": 100000,
    "Tire": 60000, "Wheel Bearing": 120000, "Clutch Kit": 100000,
    "Transmission Filter": 80000, "Catalytic Converter": 160000,
    "Oxygen Sensor": 100000, "Ignition Coil": 100000, "AC Compressor": 130000,
    "Power Steering Pump": 120000, "CV Axle": 130000,
}
DEFAULT_EXPECTED_LIFE_KM = 90000

PREMATURE_RATIO = 0.5
EXTENDED_RATIO = 1.5


def classify_severity(ratio):
    if ratio < PREMATURE_RATIO:
        return "premature"
    if ratio > EXTENDED_RATIO:
        return "extended"
    return "expected"


def classify_failure_reason(severity, prior_install_type):
    if severity == "insufficient_data":
        return "no_prior_installation_record"
    if severity == "premature":
        if prior_install_type == "Reused":
            return "early_failure_reused_part"
        return "premature_wear_possible_defect"
    if severity == "extended":
        return "extended_service_life"
    return "normal_wear_out"


def analyze(rows):
    for r in rows:
        r["job_date"] = date.fromisoformat(r["job_date"])
        r["odometer_km"] = int(r["odometer_km"])

    groups = defaultdict(list)
    for r in rows:
        groups[(r["vin"], r["part_category"])].append(r)

    results = {}
    for key, group in groups.items():
        group.sort(key=lambda r: r["job_date"])
        prior = None
        for r in group:
            if prior is None:
                results[r["job_card_id"]] = {
                    "job_card_id": r["job_card_id"],
                    "vin": r["vin"],
                    "part_category": r["part_category"],
                    "job_date": r["job_date"].isoformat(),
                    "prior_job_card_id": "",
                    "usage_km": "",
                    "usage_days": "",
                    "expected_life_km": "",
                    "usage_ratio": "",
                    "condition_severity": "insufficient_data",
                    "failure_reason": classify_failure_reason("insufficient_data", None),
                }
            else:
                expected = EXPECTED_LIFE_KM.get(r["part_category"], DEFAULT_EXPECTED_LIFE_KM)
                usage_km = r["odometer_km"] - prior["odometer_km"]
                usage_days = (r["job_date"] - prior["job_date"]).days
                ratio = usage_km / expected
                severity = classify_severity(ratio)
                results[r["job_card_id"]] = {
                    "job_card_id": r["job_card_id"],
                    "vin": r["vin"],
                    "part_category": r["part_category"],
                    "job_date": r["job_date"].isoformat(),
                    "prior_job_card_id": prior["job_card_id"],
                    "usage_km": usage_km,
                    "usage_days": usage_days,
                    "expected_life_km": expected,
                    "usage_ratio": round(ratio, 3),
                    "condition_severity": severity,
                    "failure_reason": classify_failure_reason(severity, prior["install_type"]),
                }
            prior = r

    return [results[r["job_card_id"]] for r in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="job_cards.csv")
    parser.add_argument("--out", default="job_cards_wear_analysis.csv")
    args = parser.parse_args()

    with open(args.input, newline="") as f:
        rows = list(csv.DictReader(f))

    analyzed = analyze(rows)

    fieldnames = [
        "job_card_id", "vin", "part_category", "job_date", "prior_job_card_id",
        "usage_km", "usage_days", "expected_life_km", "usage_ratio",
        "condition_severity", "failure_reason",
    ]
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(analyzed)

    counts = defaultdict(int)
    for r in analyzed:
        counts[r["condition_severity"]] += 1

    print(f"Wrote wear analysis for {len(analyzed)} job cards to {args.out}\n")
    print(f"{'severity':<18}{'count':>10}{'share':>10}")
    for severity in ("insufficient_data", "premature", "expected", "extended"):
        n = counts.get(severity, 0)
        print(f"{severity:<18}{n:>10}{n/len(analyzed):>10.1%}")


if __name__ == "__main__":
    main()
