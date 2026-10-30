import csv
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "eval_extraction.py"

FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["job_id", "vin_id"] + FIELDS)
        w.writeheader()
        w.writerows(rows)


def run_eval(truth_path, extracted_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--truth", str(truth_path), "--extracted", str(extracted_path)],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def parse_field_line(output, field):
    match = re.search(rf"^{re.escape(field)}\s*([\d.]+)%\s*([\d.]+)%\s*([\d.]+)%", output, re.MULTILINE)
    assert match, f"could not find a results line for {field!r} in:\n{output}"
    return tuple(float(g) for g in match.groups())


class EvalExtractionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.truth_path = Path(self.tmp.name) / "truth.csv"
        self.extracted_path = Path(self.tmp.name) / "extracted.csv"

    def base_row(self, job_id, task_number_truth, task_number_extracted):
        # every other field matches exactly so only task_number varies per test row
        common = {
            "part_number_removed": "BRK-A1-1000", "serial_number_removed": "SN-BRK-00000001",
            "part_number_installed": "BRK-A1-2000", "serial_number_installed": "SN-BRK-00000002",
        }
        truth_row = {"job_id": job_id, "vin_id": "VIN1", "task_number": task_number_truth, **common}
        extracted_row = {"job_id": job_id, "vin_id": "VIN1", "task_number": task_number_extracted, **common}
        return truth_row, extracted_row

    def test_accuracy_hallucination_and_miss_rates(self):
        cases = [
            ("r1", "TSK-1", "TSK-1"),      # correct match
            ("r2", "TSK-2", ""),            # missed: truth has value, extraction blank
            ("r3", "", "TSK-3"),            # hallucinated: extraction invents a value
            ("r4", "", ""),                 # correct: both agree on null
            ("r5", "tsk-5 ", "TSK-5"),      # correct after case/whitespace normalization
        ]
        truth_rows, extracted_rows = [], []
        for job_id, truth_val, extracted_val in cases:
            t, e = self.base_row(job_id, truth_val, extracted_val)
            truth_rows.append(t)
            extracted_rows.append(e)

        write_csv(self.truth_path, truth_rows)
        write_csv(self.extracted_path, extracted_rows)

        output = run_eval(self.truth_path, self.extracted_path)

        accuracy, hallucinated, missed = parse_field_line(output, "task_number")
        self.assertAlmostEqual(accuracy, 60.0, places=1)
        self.assertAlmostEqual(hallucinated, 20.0, places=1)
        self.assertAlmostEqual(missed, 20.0, places=1)

        # the other four fields match exactly in every row -> perfect score, no noise
        for field in FIELDS[1:]:
            accuracy, hallucinated, missed = parse_field_line(output, field)
            self.assertAlmostEqual(accuracy, 100.0, places=1)
            self.assertAlmostEqual(hallucinated, 0.0, places=1)
            self.assertAlmostEqual(missed, 0.0, places=1)

    def test_no_overlapping_job_ids_is_reported_without_crashing(self):
        t, e = self.base_row("only-in-truth", "TSK-1", "TSK-1")
        e["job_id"] = "only-in-extracted"
        write_csv(self.truth_path, [t])
        write_csv(self.extracted_path, [e])

        output = run_eval(self.truth_path, self.extracted_path)
        self.assertIn("No overlapping job_ids", output)


if __name__ == "__main__":
    unittest.main()
