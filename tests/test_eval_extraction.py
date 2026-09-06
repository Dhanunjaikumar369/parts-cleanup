import csv
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
EVAL_SCRIPT = os.path.join(REPO_ROOT, "eval_extraction.py")

FIELDS = [
    "task_number", "part_number_removed", "serial_number_removed",
    "part_number_installed", "serial_number_installed",
]


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


class EvalExtractionTest(unittest.TestCase):
    def test_accuracy_hallucination_and_miss_rates(self):
        fieldnames = ["job_id", "vin_id"] + FIELDS

        def row(job_id, **values):
            r = {f: "" for f in fieldnames}
            r["job_id"] = job_id
            r["vin_id"] = "VIN1"
            r.update(values)
            return r

        truth_rows = [
            row("JC-1", task_number="TSK-000001"),
            row("JC-2", task_number="TSK-000002"),
            row("JC-3"),  # blank in truth
            row("JC-4"),  # blank in truth
        ]
        extracted_rows = [
            row("JC-1", task_number="TSK-000001"),  # correct match
            row("JC-2", task_number="TSK-999999"),  # wrong value -> counts as a miss (t!="" e!="" e!=t)
            row("JC-3", task_number="TSK-HALLUCINATED"),  # hallucination
            row("JC-4"),  # correct null
        ]

        with tempfile.TemporaryDirectory() as tmp:
            truth_path = os.path.join(tmp, "truth.csv")
            extracted_path = os.path.join(tmp, "extracted.csv")
            write_csv(truth_path, fieldnames, truth_rows)
            write_csv(extracted_path, fieldnames, extracted_rows)

            result = subprocess.run(
                [sys.executable, EVAL_SCRIPT, "--extracted", extracted_path, "--truth", truth_path],
                capture_output=True, text=True, check=True,
            )

        task_line = next(line for line in result.stdout.splitlines() if line.startswith("task_number"))
        parts = task_line.split()
        accuracy, hallucinated, missed = parts[1], parts[2], parts[3]
        self.assertEqual(accuracy, "50.0%")
        self.assertEqual(hallucinated, "25.0%")
        self.assertEqual(missed, "0.0%")

    def test_no_overlapping_job_ids_reports_and_exits_cleanly(self):
        fieldnames = ["job_id", "vin_id"] + FIELDS
        with tempfile.TemporaryDirectory() as tmp:
            truth_path = os.path.join(tmp, "truth.csv")
            extracted_path = os.path.join(tmp, "extracted.csv")
            write_csv(truth_path, fieldnames, [{f: "" for f in fieldnames} | {"job_id": "JC-1", "vin_id": "V"}])
            write_csv(extracted_path, fieldnames, [{f: "" for f in fieldnames} | {"job_id": "JC-2", "vin_id": "V"}])

            result = subprocess.run(
                [sys.executable, EVAL_SCRIPT, "--extracted", extracted_path, "--truth", truth_path],
                capture_output=True, text=True, check=True,
            )
        self.assertIn("No overlapping job_ids", result.stdout)


if __name__ == "__main__":
    unittest.main()
