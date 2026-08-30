#!/usr/bin/env python3
"""
Synthetic automotive job card data generator.

Produces job cards with a task number, the part removed, the part installed,
and their serial numbers. A fraction of installed parts are reused parts that
were removed from a *different* vehicle (VIN) at an earlier job card, so the
dataset carries traceable part-reuse chains across vehicles.
"""
import argparse
import csv
import random
import string
from datetime import date, timedelta

PART_CATALOG = {
    "Brake Pad Set": ("BRK", ["A1", "B2", "C3"]),
    "Brake Rotor": ("BRT", ["A1", "B2"]),
    "Alternator": ("ALT", ["A1", "B2", "C3"]),
    "Starter Motor": ("STM", ["A1", "B2"]),
    "Battery": ("BAT", ["A1", "B2", "C3"]),
    "Radiator": ("RAD", ["A1", "B2"]),
    "Water Pump": ("WTP", ["A1", "B2"]),
    "Timing Belt": ("TMB", ["A1", "B2"]),
    "Serpentine Belt": ("SPB", ["A1", "B2"]),
    "Air Filter": ("AFL", ["A1", "B2"]),
    "Oil Filter": ("OFL", ["A1", "B2"]),
    "Fuel Pump": ("FPM", ["A1", "B2"]),
    "Spark Plug Set": ("SPK", ["A1", "B2", "C3"]),
    "Shock Absorber": ("SHK", ["A1", "B2"]),
    "Strut Assembly": ("STA", ["A1", "B2"]),
    "Tire": ("TIR", ["A1", "B2", "C3"]),
    "Wheel Bearing": ("WHB", ["A1", "B2"]),
    "Clutch Kit": ("CLK", ["A1", "B2"]),
    "Transmission Filter": ("TRF", ["A1", "B2"]),
    "Catalytic Converter": ("CAT", ["A1", "B2"]),
    "Oxygen Sensor": ("O2S", ["A1", "B2"]),
    "Ignition Coil": ("IGC", ["A1", "B2"]),
    "AC Compressor": ("ACC", ["A1", "B2"]),
    "Power Steering Pump": ("PSP", ["A1", "B2"]),
    "CV Axle": ("CVA", ["A1", "B2"]),
}

MAKES_MODELS = {
    "Toyota": ["Camry", "Corolla", "RAV4", "Hilux"],
    "Honda": ["Civic", "Accord", "CR-V"],
    "Ford": ["F-150", "Focus", "Explorer"],
    "Hyundai": ["Elantra", "Tucson", "i20"],
    "Maruti Suzuki": ["Swift", "Baleno", "Ertiga"],
    "Tata": ["Nexon", "Harrier", "Tiago"],
    "Mahindra": ["XUV700", "Scorpio", "Thar"],
}

WORKSHOPS = [
    "Central Depot", "North Bay Workshop", "Riverside Service Center",
    "Eastgate Garage", "Metro Auto Works", "Hilltop Motors Service",
    "Lakeside Service Point", "Westline Auto Care",
]

VIN_CHARS = "".join(c for c in string.ascii_uppercase + string.digits if c not in "IOQ")
REUSE_PROB = 0.15


def make_vin(rng):
    return "".join(rng.choice(VIN_CHARS) for _ in range(17))


def make_serial(rng, prefix):
    return f"SN-{prefix}-{''.join(rng.choice(string.digits) for _ in range(8))}"


def random_date(rng, start, end):
    days = (end - start).days
    return start + timedelta(days=rng.randint(0, days))


def build_vehicle_pool(rng, n_vehicles):
    vehicles = {}
    for _ in range(n_vehicles):
        vin = make_vin(rng)
        make = rng.choice(list(MAKES_MODELS))
        model = rng.choice(MAKES_MODELS[make])
        vehicles[vin] = {
            "make": make,
            "model": model,
            "year": rng.randint(2005, 2024),
            "odometer": rng.randint(0, 5000),
            "visit_weight": rng.randint(1, 10),
        }
    return vehicles


def generate(n_records, n_vehicles, seed, start_year):
    rng = random.Random(seed)
    vehicles = build_vehicle_pool(rng, n_vehicles)
    vin_list = list(vehicles)
    weights = [vehicles[v]["visit_weight"] for v in vin_list]

    start_date = date(start_year, 1, 1)
    end_date = date.today()

    events = []
    for i in range(n_records):
        vin = rng.choices(vin_list, weights=weights, k=1)[0]
        job_date = random_date(rng, start_date, end_date)
        events.append((job_date, i, vin))
    events.sort(key=lambda e: (e[0], e[1]))

    reuse_pool = {cat: [] for cat in PART_CATALOG}
    rows = []
    used_serials = set()

    def unique_serial(prefix):
        while True:
            s = make_serial(rng, prefix)
            if s not in used_serials:
                used_serials.add(s)
                return s

    for seq, (job_date, _, vin) in enumerate(events, start=1):
        vehicle = vehicles[vin]
        vehicle["odometer"] += rng.randint(500, 15000)

        category = rng.choice(list(PART_CATALOG))
        prefix, variants = PART_CATALOG[category]

        part_number_removed = f"{prefix}-{rng.choice(variants)}-{rng.randint(1000, 9999)}"
        serial_number_removed = unique_serial(prefix)

        candidates = [c for c in reuse_pool[category] if c["vin"] != vin]
        if candidates and rng.random() < REUSE_PROB:
            reused = candidates[rng.randrange(len(candidates))]
            reuse_pool[category].remove(reused)
            part_number_installed = reused["part_number"]
            serial_number_installed = reused["serial"]
            install_type = "Reused"
            reused_from_job_card_id = reused["job_card_id"]
            reused_from_vin = reused["vin"]
        else:
            part_number_installed = f"{prefix}-{rng.choice(variants)}-{rng.randint(1000, 9999)}"
            serial_number_installed = unique_serial(prefix)
            install_type = "New"
            reused_from_job_card_id = ""
            reused_from_vin = ""

        job_card_id = f"JC-{seq:06d}"
        task_number = f"TSK-{rng.randint(100000, 999999)}"

        rows.append({
            "job_card_id": job_card_id,
            "job_date": job_date.isoformat(),
            "vin": vin,
            "vehicle_make": vehicle["make"],
            "vehicle_model": vehicle["model"],
            "vehicle_year": vehicle["year"],
            "odometer_km": vehicle["odometer"],
            "task_number": task_number,
            "part_category": category,
            "part_number_removed": part_number_removed,
            "serial_number_removed": serial_number_removed,
            "part_number_installed": part_number_installed,
            "serial_number_installed": serial_number_installed,
            "install_type": install_type,
            "reused_from_job_card_id": reused_from_job_card_id,
            "reused_from_vin": reused_from_vin,
            "technician_id": f"TECH-{rng.randint(1, 40):03d}",
            "workshop_location": rng.choice(WORKSHOPS),
        })

        reuse_pool[category].append({
            "part_number": part_number_removed,
            "serial": serial_number_removed,
            "job_card_id": job_card_id,
            "vin": vin,
        })

    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10000, help="number of job card rows")
    parser.add_argument("--vehicles", type=int, default=2500, help="number of unique VINs in the fleet")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-year", type=int, default=2016)
    parser.add_argument("--out", default="job_cards.csv")
    args = parser.parse_args()

    rows = generate(args.count, args.vehicles, args.seed, args.start_year)

    fieldnames = list(rows[0].keys())
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    reused = sum(1 for r in rows if r["install_type"] == "Reused")
    print(f"Wrote {len(rows)} job cards to {args.out}")
    print(f"Reused-part installs: {reused} ({reused / len(rows):.1%})")


if __name__ == "__main__":
    main()
