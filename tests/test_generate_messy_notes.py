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
    def setUp(self):
        self.notes_rows, self.truth_rows = generate(
            n_records=400, n_vehicles=25, seed=3, start_year=2020
        )

    def test_row_counts_match(self):
        self.assertEqual(len(self.notes_rows), 400)
        self.assertEqual(len(self.truth_rows), 400)

    def test_job_ids_align_between_notes_and_truth(self):
        for notes_row, truth_row in zip(self.notes_rows, self.truth_rows):
            self.assertEqual(notes_row["job_id"], truth_row["job_id"])
            self.assertEqual(notes_row["vin_id"], truth_row["vin_id"])

    def test_every_nonblank_truth_value_appears_verbatim_in_its_note(self):
        # This is the dataset's core contract (see generate_messy_notes.py docstring):
        # ground truth only records a field when it is actually stated in the note.
        for notes_row, truth_row in zip(self.notes_rows, self.truth_rows):
            for field in TRUTH_FIELDS:
                value = truth_row[field]
                if value:
                    self.assertIn(
                        value, notes_row["notes"],
                        f"{field}={value!r} not found verbatim in note for {truth_row['job_id']}",
                    )

    def test_some_notes_have_no_extractable_info(self):
        no_info = [r for r in self.truth_rows if not any(r[f] for f in TRUTH_FIELDS)]
        self.assertGreater(len(no_info), 0)
        self.assertLess(len(no_info), len(self.truth_rows))

    def test_some_notes_are_fully_populated(self):
        full = [r for r in self.truth_rows if all(r[f] for f in TRUTH_FIELDS)]
        self.assertGreater(len(full), 0)

    def test_same_seed_is_deterministic(self):
        notes_again, truth_again = generate(
            n_records=400, n_vehicles=25, seed=3, start_year=2020
        )
        self.assertEqual(self.notes_rows, notes_again)
        self.assertEqual(self.truth_rows, truth_again)


if __name__ == "__main__":
    unittest.main()
