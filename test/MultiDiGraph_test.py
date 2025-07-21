import unittest
from typing import List

from src.utils.flatland_railway_extension.MultiDiGraphBuilder import MultiDiGraphBuilder
from src.utils.environments.scenario_loader import load_scenario_from_json
from src.utils.environments.env_small import small_flatland_env


scenarios: List[str] = ['simple_avoidance',
                        'simple_ordering',
                        'overtaking', 
                        'complex_ordering']

class TestMultiDiGraphBuilder(unittest.TestCase):
    def setUp(self): 
        self.env = small_flatland_env()

    def test_graph_generation(self):
        """ Test the graph generation for one scenario. """
        self.env.reset()
        graph_builder = MultiDiGraphBuilder(self.env)
        self.assertIsNotNone(graph_builder.graph, "Graph should be generated successfully.")
        self.assertGreater(len(graph_builder.graph.nodes), 0, "Graph should contain nodes.")
        self.assertGreater(len(graph_builder.graph.edges), 0, "Graph should contain edges.")

    def test_graph_generation_for_scenarios(self):
        """ Test the graph generation for multiple scenarios. """
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                env = load_scenario_from_json(scenario)
                env.reset()
                graph_builder = MultiDiGraphBuilder(env)
                self.assertIsNotNone(graph_builder.graph, f"Graph for {scenario} should be generated successfully.")
                self.assertGreater(len(graph_builder.graph.nodes), 0, f"Graph for {scenario} should contain nodes.")
                self.assertGreater(len(graph_builder.graph.edges), 0, f"Graph for {scenario} should contain edges.")

    