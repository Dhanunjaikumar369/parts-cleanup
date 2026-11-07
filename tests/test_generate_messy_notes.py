#!/usr/bin/env python3
"""Unit tests for generate_messy_notes.py. Run with: python3 -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_messy_notes import generate

TRUTH_FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]


class TestGenerateMessyNotes(unittest.TestCase):
    def test_row_counts_match_requested(self):
        notes_rows, truth_rows = generate(n_records=300, n_vehicles=40, seed=2, start_year=2019)
        self.assertEqual(len(notes_rows), 300)
        self.assertEqual(len(truth_rows), 300)

    def test_deterministic_with_same_seed(self):
        notes_a, truth_a = generate(n_records=200, n_vehicles=25, seed=9, start_year=2020)
        notes_b, truth_b = generate(n_records=200, n_vehicles=25, seed=9, start_year=2020)
        self.assertEqual(notes_a, notes_b)
        self.assertEqual(truth_a, truth_b)

    def test_notes_and_truth_rows_align_by_job_and_vin(self):
        notes_rows, truth_rows = generate(n_records=200, n_vehicles=25, seed=4, start_year=2018)
        for note_row, truth_row in zip(notes_rows, truth_rows):
            self.assertEqual(note_row["job_id"], truth_row["job_id"])
            self.assertEqual(note_row["vin_id"], truth_row["vin_id"])

    def test_every_nonblank_ground_truth_value_appears_in_its_note(self):
        notes_rows, truth_rows = generate(n_records=500, n_vehicles=60, seed=6, start_year=2016)
        for note_row, truth_row in zip(notes_rows, truth_rows):
            for field in TRUTH_FIELDS:
                value = truth_row[field]
                if value:
                    self.assertIn(
                        value, note_row["notes"],
                        f"{field}={value!r} missing from note text for {truth_row['job_id']}",
                    )

    def test_some_notes_carry_no_extractable_fields(self):
        _, truth_rows = generate(n_records=500, n_vehicles=60, seed=6, start_year=2016)
        no_info_count = sum(
            1 for row in truth_rows if not any(row[field] for field in TRUTH_FIELDS)
        )
        self.assertGreater(no_info_count, 0)


if __name__ == "__main__":
    unittest.main()
