import json
import unittest
from pathlib import Path

from app.repo.analyzer import search_repository


TEST_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_REPO = TEST_ROOT / "fixtures" / "sample_repo"
CASES_PATH = Path(__file__).with_name("retrieval_cases.jsonl")


class RetrievalQualityBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = [json.loads(line) for line in CASES_PATH.read_text().splitlines() if line.strip()]

    def test_fixture_has_multiple_grounded_questions(self):
        self.assertGreaterEqual(len(self.cases), 3)
        self.assertTrue(all(case["expected_files"] for case in self.cases))

    def test_recall_at_k_meets_baseline(self):
        hits = 0
        for case in self.cases:
            results = search_repository(str(FIXTURE_REPO), case["query"], limit=case["top_k"])
            paths = {result["file"] for result in results}
            if paths.intersection(case["expected_files"]):
                hits += 1
        recall = hits / len(self.cases)
        self.assertGreaterEqual(recall, 1.0)

    def test_mean_reciprocal_rank_meets_baseline(self):
        reciprocal_ranks = []
        for case in self.cases:
            results = search_repository(str(FIXTURE_REPO), case["query"], limit=case["top_k"])
            rank = next(
                (index for index, result in enumerate(results, start=1) if result["file"] in case["expected_files"]),
                None,
            )
            reciprocal_ranks.append(0.0 if rank is None else 1.0 / rank)
        mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
        self.assertGreaterEqual(mrr, 0.75)
