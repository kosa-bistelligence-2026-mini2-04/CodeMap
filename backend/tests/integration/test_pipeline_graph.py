import unittest

from app.pipeline.graph import AnalysisPipelineSupervisor


class PipelineGraphContractTests(unittest.TestCase):
    def test_workflow_contains_the_documented_order(self):
        graph = AnalysisPipelineSupervisor().work_flow.get_graph()
        edges = {(edge.source, edge.target) for edge in graph.edges}
        expected = {
            ("__start__", "clone"),
            ("clone", "code_map"),
            ("code_map", "doc_gen"),
            ("doc_gen", "onboarding"),
            ("onboarding", "report"),
            ("report", "__end__"),
        }
        self.assertTrue(expected.issubset(edges))

    def test_each_processing_node_has_a_failure_exit(self):
        graph = AnalysisPipelineSupervisor().work_flow.get_graph()
        edges = {(edge.source, edge.target) for edge in graph.edges}
        for node in ("clone", "code_map", "doc_gen", "onboarding"):
            self.assertIn((node, "__end__"), edges)
