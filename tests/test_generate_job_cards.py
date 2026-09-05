#!/usr/bin/env python3
"""Unit tests for generate_job_cards.py."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_job_cards import generate, PART_CATALOG


class GenerateJobCardsTest(unittest.TestCase):
    def test_row_count_and_ids_are_sequential(self):
        rows = generate(n_records=200, n_vehicles=50, seed=1, start_year=2020)
        self.assertEqual(len(rows), 200)
        ids = [r["job_card_id"] for r in rows]
        self.assertEqual(ids, [f"JC-{i:06d}" for i in range(1, 201)])

    def test_deterministic_for_same_seed(self):
        rows_a = generate(n_records=100, n_vehicles=30, seed=7, start_year=2018)
        rows_b = generate(n_records=100, n_vehicles=30, seed=7, start_year=2018)
        self.assertEqual(rows_a, rows_b)

    def test_serials_are_globally_unique(self):
        rows = generate(n_records=300, n_vehicles=80, seed=3, start_year=2019)
        removed = [r["serial_number_removed"] for r in rows]
        self.assertEqual(len(removed), len(set(removed)))

    def test_new_installs_have_no_reuse_bookkeeping(self):
        rows = generate(n_records=300, n_vehicles=80, seed=3, start_year=2019)
        for r in rows:
            if r["install_type"] == "New":
                self.assertEqual(r["reused_from_job_card_id"], "")
                self.assertEqual(r["reused_from_vin"], "")

    def test_reused_parts_trace_back_to_an_earlier_removal_on_a_different_vin(self):
        rows = generate(n_records=2000, n_vehicles=100, seed=11, start_year=2016)
        reused_rows = [r for r in rows if r["install_type"] == "Reused"]
        self.assertGreater(len(reused_rows), 0, "expected at least one reused part in this sample")

        removed_by_id = {r["job_card_id"]: r for r in rows}
        for row in reused_rows:
            source_id = row["reused_from_job_card_id"]
            self.assertIn(source_id, removed_by_id)
            source = removed_by_id[source_id]

            # A reused part must have come from a *different* vehicle.
            self.assertNotEqual(row["vin"], row["reused_from_vin"])
            self.assertEqual(source["vin"], row["reused_from_vin"])

            # The installed part/serial must match what was removed at the source job card.
            self.assertEqual(row["part_number_installed"], source["part_number_removed"])
            self.assertEqual(row["serial_number_installed"], source["serial_number_removed"])

            # The source job card must have happened earlier in the sequence.
            self.assertLess(int(source_id.split("-")[1]), int(row["job_card_id"].split("-")[1]))

    def test_part_category_matches_part_number_prefix(self):
        rows = generate(n_records=150, n_vehicles=40, seed=5, start_year=2021)
        for r in rows:
            prefix = PART_CATALOG[r["part_category"]][0]
            self.assertTrue(r["part_number_removed"].startswith(prefix + "-"))


if __name__ == "__main__":
    unittest.main()
