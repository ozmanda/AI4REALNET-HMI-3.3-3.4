import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.utils.environments.scenario_loader import load_scenario_from_json
from src.utils.graph.ConflictPredictor import ConflictPredictor
from src.utils.environments.env_small import small_flatland_env

SCENARIO_PATH = os.path.join(
    BASE_DIR,
    "src",
    "utils",
    "environments",
    "simple_avoidance.json",
)


class TestConflictPredictor(unittest.TestCase):
    def setUp(self):
        self.env = load_scenario_from_json(SCENARIO_PATH)
        self.env.reset()
        self.predictor = ConflictPredictor(self.env)

    def test_default_paths_conflict(self):
        matrix = self.predictor.conflict_matrix()
        self.assertGreaterEqual(len(matrix), 2)
        self.assertEqual(matrix[0][1], 1)
        self.assertTrue(self.predictor.detected_conflicts)

    def test_alternate_path_resolves_conflict(self):
        self.predictor.select_agent_path(1, 1)
        matrix = self.predictor.conflict_matrix()
        self.assertGreaterEqual(len(matrix), 2)
        self.assertEqual(matrix[0][1], 0)
        self.assertFalse(self.predictor.detected_conflicts)

    def test_complex_environment(self):
        env = small_flatland_env(malfunctions=False)
        env.reset()
        predictor = ConflictPredictor(env)
        matrix = predictor.conflict_matrix()
        self.assertIsInstance(matrix, list)


if __name__ == "__main__":
    unittest.main()
