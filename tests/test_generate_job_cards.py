import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generate_job_cards import generate


class GenerateJobCardsTest(unittest.TestCase):
    def test_row_count_and_ids(self):
        rows = generate(n_records=200, n_vehicles=30, seed=1, start_year=2020)
        self.assertEqual(len(rows), 200)
        self.assertEqual([r["job_card_id"] for r in rows],
                          [f"JC-{i:06d}" for i in range(1, 201)])

    def test_deterministic_for_fixed_seed(self):
        rows_a = generate(n_records=100, n_vehicles=20, seed=7, start_year=2020)
        rows_b = generate(n_records=100, n_vehicles=20, seed=7, start_year=2020)
        self.assertEqual(rows_a, rows_b)

    def test_removed_serials_are_globally_unique(self):
        # serial_number_removed is always freshly generated (it's the physical part
        # coming off *this* vehicle); serial_number_installed can legitimately repeat
        # an earlier removed serial when that part is reused on another vehicle.
        rows = generate(n_records=500, n_vehicles=50, seed=3, start_year=2020)
        removed_serials = [r["serial_number_removed"] for r in rows]
        self.assertEqual(len(removed_serials), len(set(removed_serials)))

    def test_reused_parts_come_from_a_different_vin_and_earlier_job(self):
        rows = generate(n_records=1000, n_vehicles=25, seed=11, start_year=2020)
        reused_rows = [r for r in rows if r["install_type"] == "Reused"]
        self.assertGreater(len(reused_rows), 0, "expected at least one reuse with a small vehicle pool")
        for r in reused_rows:
            self.assertNotEqual(r["reused_from_vin"], r["vin"])
            source_seq = int(r["reused_from_job_card_id"].split("-")[1])
            this_seq = int(r["job_card_id"].split("-")[1])
            self.assertLess(source_seq, this_seq)

    def test_new_installs_carry_no_reuse_metadata(self):
        rows = generate(n_records=300, n_vehicles=40, seed=5, start_year=2020)
        for r in rows:
            if r["install_type"] == "New":
                self.assertEqual(r["reused_from_job_card_id"], "")
                self.assertEqual(r["reused_from_vin"], "")


if __name__ == "__main__":
    unittest.main()
