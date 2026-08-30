#!/usr/bin/env python3
"""
Generates messy, free-text job card notes for LLM extraction testing.

Public output (what the LLM sees):   job_cards_notes.csv        -> job_id, vin_id, notes
Private eval output (not for LLM):   job_cards_ground_truth.csv -> job_id, vin_id, task_number,
                                      part_number_removed, serial_number_removed,
                                      part_number_installed, serial_number_installed

Ground truth only records a field's value when that field is actually mentioned in the
note text. Fields the note omits are blank -- that's the correct target for the LLM to
also leave null, since the extraction task is "pull out what's stated," not "reconstruct
the full record."
"""
import argparse
import csv
import random
import string
from datetime import date, timedelta

PART_CATALOG = {
    "Brake Pad Set": "BRK", "Brake Rotor": "BRT", "Alternator": "ALT",
    "Starter Motor": "STM", "Battery": "BAT", "Radiator": "RAD",
    "Water Pump": "WTP", "Timing Belt": "TMB", "Serpentine Belt": "SPB",
    "Air Filter": "AFL", "Oil Filter": "OFL", "Fuel Pump": "FPM",
    "Spark Plug Set": "SPK", "Shock Absorber": "SHK", "Strut Assembly": "STA",
    "Tire": "TIR", "Wheel Bearing": "WHB", "Clutch Kit": "CLK",
    "Transmission Filter": "TRF", "Catalytic Converter": "CAT",
    "Oxygen Sensor": "O2S", "Ignition Coil": "IGC", "AC Compressor": "ACC",
    "Power Steering Pump": "PSP", "CV Axle": "CVA",
}

VIN_CHARS = "".join(c for c in string.ascii_uppercase + string.digits if c not in "IOQ")

# Each template declares which of the 5 target fields it actually mentions.
# Placeholders not in a template's field set are simply not referenced.
FULL_TEMPLATES = [
    ("{task} - {cat} inspected, showing wear. Removed {pn_r} / SN {sn_r}. "
     "Installed {pn_i}, serial {sn_i}. Verified OK.",
     {"task", "pn_r", "sn_r", "pn_i", "sn_i"}),
    ("Job {task}: swapped {cat}. Out: {pn_r} (SN {sn_r}). In: {pn_i} (SN {sn_i}).",
     {"task", "pn_r", "sn_r", "pn_i", "sn_i"}),
    ("{cat} replaced under {task}. Old serial {sn_r}, part {pn_r}. "
     "New serial {sn_i}, part {pn_i}.",
     {"task", "pn_r", "sn_r", "pn_i", "sn_i"}),
    ("chngd {cat_lc} - old sn {sn_r} pn {pn_r}, new pn {pn_i} sn {sn_i}. ref {task}",
     {"task", "pn_r", "sn_r", "pn_i", "sn_i"}),
    ("Removed worn {cat} (pn {pn_r}, s/n {sn_r}) due to excessive play. "
     "Fitted replacement pn {pn_i} s/n {sn_i}. {task} closed.",
     {"task", "pn_r", "sn_r", "pn_i", "sn_i"}),
]

PARTIAL_TEMPLATES = [
    ("{task}: {cat} removed - {pn_r} / SN {sn_r}. Replacement on backorder, "
     "vehicle released to customer temporarily.",
     {"task", "pn_r", "sn_r"}),
    ("{task}: fitted new {cat} {pn_i}, serial {sn_i}. No further issues noted.",
     {"task", "pn_i", "sn_i"}),
    ("{cat} showing heavy wear, pulled unit sn {sn_r} pn {pn_r} for inspection.",
     {"pn_r", "sn_r"}),
    ("{task} - general inspection of {cat}, no action required.",
     {"task"}),
    ("swapped {cat}: old sn {sn_r}, new sn {sn_i}. task {task}",
     {"task", "sn_r", "sn_i"}),
    ("{cat} replaced: {pn_r} -> {pn_i} under {task}.",
     {"task", "pn_r", "pn_i"}),
    ("Installed {pn_i} (sn {sn_i}) on {cat}. Prior part details not recorded on paper card.",
     {"pn_i", "sn_i"}),
]

NO_INFO_TEMPLATES = [
    "Checked {cat}, no fault found. No parts replaced.",
    "Customer reported noise from {cat}. Inspected - within spec. No action taken.",
    "Routine inspection completed. All ok.",
    "No issues found during {cat} check.",
    "See attached photos for reference.",
    "N/A",
    "Vehicle washed and returned to customer.",
    "Customer requested visual inspection only. Nothing further to report.",
    "Topped up fluids, checked tyre pressure. No parts required.",
]

DECOY_SUFFIXES = [
    " Odometer: {n} km.", " PO# {n}.", " Customer contact: 555-{n4}.",
    " Bay 3, lift 2.", " Warranty claim #{n}.", "",
    "",  # weight toward no decoy
]


def make_vin(rng):
    return "".join(rng.choice(VIN_CHARS) for _ in range(17))


def make_serial(rng, prefix):
    return f"SN-{prefix}-{''.join(rng.choice(string.digits) for _ in range(8))}"


def make_part_number(rng, prefix):
    variant = rng.choice(["A1", "B2", "C3"])
    return f"{prefix}-{variant}-{rng.randint(1000, 9999)}"


def random_date(rng, start, end):
    return start + timedelta(days=rng.randint(0, (end - start).days))


def build_note(rng, values):
    roll = rng.random()
    if roll < 0.5:
        template, fields = rng.choice(FULL_TEMPLATES)
    elif roll < 0.8:
        template, fields = rng.choice(PARTIAL_TEMPLATES)
    else:
        template = rng.choice(NO_INFO_TEMPLATES)
        fields = set()

    text = template.format(
        task=values["task"], cat=values["cat"], cat_lc=values["cat"].lower(),
        pn_r=values["pn_r"], sn_r=values["sn_r"],
        pn_i=values["pn_i"], sn_i=values["sn_i"],
    )

    decoy = rng.choice(DECOY_SUFFIXES)
    if decoy:
        text += decoy.format(n=rng.randint(10000, 99999), n4=rng.randint(1000, 9999))

    return text, fields


def generate(n_records, n_vehicles, seed, start_year):
    rng = random.Random(seed)
    vins = [make_vin(rng) for _ in range(n_vehicles)]
    weights = [rng.randint(1, 10) for _ in vins]

    start_date, end_date = date(start_year, 1, 1), date.today()
    reuse_pool = {cat: [] for cat in PART_CATALOG}
    used_serials = set()

    def unique_serial(prefix):
        while True:
            s = make_serial(rng, prefix)
            if s not in used_serials:
                used_serials.add(s)
                return s

    events = sorted(
        (random_date(rng, start_date, end_date), i, rng.choices(vins, weights=weights, k=1)[0])
        for i in range(n_records)
    )

    notes_rows, truth_rows = [], []
    for seq, (_, _, vin) in enumerate(events, start=1):
        job_id = f"JC-{seq:06d}"
        category = rng.choice(list(PART_CATALOG))
        prefix = PART_CATALOG[category]

        task = f"TSK-{rng.randint(100000, 999999)}"
        pn_r = make_part_number(rng, prefix)
        sn_r = unique_serial(prefix)

        candidates = [c for c in reuse_pool[category] if c["vin"] != vin]
        if candidates and rng.random() < 0.15:
            reused = candidates[rng.randrange(len(candidates))]
            reuse_pool[category].remove(reused)
            pn_i, sn_i = reused["part_number"], reused["serial"]
        else:
            pn_i = make_part_number(rng, prefix)
            sn_i = unique_serial(prefix)

        note_text, fields_present = build_note(
            rng, {"task": task, "cat": category, "pn_r": pn_r, "sn_r": sn_r, "pn_i": pn_i, "sn_i": sn_i}
        )

        notes_rows.append({"job_id": job_id, "vin_id": vin, "notes": note_text})
        truth_rows.append({
            "job_id": job_id,
            "vin_id": vin,
            "task_number": task if "task" in fields_present else "",
            "part_number_removed": pn_r if "pn_r" in fields_present else "",
            "serial_number_removed": sn_r if "sn_r" in fields_present else "",
            "part_number_installed": pn_i if "pn_i" in fields_present else "",
            "serial_number_installed": sn_i if "sn_i" in fields_present else "",
        })

        reuse_pool[category].append({"part_number": pn_r, "serial": sn_r, "vin": vin})

    return notes_rows, truth_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--vehicles", type=int, default=2500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-year", type=int, default=2016)
    parser.add_argument("--notes-out", default="job_cards_notes.csv")
    parser.add_argument("--truth-out", default="job_cards_ground_truth.csv")
    args = parser.parse_args()

    notes_rows, truth_rows = generate(args.count, args.vehicles, args.seed, args.start_year)

    with open(args.notes_out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["job_id", "vin_id", "notes"])
        w.writeheader()
        w.writerows(notes_rows)

    with open(args.truth_out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(truth_rows[0].keys()))
        w.writeheader()
        w.writerows(truth_rows)

    no_info = sum(1 for r in truth_rows if not any(
        r[k] for k in ("task_number", "part_number_removed", "serial_number_removed",
                        "part_number_installed", "serial_number_installed")))
    print(f"Wrote {len(notes_rows)} rows to {args.notes_out} (LLM input)")
    print(f"Wrote ground truth to {args.truth_out} (for scoring only, don't feed to LLM)")
    print(f"Notes with NO extractable info: {no_info} ({no_info/len(notes_rows):.1%})")


if __name__ == "__main__":
    main()
