#!/usr/bin/env python3
"""Unit tests for eval_extraction.py."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval_extraction import norm, score_field


class NormTest(unittest.TestCase):
    def test_none_becomes_empty_string(self):
        self.assertEqual(norm(None), "")

    def test_strips_and_lowercases(self):
        self.assertEqual(norm("  TSK-123456 "), "tsk-123456")

    def test_empty_string_stays_empty(self):
        self.assertEqual(norm(""), "")


class ScoreFieldTest(unittest.TestCase):
    def setUp(self):
        self.truth = {
            "JC-1": {"f": "TSK-1"},
            "JC-2": {"f": ""},
            "JC-3": {"f": "TSK-3"},
            "JC-4": {"f": ""},
        }
        self.extracted = {
            "JC-1": {"f": "tsk-1"},   # correct match (case-insensitive)
            "JC-2": {"f": "TSK-9"},   # hallucinated: truth blank, extracted non-blank
            "JC-3": {"f": ""},        # missed: truth non-blank, extracted blank
            "JC-4": {"f": ""},        # correct null-null match
        }
        self.common = ["JC-1", "JC-2", "JC-3", "JC-4"]

    def test_counts(self):
        correct, hallucinated, missed = score_field("f", self.common, self.truth, self.extracted)
        self.assertEqual(correct, 2)
        self.assertEqual(hallucinated, 1)
        self.assertEqual(missed, 1)

    def test_only_scores_the_given_job_ids(self):
        correct, hallucinated, missed = score_field("f", ["JC-1", "JC-3"], self.truth, self.extracted)
        self.assertEqual((correct, hallucinated, missed), (1, 0, 1))


if __name__ == "__main__":
    unittest.main()
