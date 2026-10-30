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
    def test_deterministic_for_same_seed(self):
        a = generate(n_records=200, n_vehicles=30, seed=7, start_year=2020)
        b = generate(n_records=200, n_vehicles=30, seed=7, start_year=2020)
        self.assertEqual(a, b)

    def test_notes_and_truth_rows_align_on_job_id_and_vin(self):
        notes_rows, truth_rows = generate(n_records=300, n_vehicles=25, seed=4, start_year=2020)
        self.assertEqual(len(notes_rows), len(truth_rows))
        for note_row, truth_row in zip(notes_rows, truth_rows):
            self.assertEqual(note_row["job_id"], truth_row["job_id"])
            self.assertEqual(note_row["vin_id"], truth_row["vin_id"])

    def test_every_ground_truth_value_appears_verbatim_in_its_note(self):
        # Ground truth should only ever record a field when the note text actually
        # states it -- that's the whole point of the "explicitly mentioned" contract.
        notes_rows, truth_rows = generate(n_records=500, n_vehicles=30, seed=13, start_year=2020)
        for note_row, truth_row in zip(notes_rows, truth_rows):
            for field in TRUTH_FIELDS:
                value = truth_row[field]
                if value:
                    self.assertIn(value, note_row["notes"])

    def test_rows_with_no_extractable_info_leave_all_fields_blank(self):
        _, truth_rows = generate(n_records=500, n_vehicles=30, seed=13, start_year=2020)
        no_info_rows = [r for r in truth_rows if not any(r[f] for f in TRUTH_FIELDS)]
        self.assertGreater(len(no_info_rows), 0, "expected some notes with no extractable info")
        for r in no_info_rows:
            for field in TRUTH_FIELDS:
                self.assertEqual(r[field], "")

    def test_job_ids_are_unique_and_sequential(self):
        notes_rows, _ = generate(n_records=120, n_vehicles=15, seed=6, start_year=2020)
        ids = [r["job_id"] for r in notes_rows]
        self.assertEqual(ids, [f"JC-{i:06d}" for i in range(1, len(notes_rows) + 1)])


if __name__ == "__main__":
    unittest.main()
