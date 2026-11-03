import csv
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import eval_extraction


TRUTH_ROWS = [
    {"job_id": "JC-1", "vin_id": "VIN1", "task_number": "TSK-1",
     "part_number_removed": "BRK-A1-1000", "serial_number_removed": "SN-BRK-00000001",
     "part_number_installed": "", "serial_number_installed": ""},
    {"job_id": "JC-2", "vin_id": "VIN2", "task_number": "",
     "part_number_removed": "", "serial_number_removed": "",
     "part_number_installed": "", "serial_number_installed": ""},
    {"job_id": "JC-3", "vin_id": "VIN3", "task_number": "TSK-3",
     "part_number_removed": "", "serial_number_removed": "",
     "part_number_installed": "", "serial_number_installed": ""},
]

# JC-1: task_number matches exactly (case/whitespace-insensitive) -> correct
# JC-2: truth blank, extracted has a value -> hallucinated
# JC-3: truth has a value, extracted blank -> missed
EXTRACTED_ROWS = [
    {"job_id": "JC-1", "vin_id": "VIN1", "task_number": " tsk-1 ",
     "part_number_removed": "BRK-A1-1000", "serial_number_removed": "SN-BRK-00000001",
     "part_number_installed": "", "serial_number_installed": ""},
    {"job_id": "JC-2", "vin_id": "VIN2", "task_number": "TSK-999",
     "part_number_removed": "", "serial_number_removed": "",
     "part_number_installed": "", "serial_number_installed": ""},
    {"job_id": "JC-3", "vin_id": "VIN3", "task_number": "",
     "part_number_removed": "", "serial_number_removed": "",
     "part_number_installed": "", "serial_number_installed": ""},
]


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


class NormTest(unittest.TestCase):
    def test_none_becomes_empty_string(self):
        self.assertEqual(eval_extraction.norm(None), "")

    def test_strips_whitespace_and_lowercases(self):
        self.assertEqual(eval_extraction.norm("  TSK-123  "), "tsk-123")


class MainScoringTest(unittest.TestCase):
    def run_eval(self, truth_rows, extracted_rows):
        with tempfile.TemporaryDirectory() as tmp:
            truth_path = Path(tmp) / "truth.csv"
            extracted_path = Path(tmp) / "extracted.csv"
            write_csv(truth_path, truth_rows)
            write_csv(extracted_path, extracted_rows)

            argv = sys.argv
            sys.argv = ["eval_extraction.py", "--extracted", str(extracted_path), "--truth", str(truth_path)]
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    eval_extraction.main()
            finally:
                sys.argv = argv
            return buf.getvalue()

    def test_counts_correct_hallucinated_and_missed(self):
        output = self.run_eval(TRUTH_ROWS, EXTRACTED_ROWS)
        lines = {line.split()[0]: line for line in output.splitlines() if line.startswith("task_number")}
        task_line = lines["task_number"]
        # 1 of 3 correct, 1 of 3 hallucinated, 1 of 3 missed
        self.assertIn("33.3%", task_line)
        self.assertEqual(task_line.count("33.3%"), 3)

    def test_field_with_no_mentions_is_all_correct(self):
        output = self.run_eval(TRUTH_ROWS, EXTRACTED_ROWS)
        part_installed_line = next(
            line for line in output.splitlines() if line.startswith("part_number_installed")
        )
        self.assertIn("100.0%", part_installed_line)

    def test_no_overlapping_job_ids_prints_message(self):
        other_truth = [{**row, "job_id": row["job_id"] + "-X"} for row in TRUTH_ROWS]
        output = self.run_eval(other_truth, EXTRACTED_ROWS)
        self.assertIn("No overlapping job_ids", output)


if __name__ == "__main__":
    unittest.main()
