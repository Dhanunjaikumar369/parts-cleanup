#!/usr/bin/env python3
"""Unit tests for generate_messy_notes.py."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_messy_notes import generate

TRUTH_FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]


class GenerateMessyNotesTest(unittest.TestCase):
    def test_notes_and_truth_rows_line_up(self):
        notes_rows, truth_rows = generate(n_records=200, n_vehicles=50, seed=1, start_year=2020)
        self.assertEqual(len(notes_rows), 200)
        self.assertEqual(len(truth_rows), 200)
        for n, t in zip(notes_rows, truth_rows):
            self.assertEqual(n["job_id"], t["job_id"])
            self.assertEqual(n["vin_id"], t["vin_id"])

    def test_deterministic_for_same_seed(self):
        a = generate(n_records=100, n_vehicles=30, seed=7, start_year=2018)
        b = generate(n_records=100, n_vehicles=30, seed=7, start_year=2018)
        self.assertEqual(a, b)

    def test_ground_truth_values_only_recorded_when_mentioned_in_note(self):
        # Every non-blank ground-truth field must actually appear as a substring
        # of the note text -- otherwise the LLM has no way to "explicitly" extract it.
        notes_rows, truth_rows = generate(n_records=500, n_vehicles=100, seed=13, start_year=2016)
        for note, truth in zip(notes_rows, truth_rows):
            for field in TRUTH_FIELDS:
                value = truth[field]
                if value:
                    self.assertIn(value, note["notes"],
                                  f"{field}={value!r} not found in note: {note['notes']!r}")

    def test_no_info_notes_have_fully_blank_ground_truth(self):
        notes_rows, truth_rows = generate(n_records=500, n_vehicles=100, seed=13, start_year=2016)
        blank_truth_count = sum(
            1 for t in truth_rows if not any(t[f] for f in TRUTH_FIELDS)
        )
        # With NO_INFO_TEMPLATES weighted at ~20% of rows, some should show up in this sample.
        self.assertGreater(blank_truth_count, 0)


if __name__ == "__main__":
    unittest.main()
