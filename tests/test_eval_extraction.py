import csv
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import eval_extraction as ee


class NormTest(unittest.TestCase):
    def test_strips_and_lowercases(self):
        self.assertEqual(ee.norm("  ABC-123 "), "abc-123")

    def test_none_becomes_empty_string(self):
        self.assertEqual(ee.norm(None), "")

    def test_empty_string_stays_empty(self):
        self.assertEqual(ee.norm(""), "")


TRUTH_ROWS = [
    {"job_id": "JC-1", "task_number": "TSK-1", "part_number_removed": "", "serial_number_removed": "",
     "part_number_installed": "PN-A", "serial_number_installed": "SN-A"},
    {"job_id": "JC-2", "task_number": "", "part_number_removed": "", "serial_number_removed": "",
     "part_number_installed": "", "serial_number_installed": ""},
    {"job_id": "JC-3", "task_number": "TSK-3", "part_number_removed": "PN-B", "serial_number_removed": "SN-B",
     "part_number_installed": "PN-C", "serial_number_installed": "SN-C"},
]

# JC-1: task_number matches; part_number_installed/serial_number_installed match
# JC-2: everything correctly left blank, except task_number is hallucinated
# JC-3: task_number missed (blank), part_number_removed matches, rest blank/missed
EXTRACTED_ROWS = [
    {"job_id": "JC-1", "task_number": "TSK-1", "part_number_removed": "", "serial_number_removed": "",
     "part_number_installed": "PN-A", "serial_number_installed": "SN-A"},
    {"job_id": "JC-2", "task_number": "TSK-999", "part_number_removed": "", "serial_number_removed": "",
     "part_number_installed": "", "serial_number_installed": ""},
    {"job_id": "JC-3", "task_number": "", "part_number_removed": "PN-B", "serial_number_removed": "",
     "part_number_installed": "", "serial_number_installed": ""},
]


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


class EvalExtractionCliTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.TemporaryDirectory()
        self.truth_path = Path(self.tmpdir.name) / "truth.csv"
        self.extracted_path = Path(self.tmpdir.name) / "extracted.csv"
        write_csv(self.truth_path, TRUTH_ROWS, ["job_id"] + ee.FIELDS)
        write_csv(self.extracted_path, EXTRACTED_ROWS, ["job_id"] + ee.FIELDS)

    def tearDown(self):
        self.tmpdir.cleanup()

    def run_eval(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "eval_extraction.py"),
             "--extracted", str(self.extracted_path), "--truth", str(self.truth_path)],
            capture_output=True, text=True, check=True,
        )
        return result.stdout

    def test_scores_task_number_field(self):
        out = self.run_eval()
        # task_number: JC-1 correct, JC-2 hallucinated, JC-3 missed -> 1/3 each
        line = next(l for l in out.splitlines() if l.startswith("task_number"))
        self.assertIn("33.3%", line)

    def test_scores_fully_correct_field(self):
        out = self.run_eval()
        # part_number_installed: JC-1 correct, JC-2 correct (both blank), JC-3 missed
        line = next(l for l in out.splitlines() if l.startswith("part_number_installed"))
        parts = line.split()
        self.assertEqual(parts[1], "66.7%")

    def test_reports_row_count(self):
        out = self.run_eval()
        self.assertIn("Scoring 3 rows", out)

    def test_no_overlap_prints_message(self):
        write_csv(self.extracted_path, [{"job_id": "JC-999", **{f: "" for f in ee.FIELDS}}],
                  ["job_id"] + ee.FIELDS)
        out = self.run_eval()
        self.assertIn("No overlapping job_ids", out)


if __name__ == "__main__":
    unittest.main()
