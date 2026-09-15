import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import generate_messy_notes as gmn

TRUTH_FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]


class GenerateMessyNotesTest(unittest.TestCase):
    def test_row_counts_and_ids_match(self):
        notes, truth = gmn.generate(n_records=300, n_vehicles=40, seed=1, start_year=2020)
        self.assertEqual(len(notes), 300)
        self.assertEqual(len(truth), 300)
        self.assertEqual([r["job_id"] for r in notes], [r["job_id"] for r in truth])

    def test_deterministic_for_same_seed(self):
        notes_a, truth_a = gmn.generate(n_records=150, n_vehicles=20, seed=4, start_year=2020)
        notes_b, truth_b = gmn.generate(n_records=150, n_vehicles=20, seed=4, start_year=2020)
        self.assertEqual(notes_a, notes_b)
        self.assertEqual(truth_a, truth_b)

    def test_ground_truth_values_appear_in_their_note_text(self):
        notes, truth = gmn.generate(n_records=500, n_vehicles=50, seed=8, start_year=2020)
        for note_row, truth_row in zip(notes, truth):
            for field in TRUTH_FIELDS:
                value = truth_row[field]
                if value:
                    self.assertIn(value, note_row["notes"],
                                  f"{field}={value!r} missing from note {note_row['job_id']!r}")

    def test_no_info_branch_reports_no_fields(self):
        # A roll that lands in the NO_INFO_TEMPLATES branch must yield an empty
        # fields set, since none of those templates mention the 5 target fields.
        class FixedRollRng:
            def __init__(self, roll, real_rng):
                self._roll = roll
                self._real = real_rng

            def random(self):
                return self._roll

            def __getattr__(self, name):
                return getattr(self._real, name)

        values = {
            "task": "TSK-100000", "cat": "Battery",
            "pn_r": "BAT-A1-1000", "sn_r": "SN-BAT-00000001",
            "pn_i": "BAT-B2-2000", "sn_i": "SN-BAT-00000002",
        }
        rng = FixedRollRng(0.95, gmn.random.Random(6))
        _, fields = gmn.build_note(rng, values)
        self.assertEqual(fields, set())

    def test_build_note_only_reports_fields_actually_in_template(self):
        rng = gmn.random.Random(2)
        values = {
            "task": "TSK-100000", "cat": "Battery",
            "pn_r": "BAT-A1-1000", "sn_r": "SN-BAT-00000001",
            "pn_i": "BAT-B2-2000", "sn_i": "SN-BAT-00000002",
        }
        for _ in range(200):
            text, fields = gmn.build_note(rng, values)
            for key, placeholder_value in (
                ("task", values["task"]), ("pn_r", values["pn_r"]), ("sn_r", values["sn_r"]),
                ("pn_i", values["pn_i"]), ("sn_i", values["sn_i"]),
            ):
                if key in fields:
                    self.assertIn(placeholder_value, text)


if __name__ == "__main__":
    unittest.main()
