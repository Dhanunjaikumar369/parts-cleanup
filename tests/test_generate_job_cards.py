import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_job_cards import PART_CATALOG, generate


class GenerateJobCardsTests(unittest.TestCase):
    def test_row_count_matches_requested_count(self):
        rows = generate(n_records=200, n_vehicles=30, seed=1, start_year=2020)
        self.assertEqual(len(rows), 200)

    def test_deterministic_for_same_seed(self):
        rows_a = generate(n_records=150, n_vehicles=20, seed=7, start_year=2019)
        rows_b = generate(n_records=150, n_vehicles=20, seed=7, start_year=2019)
        self.assertEqual(rows_a, rows_b)

    def test_serial_numbers_are_globally_unique(self):
        rows = generate(n_records=300, n_vehicles=40, seed=3, start_year=2018)
        removed = [r["serial_number_removed"] for r in rows]
        self.assertEqual(len(removed), len(set(removed)))

    def test_part_category_is_always_from_catalog(self):
        rows = generate(n_records=100, n_vehicles=15, seed=5, start_year=2021)
        for row in rows:
            self.assertIn(row["part_category"], PART_CATALOG)

    def test_reused_installs_come_from_a_different_vin(self):
        rows = generate(n_records=500, n_vehicles=25, seed=11, start_year=2016)
        reused = [r for r in rows if r["install_type"] == "Reused"]
        self.assertGreater(len(reused), 0, "expected at least one reuse with this seed/config")
        for row in reused:
            self.assertNotEqual(row["reused_from_vin"], row["vin"])
            self.assertNotEqual(row["reused_from_job_card_id"], row["job_card_id"])

    def test_reused_part_matches_an_earlier_removal(self):
        rows = generate(n_records=500, n_vehicles=25, seed=11, start_year=2016)
        removed_by_job_card = {r["job_card_id"]: r for r in rows}
        for row in rows:
            if row["install_type"] != "Reused":
                continue
            source = removed_by_job_card[row["reused_from_job_card_id"]]
            self.assertEqual(row["part_number_installed"], source["part_number_removed"])
            self.assertEqual(row["serial_number_installed"], source["serial_number_removed"])
            self.assertEqual(row["part_category"], source["part_category"])

    def test_new_installs_have_no_reuse_reference(self):
        rows = generate(n_records=200, n_vehicles=20, seed=2, start_year=2020)
        for row in rows:
            if row["install_type"] == "New":
                self.assertEqual(row["reused_from_job_card_id"], "")
                self.assertEqual(row["reused_from_vin"], "")


if __name__ == "__main__":
    unittest.main()
