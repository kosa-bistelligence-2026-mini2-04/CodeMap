import inspect
import unittest

try:
    from app.graph import service as graph_service
    from app.parse import service as parse_service
except ImportError:
    graph_service = None
    parse_service = None


RISK_READY = parse_service is not None and hasattr(parse_service, "detect_risk_signals")
STACK_SCORE_READY = parse_service is not None and hasattr(parse_service, "score_tech_stack")
GRAPH_READY = graph_service is not None and hasattr(graph_service, "build_dependency_graph")


class Phase2RagFunctionContractTests(unittest.TestCase):
    @unittest.skipUnless(RISK_READY, "RAG-PARSE-B-211 위험 신호 태깅은 Phase 2 예정")
    def test_risk_detection_accepts_parsed_files(self):
        self.assertEqual(
            list(inspect.signature(parse_service.detect_risk_signals).parameters),
            ["files"],
        )

    @unittest.skipUnless(STACK_SCORE_READY, "RAG-PARSE-B-212 기술 스택 점수화는 보류")
    def test_stack_scoring_accepts_parsed_files_and_stack(self):
        self.assertEqual(
            list(inspect.signature(parse_service.score_tech_stack).parameters),
            ["files", "tech_stack"],
        )

    @unittest.skipUnless(GRAPH_READY, "RAG-GRAPH-B-201 의존성 그래프는 Phase 2 예정")
    def test_dependency_graph_accepts_parsed_files(self):
        self.assertEqual(
            list(inspect.signature(graph_service.build_dependency_graph).parameters),
            ["files"],
        )
