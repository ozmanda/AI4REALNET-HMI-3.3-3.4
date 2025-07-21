import os
import sys
import numpy as np
import networkx as nx
from typing import Tuple, List, Dict
from flatland.envs.rail_env import RailEnv


from flatland.envs.rail_env_action import RailEnvActions
from flatland.core.grid.grid4_utils import get_new_position
from flatland.envs.fast_methods import fast_position_equal, fast_argmax, fast_count_nonzero

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.flatland_railway_extension.RailroadSwitchAnalyser import RailroadSwitchAnalyser
from utils.environments.env_small import small_flatland_env
from flatland.envs.rail_env_action import RailEnvActions

n_directions: int = 4  # range [1:infty)
rail_actions: Dict[int, RailEnvActions] = {
    0: "North",
    1: "East",
    2: "South",
    3: "West",
}

class MultiDiGraphBuilder:
    def __init__(self, env: RailEnv):
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self.env: RailEnv = env
        self._init_parameters()
        self._init_switch_analyser()
        self._generate_graph()

    def _init_parameters(self):
        self.height: int = self.env.height
        self.width: int = self.env.width
        self.max_depth: int = self.height * self.width * 10
        self.from_directions: List[int] = [i for i in range(n_directions)]

        self.nodes: Dict[str, Tuple[int, int]] = {}

    def _init_switch_analyser(self):
        """Initialize the switch analyser if needed."""
        self.switch_analyser: RailroadSwitchAnalyser = RailroadSwitchAnalyser(
            self.env,
            handle_diamond_crossing_as_a_switch=True,
            handle_dead_end_as_a_switch=True
        )
        pass

    def _generate_graph(self) -> None:
        for x, y in ((x, y) for x in range(self.height) for y in range(self.width)):
            possible_transitions: Dict[int, List[int]] = {} # range [0,1]
            for direction in self.from_directions:
                possible_transitions[direction] = self.env.rail.get_transitions(*(x, y), direction)
            _, nonzero_directions = self._get_valid_transitions((x, y)) 
            if nonzero_directions:
                start_direction = nonzero_directions[0] 
                start_node = self._find_next_node((x, y), start_direction)
                break

        self._traverse_grid(start_node, start_direction)
    
    
    def _traverse_grid(self, start_node: Tuple[int, int], start_direction: int = 0):
        """Traverse the grid from the start node in the specified direction."""
        self._add_node(start_node)
        self._current_depth: int = 0
        self._node_splitter(start_node, start_direction)


    def _node_splitter(self, node: Tuple[int, int], from_direction: int) -> None:
        """ Splits the nodes, following the valid transitions. """
        self._current_depth += 1
        if self._current_depth > self.max_depth:
            raise ValueError("Maximum depth exceeded while traversing the graph.")
        
        # Get valid transitions from the current node
        _, nonzero_directions = self._get_valid_transitions(node)
        for direction in nonzero_directions:
            if direction == from_direction: # prevents going back to the previous node
                continue
            next_node = self._find_next_node(node, direction)
            if next_node and f'{next_node[0]}_{next_node[1]}' not in self.nodes.keys():
                self._add_node(next_node)
                self._add_edge(node, next_node, key=direction)
                for transition_direction in self.env.rail.get_transitions(*node, direction):
                    self._node_splitter(next_node, from_direction=direction)


    def _find_next_node(self, previous_position: Tuple[int, int], from_direction: int) -> Tuple[int, int]:
        """
        Find the next node in the graph based on the current position and direction of traversal.
        """
        # first transition to new cell
        n_transitions = 1
        depth = 0
        current_position = get_new_position(previous_position, from_direction)
        
        while n_transitions == 1:
            transitions: Tuple = self.env.rail.get_transitions(*current_position, from_direction)
            n_transitions: int = fast_count_nonzero(transitions)
            if n_transitions == 0:
                break
            elif n_transitions > 1:
                return current_position
            else:
                next_position: Tuple = get_new_position(current_position, transitions.index(1))
                depth += 1
                current_position = next_position

            if depth > self.max_depth:
                raise ValueError("Maximum depth exceeded while finding next node.")
            

    def _get_valid_transitions(self, position: Tuple[int, int]) -> List[int]:
        """ 
        Get valid transition directions from the current position.
          - valid_transitions: List indicating if a transition is valid (1) or not (0), for each direction / orientation, [North, East, South, West].
          - nonzero_transitions: List of indices where valid transitions are found, where: 0 = North, 1 = East, 2 = South, 3 = West.
        """
        valid_transitions = [0] * 4 
        for direction in self.from_directions:
            transitions: List = list(self.env.rail.get_transitions(*position, direction))
            valid_transitions = [a or b for a, b in zip(valid_transitions, transitions)]
        nonzero_transitions = [i for i, val in enumerate(valid_transitions) if val != 0]
        return valid_transitions, nonzero_transitions


    def _add_node(self, node_position: Tuple[int, int]):
        """Add a node to the graph."""
        node_id: str = f"{node_position[0]}_{node_position[1]}"
        self.nodes[node_id] = node_position
        self.graph.add_node(node_id, position=node_position)


    def _add_edge(self, u: Tuple[int, int], v: Tuple[int, int], key=None, **attr):
        """Add an edge to the graph."""
        self.graph.add_edge(u, v, key=key, **attr)

    def get_graph(self):
        """Return the constructed graph."""
        return self.graph

    def clear(self):
        """Clear the graph."""
        self.graph.clear()


if __name__ == "__main__":
    # Example usage
    from flatland.envs.rail_env import RailEnv

    # Assuming you have a RailEnv instance
    env: RailEnv = small_flatland_env()
    _ = env.reset()
    graph_builder = MultiDiGraphBuilder(env)