#!/usr/bin/env python3
import unittest

from analyze_part_wear import compute_usage


def row(job_card_id, job_date, vin, odometer_km, part_category,
        serial_installed, install_type="New",
        reused_from_job_card_id="", reused_from_vin=""):
    return {
        "job_card_id": job_card_id,
        "job_date": job_date,
        "vin": vin,
        "odometer_km": str(odometer_km),
        "part_category": part_category,
        "serial_number_installed": serial_installed,
        "install_type": install_type,
        "reused_from_job_card_id": reused_from_job_card_id,
        "reused_from_vin": reused_from_vin,
    }


class ComputeUsageTests(unittest.TestCase):
    def test_first_job_for_vin_category_has_no_interval(self):
        rows = [row("JC-1", "2020-01-01", "VIN-A", 10000, "Battery", "SN-1")]
        intervals, shelf = compute_usage(rows)
        self.assertEqual(intervals, [])
        self.assertEqual(shelf, [])

    def test_consecutive_jobs_same_vin_category_yield_interval(self):
        rows = [
            row("JC-1", "2020-01-01", "VIN-A", 10000, "Battery", "SN-1"),
            row("JC-2", "2021-01-01", "VIN-A", 25000, "Battery", "SN-2"),
        ]
        intervals, _ = compute_usage(rows)
        self.assertEqual(len(intervals), 1)
        rec = intervals[0]
        self.assertEqual(rec["days_in_service"], 366)
        self.assertEqual(rec["km_driven"], 15000)
        self.assertEqual(rec["prev_job_card_id"], "JC-1")
        self.assertEqual(rec["job_card_id"], "JC-2")

    def test_different_category_does_not_pair_with_other_category(self):
        rows = [
            row("JC-1", "2020-01-01", "VIN-A", 10000, "Battery", "SN-1"),
            row("JC-2", "2021-01-01", "VIN-A", 25000, "Alternator", "SN-2"),
        ]
        intervals, _ = compute_usage(rows)
        self.assertEqual(intervals, [])

    def test_different_vin_does_not_pair(self):
        rows = [
            row("JC-1", "2020-01-01", "VIN-A", 10000, "Battery", "SN-1"),
            row("JC-2", "2021-01-01", "VIN-B", 25000, "Battery", "SN-2"),
        ]
        intervals, _ = compute_usage(rows)
        self.assertEqual(intervals, [])

    def test_reuse_shelf_time_uses_source_job_date(self):
        rows = [
            row("JC-1", "2020-01-01", "VIN-A", 10000, "Alternator", "SN-SHARED"),
            row("JC-2", "2020-06-01", "VIN-B", 40000, "Alternator", "SN-SHARED",
                install_type="Reused", reused_from_job_card_id="JC-1", reused_from_vin="VIN-A"),
        ]
        _, shelf = compute_usage(rows)
        self.assertEqual(len(shelf), 1)
        rec = shelf[0]
        self.assertEqual(rec["shelf_days"], 152)
        self.assertEqual(rec["removed_from_vin"], "VIN-A")
        self.assertEqual(rec["installed_on_vin"], "VIN-B")

    def test_reuse_with_missing_source_job_is_skipped(self):
        rows = [
            row("JC-2", "2020-06-01", "VIN-B", 40000, "Alternator", "SN-SHARED",
                install_type="Reused", reused_from_job_card_id="JC-999", reused_from_vin="VIN-A"),
        ]
        _, shelf = compute_usage(rows)
        self.assertEqual(shelf, [])


if __name__ == "__main__":
    unittest.main()
