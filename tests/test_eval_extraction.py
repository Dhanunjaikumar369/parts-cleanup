#!/usr/bin/env python3
"""Unit tests for eval_extraction.py. Run with: python3 -m unittest discover tests"""
import csv
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval_extraction import FIELDS, main, norm


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestNorm(unittest.TestCase):
    def test_none_becomes_empty_string(self):
        self.assertEqual(norm(None), "")

    def test_strips_and_lowercases(self):
        self.assertEqual(norm("  TSK-123456  "), "tsk-123456")


class TestMain(unittest.TestCase):
    def run_eval(self, truth_rows, extracted_rows):
        with tempfile.TemporaryDirectory() as tmp:
            truth_path = os.path.join(tmp, "truth.csv")
            extracted_path = os.path.join(tmp, "extracted.csv")
            write_csv(truth_path, truth_rows, ["job_id", "vin_id"] + FIELDS)
            write_csv(extracted_path, extracted_rows, ["job_id", "vin_id"] + FIELDS)

            argv = sys.argv
            sys.argv = ["eval_extraction.py", "--extracted", extracted_path, "--truth", truth_path]
            out = io.StringIO()
            try:
                with redirect_stdout(out):
                    main()
            finally:
                sys.argv = argv
            return out.getvalue()

    def test_perfect_match_scores_100_percent(self):
        truth_rows = [
            {"job_id": "JC-000001", "vin_id": "V1", "task_number": "TSK-100000",
             "part_number_removed": "", "serial_number_removed": "",
             "part_number_installed": "", "serial_number_installed": ""},
        ]
        extracted_rows = [dict(truth_rows[0])]
        output = self.run_eval(truth_rows, extracted_rows)
        self.assertIn("task_number", output)
        for line in output.splitlines():
            if line.startswith("task_number"):
                self.assertIn("100.0%", line)

    def test_hallucination_and_miss_are_counted(self):
        truth_rows = [
            {"job_id": "JC-1", "vin_id": "V1", "task_number": "",
             "part_number_removed": "BRK-A1-1000", "serial_number_removed": "",
             "part_number_installed": "", "serial_number_installed": ""},
            {"job_id": "JC-2", "vin_id": "V2", "task_number": "",
             "part_number_removed": "", "serial_number_removed": "",
             "part_number_installed": "", "serial_number_installed": ""},
        ]
        extracted_rows = [
            {"job_id": "JC-1", "vin_id": "V1", "task_number": "",
             "part_number_removed": "", "serial_number_removed": "",
             "part_number_installed": "", "serial_number_installed": ""},
            {"job_id": "JC-2", "vin_id": "V2", "task_number": "",
             "part_number_removed": "BRK-A1-9999", "serial_number_removed": "",
             "part_number_installed": "", "serial_number_installed": ""},
        ]
        output = self.run_eval(truth_rows, extracted_rows)
        for line in output.splitlines():
            if line.startswith("part_number_removed"):
                self.assertIn("0.0%", line)  # accuracy
                self.assertIn("50.0%", line)  # hallucinated and missed, each one of two rows

    def test_no_overlapping_job_ids_reports_and_does_not_crash(self):
        truth_rows = [{"job_id": "JC-1", "vin_id": "V1", **{f: "" for f in FIELDS}}]
        extracted_rows = [{"job_id": "JC-2", "vin_id": "V2", **{f: "" for f in FIELDS}}]
        output = self.run_eval(truth_rows, extracted_rows)
        self.assertIn("No overlapping job_ids", output)


if __name__ == "__main__":
    unittest.main()
