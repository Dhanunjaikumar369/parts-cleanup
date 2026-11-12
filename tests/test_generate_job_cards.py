import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_job_cards import generate, make_serial, make_vin, PART_CATALOG
import random


class TestMakeHelpers(unittest.TestCase):
    def test_vin_length_and_alphabet(self):
        rng = random.Random(1)
        vin = make_vin(rng)
        self.assertEqual(len(vin), 17)
        self.assertTrue(set(vin) <= set("ABCDEFGHJKLMNPRSTUVWXYZ0123456789"))

    def test_serial_format(self):
        rng = random.Random(1)
        serial = make_serial(rng, "BRK")
        self.assertRegex(serial, r"^SN-BRK-\d{8}$")


class TestGenerate(unittest.TestCase):
    def setUp(self):
        self.rows = generate(n_records=300, n_vehicles=20, seed=7, start_year=2020)

    def test_row_count(self):
        self.assertEqual(len(self.rows), 300)

    def test_job_card_ids_unique_and_sequential(self):
        ids = [r["job_card_id"] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        expected = [f"JC-{i:06d}" for i in range(1, len(self.rows) + 1)]
        self.assertEqual(ids, expected)

    def test_install_type_values(self):
        for row in self.rows:
            self.assertIn(row["install_type"], ("New", "Reused"))

    def test_reused_parts_come_from_a_different_vin_and_earlier_job(self):
        by_id = {r["job_card_id"]: r for r in self.rows}
        seen_reused = False
        for row in self.rows:
            if row["install_type"] != "Reused":
                continue
            seen_reused = True
            self.assertNotEqual(row["reused_from_vin"], row["vin"])
            source = by_id[row["reused_from_job_card_id"]]
            self.assertLess(source["job_card_id"], row["job_card_id"])
            self.assertEqual(source["part_number_removed"], row["part_number_installed"])
            self.assertEqual(source["serial_number_removed"], row["serial_number_installed"])
        self.assertTrue(seen_reused, "expected at least one reused part in a 300-row sample")

    def test_new_installs_have_no_reuse_metadata(self):
        for row in self.rows:
            if row["install_type"] == "New":
                self.assertEqual(row["reused_from_job_card_id"], "")
                self.assertEqual(row["reused_from_vin"], "")

    def test_removed_serials_are_globally_unique(self):
        serials = [r["serial_number_removed"] for r in self.rows]
        self.assertEqual(len(serials), len(set(serials)))

    def test_part_category_is_from_catalog(self):
        for row in self.rows:
            self.assertIn(row["part_category"], PART_CATALOG)

    def test_same_seed_is_deterministic(self):
        other = generate(n_records=300, n_vehicles=20, seed=7, start_year=2020)
        self.assertEqual(self.rows, other)

    def test_different_seed_changes_output(self):
        other = generate(n_records=300, n_vehicles=20, seed=8, start_year=2020)
        self.assertNotEqual(self.rows, other)


if __name__ == "__main__":
    unittest.main()
