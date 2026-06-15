from __future__ import annotations

import unittest

from training.visual_status import ga_status_from_progress


class GAVisualStatusTests(unittest.TestCase):
    def test_generation_summary_shows_current_generation(self):
        status = ga_status_from_progress(
            "Generation 003/020: best=12.345 avg=6.789 overall_best=12.345"
        )

        self.assertIsNotNone(status)
        self.assertEqual("GA Training", status.title)
        self.assertEqual("第 3 代 / 共 20 代", status.primary)
        self.assertIn("best=12.345", status.secondary)

    def test_evaluation_progress_shows_current_generation(self):
        status = ga_status_from_progress("Evaluating generation 004/020 (30 genomes)")

        self.assertIsNotNone(status)
        self.assertEqual("第 4 代 / 共 20 代", status.primary)
        self.assertEqual("Evaluating 30 genomes", status.secondary)


if __name__ == "__main__":
    unittest.main()
