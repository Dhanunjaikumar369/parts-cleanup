import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_job_cards import generate, PART_CATALOG


class GenerateJobCardsTest(unittest.TestCase):
    def test_deterministic_for_same_seed(self):
        a = generate(n_records=200, n_vehicles=30, seed=7, start_year=2020)
        b = generate(n_records=200, n_vehicles=30, seed=7, start_year=2020)
        self.assertEqual(a, b)

    def test_different_seed_changes_output(self):
        a = generate(n_records=200, n_vehicles=30, seed=7, start_year=2020)
        b = generate(n_records=200, n_vehicles=30, seed=8, start_year=2020)
        self.assertNotEqual(a, b)

    def test_job_card_ids_are_unique_and_sequential(self):
        rows = generate(n_records=150, n_vehicles=20, seed=1, start_year=2020)
        ids = [r["job_card_id"] for r in rows]
        self.assertEqual(ids, [f"JC-{i:06d}" for i in range(1, len(rows) + 1)])

    def test_reused_parts_come_from_a_different_vin_and_earlier_job_card(self):
        rows = generate(n_records=1500, n_vehicles=40, seed=3, start_year=2020)
        reused_rows = [r for r in rows if r["install_type"] == "Reused"]
        self.assertGreater(len(reused_rows), 0, "expected at least one reused part in this sample")

        seq_by_id = {r["job_card_id"]: i for i, r in enumerate(rows)}
        for r in reused_rows:
            self.assertNotEqual(r["reused_from_vin"], r["vin"])
            self.assertIn(r["reused_from_job_card_id"], seq_by_id)
            self.assertLess(seq_by_id[r["reused_from_job_card_id"]], seq_by_id[r["job_card_id"]])

    def test_new_installs_have_no_reuse_reference(self):
        rows = generate(n_records=300, n_vehicles=20, seed=5, start_year=2020)
        for r in rows:
            if r["install_type"] == "New":
                self.assertEqual(r["reused_from_job_card_id"], "")
                self.assertEqual(r["reused_from_vin"], "")

    def test_removed_serials_are_unique(self):
        rows = generate(n_records=500, n_vehicles=25, seed=11, start_year=2020)
        removed_serials = [r["serial_number_removed"] for r in rows]
        self.assertEqual(len(removed_serials), len(set(removed_serials)))

    def test_part_category_is_from_catalog(self):
        rows = generate(n_records=100, n_vehicles=10, seed=2, start_year=2020)
        for r in rows:
            self.assertIn(r["part_category"], PART_CATALOG)

    def test_row_count_matches_requested_count(self):
        rows = generate(n_records=50, n_vehicles=10, seed=9, start_year=2020)
        self.assertEqual(len(rows), 50)


if __name__ == "__main__":
    unittest.main()
