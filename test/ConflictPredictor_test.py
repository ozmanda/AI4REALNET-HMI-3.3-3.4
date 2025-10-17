import os
import sys
import unittest
from src.utils.environments.env_small import small_flatland_env 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.utils.environments.scenario_loader import load_scenario_from_json
from src.utils.graph.ConflictPredictor import ConflictPredictor

SCENARIO_PATH = os.path.join(
    BASE_DIR,
    "src",
    "utils",
    "environments",
    "simple_avoidance.json",
)


class TestConflictPredictor(unittest.TestCase):
    def setup_scenario(self):
        self.env = load_scenario_from_json(SCENARIO_PATH)
        self.env.reset()
        self.predictor = ConflictPredictor(self.env)
        
    def setup_simple_env(self): 
        self.env = small_flatland_env()
        self.env.reset()
        self.predictor = ConflictPredictor(self.env)

    def test_default_paths_conflict(self):
        """Agents following their default shortest paths should conflict."""
        self.setup_scenario()
        matrix = self.predictor.conflict_matrix()
        self.assertGreaterEqual(len(matrix), 2)
        self.assertEqual(matrix[0][1], 1)
        self.assertTrue(self.predictor.detected_conflicts)

    def test_complex_environment(self): 
        self.env = small_flatland_env(malfunctions=False)
        self.env.reset()
        self.predictor = ConflictPredictor(self.env)
        matrix = self.predictor.conflict_matrix()
        self.assertIsInstance(matrix, list)

    def test_alternate_path_resolves_conflict(self):
        """Switching one agent to the alternative path should avoid the conflict."""
        self.predictor.select_agent_path(1, 1)
        matrix = self.predictor.conflict_matrix()
        self.assertGreaterEqual(len(matrix), 2)
        self.assertFalse(self.predictor.detected_conflicts)


if __name__ == "__main__":
    unittest.main()
