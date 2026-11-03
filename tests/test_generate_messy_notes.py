import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_messy_notes import generate

TRUTH_FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]


class GenerateMessyNotesTest(unittest.TestCase):
    def test_row_counts_match_request(self):
        notes_rows, truth_rows = generate(n_records=50, n_vehicles=10, seed=1, start_year=2020)
        self.assertEqual(len(notes_rows), 50)
        self.assertEqual(len(truth_rows), 50)

    def test_notes_and_truth_are_aligned_by_job_and_vin(self):
        notes_rows, truth_rows = generate(n_records=80, n_vehicles=12, seed=2, start_year=2020)
        for note, truth in zip(notes_rows, truth_rows):
            self.assertEqual(note["job_id"], truth["job_id"])
            self.assertEqual(note["vin_id"], truth["vin_id"])

    def test_every_nonblank_truth_value_appears_verbatim_in_its_note(self):
        notes_rows, truth_rows = generate(n_records=300, n_vehicles=20, seed=4, start_year=2020)
        for note, truth in zip(notes_rows, truth_rows):
            for field in TRUTH_FIELDS:
                value = truth[field]
                if value:
                    self.assertIn(value, note["notes"], f"{field}={value!r} missing from note text")

    def test_some_rows_have_no_extractable_info(self):
        _, truth_rows = generate(n_records=300, n_vehicles=20, seed=4, start_year=2020)
        no_info = [t for t in truth_rows if not any(t[f] for f in TRUTH_FIELDS)]
        self.assertTrue(no_info, "expected at least one row with no extractable fields")

    def test_some_rows_have_full_extractable_info(self):
        _, truth_rows = generate(n_records=300, n_vehicles=20, seed=4, start_year=2020)
        full_info = [t for t in truth_rows if all(t[f] for f in TRUTH_FIELDS)]
        self.assertTrue(full_info, "expected at least one row with all five fields present")

    def test_same_seed_is_deterministic(self):
        a = generate(n_records=30, n_vehicles=8, seed=42, start_year=2020)
        b = generate(n_records=30, n_vehicles=8, seed=42, start_year=2020)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
