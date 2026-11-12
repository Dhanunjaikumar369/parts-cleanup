import csv
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import eval_extraction as ee


class TestNorm(unittest.TestCase):
    def test_none_becomes_empty_string(self):
        self.assertEqual(ee.norm(None), "")

    def test_strips_and_lowercases(self):
        self.assertEqual(ee.norm("  TSK-123456  "), "tsk-123456")

    def test_already_normalized_value_is_unchanged(self):
        self.assertEqual(ee.norm("abc"), "abc")


class TestMainScoring(unittest.TestCase):
    """Runs main() end-to-end against small, hand-crafted CSVs to check the
    accuracy/hallucination/miss arithmetic, not just that it executes."""

    def _write_csv(self, path, fieldnames, rows):
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_scoring_arithmetic(self):
        fields = [
            "job_id", "vin_id", "task_number", "part_number_removed",
            "serial_number_removed", "part_number_installed", "serial_number_installed",
        ]
        truth_rows = [
            {"job_id": "JC-1", "vin_id": "V1", "task_number": "TSK-1",
             "part_number_removed": "", "serial_number_removed": "",
             "part_number_installed": "", "serial_number_installed": ""},
            {"job_id": "JC-2", "vin_id": "V2", "task_number": "",
             "part_number_removed": "", "serial_number_removed": "",
             "part_number_installed": "", "serial_number_installed": ""},
            {"job_id": "JC-3", "vin_id": "V3", "task_number": "TSK-3",
             "part_number_removed": "", "serial_number_removed": "",
             "part_number_installed": "", "serial_number_installed": ""},
            {"job_id": "JC-4", "vin_id": "V4", "task_number": "TSK-4",
             "part_number_removed": "", "serial_number_removed": "",
             "part_number_installed": "", "serial_number_installed": ""},
        ]
        extracted_rows = [
            # exact match -> correct
            {**truth_rows[0], "task_number": "TSK-1"},
            # truth blank, extracted non-blank -> hallucinated
            {**truth_rows[1], "task_number": "TSK-2"},
            # truth non-blank, extracted blank -> missed
            {**truth_rows[2], "task_number": ""},
            # case/whitespace-insensitive match -> correct
            {**truth_rows[3], "task_number": "  tsk-4  "},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            truth_path = os.path.join(tmp, "truth.csv")
            extracted_path = os.path.join(tmp, "extracted.csv")
            self._write_csv(truth_path, fields, truth_rows)
            self._write_csv(extracted_path, fields, extracted_rows)

            argv = sys.argv
            out = io.StringIO()
            try:
                sys.argv = ["eval_extraction.py", "--extracted", extracted_path, "--truth", truth_path]
                with redirect_stdout(out):
                    ee.main()
            finally:
                sys.argv = argv

        lines = out.getvalue().splitlines()
        task_line = next(line for line in lines if line.startswith("task_number"))
        # 2 of 4 correct, 1 hallucinated, 1 missed
        self.assertIn("50.0%", task_line)
        self.assertIn("25.0%", task_line)

    def test_no_overlapping_ids_prints_message(self):
        fields = ["job_id", "vin_id", "task_number", "part_number_removed",
                  "serial_number_removed", "part_number_installed", "serial_number_installed"]
        with tempfile.TemporaryDirectory() as tmp:
            truth_path = os.path.join(tmp, "truth.csv")
            extracted_path = os.path.join(tmp, "extracted.csv")
            self._write_csv(truth_path, fields, [{f: "" for f in fields} | {"job_id": "JC-1"}])
            self._write_csv(extracted_path, fields, [{f: "" for f in fields} | {"job_id": "JC-2"}])

            argv = sys.argv
            out = io.StringIO()
            try:
                sys.argv = ["eval_extraction.py", "--extracted", extracted_path, "--truth", truth_path]
                with redirect_stdout(out):
                    ee.main()
            finally:
                sys.argv = argv

        self.assertIn("No overlapping job_ids", out.getvalue())


if __name__ == "__main__":
    unittest.main()
