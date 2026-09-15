import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import generate_job_cards as gjc


class GenerateJobCardsTest(unittest.TestCase):
    def test_row_count_and_ids(self):
        rows = gjc.generate(n_records=200, n_vehicles=30, seed=1, start_year=2020)
        self.assertEqual(len(rows), 200)
        self.assertEqual(rows[0]["job_card_id"], "JC-000001")
        self.assertEqual(rows[-1]["job_card_id"], "JC-000200")

    def test_deterministic_for_same_seed(self):
        rows_a = gjc.generate(n_records=100, n_vehicles=20, seed=7, start_year=2020)
        rows_b = gjc.generate(n_records=100, n_vehicles=20, seed=7, start_year=2020)
        self.assertEqual(rows_a, rows_b)

    def test_vin_format(self):
        rng = gjc.random.Random(3)
        vin = gjc.make_vin(rng)
        self.assertEqual(len(vin), 17)
        self.assertFalse(set(vin) & set("IOQ"))

    def test_serials_are_unique(self):
        rows = gjc.generate(n_records=500, n_vehicles=50, seed=5, start_year=2020)
        removed = [r["serial_number_removed"] for r in rows]
        installed_new = [r["serial_number_installed"] for r in rows if r["install_type"] == "New"]
        all_new_serials = removed + installed_new
        self.assertEqual(len(all_new_serials), len(set(all_new_serials)))

    def test_reused_parts_come_from_a_different_vin(self):
        rows = gjc.generate(n_records=2000, n_vehicles=40, seed=11, start_year=2016)
        reused_rows = [r for r in rows if r["install_type"] == "Reused"]
        self.assertGreater(len(reused_rows), 0, "expected at least one reused part with this seed")
        for r in reused_rows:
            self.assertNotEqual(r["reused_from_vin"], r["vin"])
            self.assertTrue(r["reused_from_job_card_id"])

    def test_reused_part_matches_an_earlier_removal(self):
        rows = gjc.generate(n_records=2000, n_vehicles=40, seed=11, start_year=2016)
        by_id = {r["job_card_id"]: r for r in rows}
        reused_rows = [r for r in rows if r["install_type"] == "Reused"]
        self.assertGreater(len(reused_rows), 0)
        for r in reused_rows:
            source = by_id[r["reused_from_job_card_id"]]
            self.assertEqual(source["vin"], r["reused_from_vin"])
            self.assertEqual(source["serial_number_removed"], r["serial_number_installed"])
            self.assertEqual(source["part_number_removed"], r["part_number_installed"])
            # a part can only be reused once: the source job's own install_type
            # is irrelevant, but no other row should claim the same source.

    def test_reused_part_is_not_reused_twice(self):
        rows = gjc.generate(n_records=3000, n_vehicles=60, seed=23, start_year=2016)
        sources = [r["reused_from_job_card_id"] for r in rows if r["install_type"] == "Reused"]
        self.assertEqual(len(sources), len(set(sources)))

    def test_odometer_is_non_decreasing_per_vehicle(self):
        rows = gjc.generate(n_records=2000, n_vehicles=15, seed=9, start_year=2016)
        last_odo = {}
        for r in rows:
            vin = r["vin"]
            if vin in last_odo:
                self.assertGreaterEqual(r["odometer_km"], last_odo[vin])
            last_odo[vin] = r["odometer_km"]


if __name__ == "__main__":
    unittest.main()
