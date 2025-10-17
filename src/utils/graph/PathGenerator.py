import heapq
import itertools

import numpy as np
import networkx as nx

from itertools import islice, product
from typing import Tuple, Dict, List, Union, Any, Callable, Optional
from flatland.envs.agent_utils import EnvAgent

class PathGenerator:
    def __init__(self, graph: nx.MultiDiGraph, station_lookup: Dict[Tuple[int, int], Union[str, int]], k: int = 4, weight: str = 'length', weight_goal: str = 'min'):
        self.k = k
        self.graph = graph
        self.weight = weight
        self.station_lookup = station_lookup
        self._init_digraph(weight_goal)

    def _init_digraph(self, weight_goal: str): 
        self.digraph = nx.DiGraph()
        for u, v, data in self.graph.edges(data=True):
            weight = data['attr'].get(self.weight)
            if self.digraph.has_edge(u, v):
                if weight_goal == 'min':
                    if self.digraph[u][v]['attr'].get(self.weight) > weight:
                        self.digraph[u][v]['attr'][self.weight] = weight

                elif weight_goal == 'max':
                    if self.digraph[u][v]['attr'].get(self.weight) < weight:
                        self.digraph[u][v]['attr'][self.weight] = weight

                else:
                    raise ValueError(f'Incompatible weight goals: {weight_goal}, choose either "max" or "min"')
            else:
                self.digraph.add_edge(u, v, **data)

    def get_k_shortest_paths(self):
        """
        Get the k-shortest paths between each every station-pair.
        """
        # TODO: more efficient way to save this data?
        station_nodes = self.station_lookup.keys()
        self.path_lookup: Dict[Tuple[Tuple[int, int], Tuple[int, int]], List[str]] = {}
        self.paths: Dict[str, List] = {}  # Dictionary of path IDs to paths
        for source_node in station_nodes:
            for target_node in station_nodes:
                print(f'Calculating paths from {source_node} to {target_node}...')
                if source_node != target_node:
                    for k, path in enumerate(self._yen_k_shortest_paths(source_node, target_node, self.k, weight=self.weight)):
                        pathID = (source_node, target_node, k)
                        self.paths[pathID] = path
                        if (source_node, target_node) not in self.path_lookup.keys():
                            self.path_lookup[(source_node, target_node)] = [pathID]
                        else:
                            self.path_lookup[(source_node, target_node)].append(pathID)

        return self.path_lookup, self.paths


    def _get_k_shortest_paths(self, source_node: Tuple[int, int], target_node: Tuple[int, int], 
                              k: int, weight: int = None) -> List[List[Tuple[int, int, int]]]:
        """
        Find the k shortest paths in the graph - MultiDiGraph is not implemented yet, using DiGraph instead -> requires some helper
        functions to manage nodes connected by multiple edges. 

        :param source_node: The starting node.
        :param target_node: The target node.
        :param k: The number of shortest paths to find.
        :param weight: The name of the edge attribute to consider for the paths
        """
        node_paths = self._yen_k_shortest_paths(source_node, target_node, k, weight)
        k_shortest_edge_paths = self._multidigraph_correction(node_paths, weight=weight)
        return k_shortest_edge_paths

    def _yen_k_shortest_paths(self,
                              source_node: Tuple[int, int],
                              target_node: Tuple[int, int],
                              k: int,
                              weight: Optional[str]) -> List[List[Tuple[int, int]]]:
        if source_node == target_node:
            return [[source_node]]

        try:
            first_path = self._shortest_path(self.digraph, source_node, target_node, weight)
        except nx.NetworkXNoPath:
            return []

        if not first_path:
            return []

        shortest_paths: List[List[Tuple[int, int]]] = [first_path]
        candidates: List[Tuple[float, List[Tuple[int, int]]]] = []
        candidates_seen: set = set()

        for _ in range(1, k):
            last_path = shortest_paths[-1]
            for spur_index in range(len(last_path) - 1):
                spur_node = last_path[spur_index]
                root_path = last_path[:spur_index + 1]

                graph_copy = self.digraph.copy()

                for path in shortest_paths:
                    if path[:spur_index + 1] == root_path and spur_index + 1 < len(path):
                        u = path[spur_index]
                        v = path[spur_index + 1]
                        if graph_copy.has_edge(u, v):
                            graph_copy.remove_edge(u, v)

                for node in root_path[:-1]:
                    if graph_copy.has_node(node):
                        graph_copy.remove_node(node)

                try:
                    spur_path = self._shortest_path(graph_copy, spur_node, target_node, weight)
                except nx.NetworkXNoPath:
                    spur_path = None

                if spur_path:
                    total_path = root_path[:-1] + spur_path
                    path_key = tuple(total_path)
                    if path_key in candidates_seen:
                        continue

                    total_cost = self._path_cost(total_path, weight)
                    heapq.heappush(candidates, (total_cost, total_path))
                    candidates_seen.add(path_key)

            if not candidates:
                break

            _, next_path = heapq.heappop(candidates)
            shortest_paths.append(next_path)

        return shortest_paths

    def _shortest_path(self, graph: nx.DiGraph,
                        source: Tuple[int, int],
                        target: Tuple[int, int],
                        weight: Optional[str]) -> List[Tuple[int, int]]:
        weight_fn = self._build_weight_function(weight)
        return nx.shortest_path(graph, source, target, weight=weight_fn)

    def _build_weight_function(self, weight: Optional[str]) -> Optional[Callable[[Any, Any, Dict[str, Any]], float]]:
        if weight is None:
            return None

        def weight_function(u, v, data):
            return self._edge_weight(data, weight)

        return weight_function

    def _edge_weight(self, data: Dict[str, Any], weight: str) -> float:
        if not weight:
            return 1.0
        attr = data.get('attr', {})
        value = attr.get(weight, data.get(weight))
        if value is None:
            return 1.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 1.0

    def _path_cost(self, path: List[Tuple[int, int]], weight: Optional[str]) -> float:
        if len(path) < 2:
            return 0.0
        total_cost = 0.0
        for u, v in zip(path[:-1], path[1:]):
            data = self.digraph.get_edge_data(u, v)
            if data is None:
                continue
            total_cost += self._edge_weight(data, weight) if weight else 1.0
        return total_cost



    def _multidigraph_correction(self, node_paths: List[List[Tuple[int, int]]], weight: str = None) -> List[List[Tuple[int, int, int]]]:
        """
        Translate DiGraph node paths to MultiDiGraph edge paths. 
        """
        heap = [] # max-heap of size k storing (-total_weight, edge_path)
        for path in node_paths:
            edge_options_per_step: List = []
            for u, v in zip(path[:-1], path[1:]):
                edges = [(u, v, key) for key in self.graph[u][v].keys()]
                edge_options_per_step.append(edges)
            
            for combination in itertools.product(*edge_options_per_step):
                total_weight = sum(self.graph[u][v][key]['attr'][weight] for u, v, key in combination)
    
                # push into heap
                if len(heap) < self.k:
                    heapq.heappush(heap, (-total_weight, combination))
                else:
                    # only keep if better than current worst
                    if -heap[0][0] > total_weight:
                        heapq.heapreplace(heap, (-total_weight, combination))

        # extract paths from heap
        k_shortest_edge_paths: List[List[Tuple[int, int, int]]] = [path for _, path in sorted(heap, key=lambda x: -x[0])]
        return k_shortest_edge_paths


    def get_conflict_matrix(self, paths: Dict[str, List]) -> np.ndarray:
        """
        Identify conflicts in the graph based on overlapping paths. Method: if any of the subpaths include the same node,
        a conflict is detected.
        """
        self.path_conflict_matrix = np.zeros((len(paths), len(paths)))
        for i, path in enumerate(paths):
            for j, other_path in enumerate(paths):
                if i != j and set(path) & set(other_path):
                    self.path_conflict_matrix[i, j] = 1
        return self.path_conflict_matrix
    

    def _edge_occupation_time(self, edge: Tuple[Tuple[int, int], Tuple[int, int], int], agent: EnvAgent):
        """
        Determine the time an agent occupies a specific edge.
        """
        pass

    def _node_occupation_time(self, node: Tuple[int, int], agent: EnvAgent):
        """
        Determine the time an agent occupies a specific node.
        """
        pass

