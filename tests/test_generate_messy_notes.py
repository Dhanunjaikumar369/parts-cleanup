import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generate_messy_notes import generate

TARGET_FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]


class GenerateMessyNotesTest(unittest.TestCase):
    def test_notes_and_truth_are_aligned(self):
        notes_rows, truth_rows = generate(n_records=300, n_vehicles=30, seed=2, start_year=2020)
        self.assertEqual(len(notes_rows), 300)
        self.assertEqual(len(truth_rows), 300)
        for note, truth in zip(notes_rows, truth_rows):
            self.assertEqual(note["job_id"], truth["job_id"])
            self.assertEqual(note["vin_id"], truth["vin_id"])

    def test_deterministic_for_fixed_seed(self):
        result_a = generate(n_records=150, n_vehicles=20, seed=9, start_year=2020)
        result_b = generate(n_records=150, n_vehicles=20, seed=9, start_year=2020)
        self.assertEqual(result_a, result_b)

    def test_ground_truth_values_are_actually_present_in_the_note_text(self):
        # Every non-blank ground-truth field must be traceable to the note text it
        # was extracted from -- otherwise the "eval" would be scoring against a
        # value the LLM was never given a chance to see.
        notes_rows, truth_rows = generate(n_records=500, n_vehicles=40, seed=13, start_year=2020)
        checked_any_field = False
        for note, truth in zip(notes_rows, truth_rows):
            for field in TARGET_FIELDS:
                value = truth[field]
                if value:
                    checked_any_field = True
                    self.assertIn(value, note["notes"])
        self.assertTrue(checked_any_field, "expected at least one populated ground-truth field")

    def test_some_notes_have_no_extractable_info(self):
        _, truth_rows = generate(n_records=500, n_vehicles=40, seed=13, start_year=2020)
        no_info = [t for t in truth_rows if not any(t[f] for f in TARGET_FIELDS)]
        self.assertGreater(len(no_info), 0)

    def test_removed_serials_are_globally_unique(self):
        # serial_number_removed is always freshly generated; serial_number_installed
        # can legitimately repeat an earlier removed serial when a part is reused.
        _, truth_rows = generate(n_records=500, n_vehicles=40, seed=17, start_year=2020)
        removed_serials = [t["serial_number_removed"] for t in truth_rows if t["serial_number_removed"]]
        self.assertEqual(len(removed_serials), len(set(removed_serials)))


if __name__ == "__main__":
    unittest.main()
