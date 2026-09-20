import csv
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval_extraction import FIELDS, main, norm


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class NormTests(unittest.TestCase):
    def test_none_becomes_empty_string(self):
        self.assertEqual(norm(None), "")

    def test_strips_whitespace_and_lowercases(self):
        self.assertEqual(norm("  TSK-123456  "), "tsk-123456")


class MainScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.truth_path = os.path.join(self.tmpdir.name, "truth.csv")
        self.extracted_path = os.path.join(self.tmpdir.name, "extracted.csv")

    def run_eval(self):
        argv = sys.argv
        sys.argv = ["eval_extraction.py", "--extracted", self.extracted_path, "--truth", self.truth_path]
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                main()
        finally:
            sys.argv = argv
        return buf.getvalue()

    def test_reports_correct_hallucination_and_miss_rates(self):
        fieldnames = ["job_id"] + FIELDS
        write_csv(self.truth_path, fieldnames, [
            {"job_id": "JC-1", "task_number": "TSK-100000", "part_number_removed": "",
             "serial_number_removed": "", "part_number_installed": "", "serial_number_installed": ""},
            {"job_id": "JC-2", "task_number": "", "part_number_removed": "",
             "serial_number_removed": "", "part_number_installed": "", "serial_number_installed": ""},
        ])
        write_csv(self.extracted_path, fieldnames, [
            {"job_id": "JC-1", "task_number": "", "part_number_removed": "",
             "serial_number_removed": "", "part_number_installed": "", "serial_number_installed": ""},
            {"job_id": "JC-2", "task_number": "TSK-999999", "part_number_removed": "",
             "serial_number_removed": "", "part_number_installed": "", "serial_number_installed": ""},
        ])

        output = self.run_eval()

        self.assertIn("Scoring 2 rows", output)
        task_line = next(line for line in output.splitlines() if line.startswith("task_number"))
        self.assertIn("0.0%", task_line)
        self.assertIn("50.0%", task_line)

    def test_case_and_whitespace_insensitive_match_counts_as_correct(self):
        fieldnames = ["job_id"] + FIELDS
        write_csv(self.truth_path, fieldnames, [
            {"job_id": "JC-1", "task_number": "TSK-100000", "part_number_removed": "",
             "serial_number_removed": "", "part_number_installed": "", "serial_number_installed": ""},
        ])
        write_csv(self.extracted_path, fieldnames, [
            {"job_id": "JC-1", "task_number": "  tsk-100000  ", "part_number_removed": "",
             "serial_number_removed": "", "part_number_installed": "", "serial_number_installed": ""},
        ])

        output = self.run_eval()

        task_line = next(line for line in output.splitlines() if line.startswith("task_number"))
        self.assertIn("100.0%", task_line)

    def test_no_overlapping_ids_reports_and_does_not_crash(self):
        fieldnames = ["job_id"] + FIELDS
        write_csv(self.truth_path, fieldnames, [
            {"job_id": "JC-1", "task_number": "TSK-100000", "part_number_removed": "",
             "serial_number_removed": "", "part_number_installed": "", "serial_number_installed": ""},
        ])
        write_csv(self.extracted_path, fieldnames, [
            {"job_id": "JC-2", "task_number": "TSK-999999", "part_number_removed": "",
             "serial_number_removed": "", "part_number_installed": "", "serial_number_installed": ""},
        ])

        output = self.run_eval()

        self.assertIn("No overlapping job_ids", output)


if __name__ == "__main__":
    unittest.main()
