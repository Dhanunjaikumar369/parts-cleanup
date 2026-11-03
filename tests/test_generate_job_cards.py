import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_job_cards import generate, PART_CATALOG

PART_NUMBER_RE = re.compile(r"^[A-Z0-9]{2,4}-[A-Z0-9]{2}-\d{4}$")
SERIAL_RE = re.compile(r"^SN-[A-Z0-9]{2,4}-\d{8}$")


class GenerateJobCardsTest(unittest.TestCase):
    def test_row_count_matches_request(self):
        rows = generate(n_records=50, n_vehicles=10, seed=1, start_year=2020)
        self.assertEqual(len(rows), 50)

    def test_job_card_ids_are_unique_and_sequential(self):
        rows = generate(n_records=40, n_vehicles=10, seed=1, start_year=2020)
        ids = [r["job_card_id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [f"JC-{i:06d}" for i in range(1, 41)])

    def test_serial_numbers_are_globally_unique(self):
        rows = generate(n_records=200, n_vehicles=20, seed=7, start_year=2020)
        serials = [r["serial_number_removed"] for r in rows] + [
            r["serial_number_installed"] for r in rows if r["install_type"] == "New"
        ]
        self.assertEqual(len(serials), len(set(serials)))

    def test_part_and_serial_number_formats(self):
        rows = generate(n_records=100, n_vehicles=15, seed=3, start_year=2020)
        for r in rows:
            self.assertRegex(r["part_number_removed"], PART_NUMBER_RE)
            self.assertRegex(r["part_number_installed"], PART_NUMBER_RE)
            self.assertRegex(r["serial_number_removed"], SERIAL_RE)
            self.assertRegex(r["serial_number_installed"], SERIAL_RE)

    def test_reused_parts_come_from_a_different_earlier_vin(self):
        rows = generate(n_records=500, n_vehicles=25, seed=11, start_year=2016)
        by_id = {r["job_card_id"]: r for r in rows}
        seen_reuse = False
        for r in rows:
            if r["install_type"] != "Reused":
                continue
            seen_reuse = True
            self.assertNotEqual(r["reused_from_vin"], r["vin"])
            source = by_id[r["reused_from_job_card_id"]]
            self.assertLess(source["job_card_id"], r["job_card_id"])
            self.assertEqual(source["vin"], r["reused_from_vin"])
            self.assertEqual(source["part_category"], r["part_category"])
            self.assertEqual(source["serial_number_removed"], r["serial_number_installed"])
        self.assertTrue(seen_reuse, "expected at least one reused part in a 500-row sample")

    def test_new_installs_have_no_reuse_metadata(self):
        rows = generate(n_records=100, n_vehicles=15, seed=3, start_year=2020)
        for r in rows:
            if r["install_type"] == "New":
                self.assertEqual(r["reused_from_job_card_id"], "")
                self.assertEqual(r["reused_from_vin"], "")

    def test_part_category_is_from_catalog(self):
        rows = generate(n_records=60, n_vehicles=10, seed=5, start_year=2020)
        for r in rows:
            self.assertIn(r["part_category"], PART_CATALOG)

    def test_same_seed_is_deterministic(self):
        rows_a = generate(n_records=30, n_vehicles=8, seed=42, start_year=2020)
        rows_b = generate(n_records=30, n_vehicles=8, seed=42, start_year=2020)
        self.assertEqual(rows_a, rows_b)


if __name__ == "__main__":
    unittest.main()
