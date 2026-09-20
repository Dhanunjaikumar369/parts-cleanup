import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_messy_notes import generate

TRUTH_FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]


class GenerateMessyNotesTests(unittest.TestCase):
    def test_row_counts_match_requested_count_and_line_up(self):
        notes_rows, truth_rows = generate(n_records=200, n_vehicles=25, seed=1, start_year=2020)
        self.assertEqual(len(notes_rows), 200)
        self.assertEqual(len(truth_rows), 200)
        for notes_row, truth_row in zip(notes_rows, truth_rows):
            self.assertEqual(notes_row["job_id"], truth_row["job_id"])
            self.assertEqual(notes_row["vin_id"], truth_row["vin_id"])

    def test_deterministic_for_same_seed(self):
        result_a = generate(n_records=150, n_vehicles=20, seed=9, start_year=2019)
        result_b = generate(n_records=150, n_vehicles=20, seed=9, start_year=2019)
        self.assertEqual(result_a, result_b)

    def test_ground_truth_values_appear_verbatim_in_their_note(self):
        notes_rows, truth_rows = generate(n_records=300, n_vehicles=30, seed=4, start_year=2018)
        for notes_row, truth_row in zip(notes_rows, truth_rows):
            for field in TRUTH_FIELDS:
                value = truth_row[field]
                if value:
                    self.assertIn(value, notes_row["notes"])

    def test_some_notes_carry_no_extractable_info(self):
        _, truth_rows = generate(n_records=500, n_vehicles=40, seed=6, start_year=2016)
        no_info = [r for r in truth_rows if not any(r[f] for f in TRUTH_FIELDS)]
        self.assertGreater(len(no_info), 0)

    def test_some_notes_carry_full_extractable_info(self):
        _, truth_rows = generate(n_records=500, n_vehicles=40, seed=6, start_year=2016)
        full_info = [r for r in truth_rows if all(r[f] for f in TRUTH_FIELDS)]
        self.assertGreater(len(full_info), 0)


if __name__ == "__main__":
    unittest.main()
