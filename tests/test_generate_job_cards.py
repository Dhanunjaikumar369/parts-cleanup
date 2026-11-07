#!/usr/bin/env python3
"""Unit tests for generate_job_cards.py. Run with: python3 -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_job_cards import generate


class TestGenerateJobCards(unittest.TestCase):
    def test_row_count_matches_requested(self):
        rows = generate(n_records=200, n_vehicles=30, seed=1, start_year=2020)
        self.assertEqual(len(rows), 200)

    def test_deterministic_with_same_seed(self):
        rows_a = generate(n_records=150, n_vehicles=20, seed=7, start_year=2018)
        rows_b = generate(n_records=150, n_vehicles=20, seed=7, start_year=2018)
        self.assertEqual(rows_a, rows_b)

    def test_different_seeds_diverge(self):
        rows_a = generate(n_records=150, n_vehicles=20, seed=7, start_year=2018)
        rows_b = generate(n_records=150, n_vehicles=20, seed=8, start_year=2018)
        self.assertNotEqual(rows_a, rows_b)

    def test_job_card_ids_are_sequential_and_unique(self):
        rows = generate(n_records=300, n_vehicles=40, seed=3, start_year=2019)
        ids = [r["job_card_id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [f"JC-{i:06d}" for i in range(1, len(rows) + 1)])

    def test_install_type_is_new_or_reused(self):
        rows = generate(n_records=500, n_vehicles=50, seed=5, start_year=2017)
        for row in rows:
            self.assertIn(row["install_type"], ("New", "Reused"))

    def test_new_installs_have_no_reuse_backlink(self):
        rows = generate(n_records=500, n_vehicles=50, seed=5, start_year=2017)
        for row in rows:
            if row["install_type"] == "New":
                self.assertEqual(row["reused_from_job_card_id"], "")
                self.assertEqual(row["reused_from_vin"], "")

    def test_reused_installs_backlink_to_earlier_job_card_on_other_vin(self):
        rows = generate(n_records=2000, n_vehicles=100, seed=11, start_year=2016)
        reused_rows = [r for r in rows if r["install_type"] == "Reused"]
        self.assertGreater(len(reused_rows), 0, "seed/size should produce at least one reuse")
        for row in reused_rows:
            self.assertNotEqual(row["reused_from_job_card_id"], "")
            self.assertNotEqual(row["reused_from_vin"], row["vin"])
            source_seq = int(row["reused_from_job_card_id"].split("-")[1])
            own_seq = int(row["job_card_id"].split("-")[1])
            self.assertLess(source_seq, own_seq)

    def test_reused_part_and_serial_match_the_removed_part_from_source_job_card(self):
        rows = generate(n_records=2000, n_vehicles=100, seed=11, start_year=2016)
        by_id = {r["job_card_id"]: r for r in rows}
        for row in rows:
            if row["install_type"] == "Reused":
                source = by_id[row["reused_from_job_card_id"]]
                self.assertEqual(row["part_number_installed"], source["part_number_removed"])
                self.assertEqual(row["serial_number_installed"], source["serial_number_removed"])
                self.assertEqual(source["vin"], row["reused_from_vin"])

    def test_removed_serials_are_unique_across_rows(self):
        rows = generate(n_records=500, n_vehicles=50, seed=5, start_year=2017)
        removed_serials = [r["serial_number_removed"] for r in rows]
        self.assertEqual(len(removed_serials), len(set(removed_serials)))


if __name__ == "__main__":
    unittest.main()
