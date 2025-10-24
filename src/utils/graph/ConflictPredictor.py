from typing import Tuple, Dict, Any, Union, List, Optional
from flatland.envs.rail_env import RailEnv
from flatland.envs.agent_utils import EnvAgent
from .MultiDiGraphBuilder import MultiDiGraphBuilder



class ConflictPredictor(): 
    """
    Class that predicts conflicts in a railway environment using its MultiDiGraph representation.
    """
    def __init__(self, env: RailEnv):
        """
        Initialize the ConflictPredictor with a given environment.

        Parameters:
            - env: RailEnv, the railway environment to analyze
        """
        self.env = env
        self.graph = MultiDiGraphBuilder(env)
        self.agent_paths: Dict[int, Dict[str, Any]] = {}
        self.agent_schedules: Dict[int, List[Dict[str, Any]]] = {}
        self.detected_conflicts: List[Dict[str, Any]] = []
        self.agent_index: Dict[int, int] = {}
        self.agent_conflict_matrix: List[List[int]] = []
        self._latest_conflict_detail: Optional[Dict[str, Any]] = None
        self.agent_path_selection: Dict[int, int] = {}
        self.agent_delay_offsets: Dict[int, float] = {}
        self._precompute_station_paths()
        self._init_conflict_predictor()
        self._assign_agent_paths()

    def _init_conflict_predictor(self):
        self.agent_schedules.clear()
        self.detected_conflicts = []
        self.agent_conflict_matrix = []
        self._latest_conflict_detail = None
        self.agent_paths = {}
        self._place_agents()
        self._match_edges()

    def update_agents(self, agents: Optional[List[EnvAgent]] = None) -> None: 
        """ Update agent positions and re-calculate their origin nodes and rail IDs. """
        self._place_agents()
        self._match_edges()
        self._assign_agent_paths()

    def _place_agents(self):
        for agent_handle in self.env.get_agent_handles():
            agent = self.env.agents[agent_handle]
            if agent.position is not None:
                position: Tuple[int, int] = agent.position
            else: 
                position: Tuple[int, int] = agent.initial_position

            # get initial origin node
            self._get_origin_node(position, agent_handle)

            if self.graph.rail_clusters[position[0], position[1]] > 0: 
                self.env.agents[agent_handle].rail_ID = self.graph.rail_clusters[position[0], position[1]]
            elif self.graph.switch_clusters[position[0], position[1]] > 0:
                self.env.agents[agent_handle].rail_ID = self.graph.switch_clusters[position[0], position[1]]
            else: 
                raise ValueError(f"Agent {agent_handle} is not placed on a valid rail or switch.")
            
            
    def _match_edges(self) -> None:
        """ Match edges in the graph to the agents' rail IDs. """
        for agent_handle in self.env.get_agent_handles():
            rail_ID = self.env.agents[agent_handle].rail_ID
            if rail_ID is not None:
                for u, v, data in self.graph.graph.edges(data=True):
                    if data.get('rail_ID') == rail_ID:
                        self.env.agents[agent_handle].rail_edge = (u, v)
                        break


    def _get_origin_node(self, position: Tuple[int, int], agent_handle: Union[int, str]) -> None: 
        """ Add the agent's origin node. """
        agent = self.env.agents[agent_handle]
        if position in self.graph.graph.nodes:
            node_attr = self.graph.graph.nodes[position]
            agent.origin_node = position
            agent.origin_station_id = node_attr.get('station_ID')
            return

        # Fall back to searching edges whose resources include the position.
        for u, v, data in self.graph.graph.edges(data=True):
            attr = data.get('attr', {})
            resources = attr.get('resources', [])
            if any(res_pos == position for res_pos, _ in resources):
                agent.origin_node = u
                agent.origin_station_id = self.graph.graph.nodes[u].get('station_ID')
                agent.origin_edge = (u, v)
                return

        raise ValueError(f"Unable to match agent {agent_handle} position {position} to a graph node or edge.")


    def _precompute_station_paths(self) -> None:
        """Compute k-shortest paths between all station pairs independent of agents."""
        self.graph.station_path_data()
        self.station_path_lookup: Dict[Tuple[Tuple[int, int], Tuple[int, int]], List[str]] = getattr(self.graph, "path_lookup", {})
        self.station_paths: Dict[str, List[Tuple[int, int, int]]] = getattr(self.graph, "paths", {})

    def _assign_agent_paths(self) -> None:
        """Assign default paths to the agents based on the precomputed station paths."""
        self.agent_paths = {}
        for agent_handle in self.env.get_agent_handles():
            agent = self.env.agents[agent_handle]
            station_pair = self._determine_agent_stations(agent)
            if not station_pair:
                continue

            start_node, target_node = station_pair
            path_candidates = self.station_path_lookup.get((start_node, target_node))
            if not path_candidates:
                continue

            selected_index = self.agent_path_selection.get(agent_handle, 0)
            if selected_index < 0 or selected_index >= len(path_candidates):
                selected_index = 0

            chosen_path_id = path_candidates[selected_index]
            edges = self.station_paths.get(chosen_path_id)
            if edges is None:
                continue
            self.agent_paths[agent_handle] = {
                "path_id": chosen_path_id,
                "available_paths": path_candidates,
                "selected_path_index": selected_index,
                "edges": edges,
                "start": start_node,
                "target": target_node,
            }
            self.agent_schedules.pop(agent_handle, None)

    def _determine_agent_stations(self, agent: EnvAgent) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Determine the start and target station nodes for an agent."""
        start_position = None
        target_position = None

        if getattr(agent, "waypoints", None):
            if agent.waypoints:
                start_position = self._extract_waypoint_position(agent.waypoints[0])
                target_position = self._extract_waypoint_position(agent.waypoints[-1])

        if start_position is None:
            start_position = agent.initial_position or agent.position
        if target_position is None:
            target_position = getattr(agent, "target", None)

        start_node = self._resolve_station_node(start_position)
        target_node = self._resolve_station_node(target_position)

        if start_node is None or target_node is None:
            return None
        return start_node, target_node

    def _resolve_station_node(self, position: Optional[Union[Tuple[int, int], List[int]]]) -> Optional[Tuple[int, int]]:
        if position is None:
            return None
        if isinstance(position, list):
            position = tuple(position)
        if isinstance(position, tuple):
            if position in getattr(self.graph, "station_lookup", {}):
                return position
            # Fallback: if agent is currently on a graph node that maps to a station
            station_id = getattr(self.env, "stations", None)
            if station_id:
                for station in station_id:
                    coord = (station["r"], station["c"])
                    if coord == position:
                        return coord
        return None

    def _get_available_paths_for_agent(self, agent_handle: int) -> List[str]:
        agent = self.env.agents[agent_handle]
        station_pair = self._determine_agent_stations(agent)
        if not station_pair:
            return []
        start_node, target_node = station_pair
        return self.station_path_lookup.get((start_node, target_node), [])

    def get_available_paths(self, agent_handle: int) -> List[str]:
        """Return the list of path identifiers available to the given agent."""
        return list(self._get_available_paths_for_agent(agent_handle))

    def path_cells(self, path_id: str) -> List[Tuple[int, int]]:
        edges = self.station_paths.get(path_id)
        if edges is None:
            return []
        cells: List[Tuple[int, int]] = []
        for idx, edge in enumerate(edges):
            u, v, key = edge
            if idx == 0:
                cells.append(u)
            attr = self.graph.graph[u][v][key]["attr"]
            resources = attr.get("resources", [])
            for cell, _ in resources:
                if not cells or cells[-1] != cell:
                    cells.append(cell)
            if not cells or cells[-1] != v:
                cells.append(v)
        return cells

    def agent_cell_path(self, agent_handle: int) -> List[Tuple[int, int]]:
        path_info = self.agent_paths.get(agent_handle)
        if not path_info:
            return []
        return self.path_cells(path_info["path_id"])

    def get_selected_path_index(self, agent_handle: int) -> int:
        return int(self.agent_path_selection.get(agent_handle, 0))

    def evaluate_selection(
        self,
        overrides: Optional[Dict[int, int]] = None,
        delay_overrides: Optional[Dict[int, float]] = None,
    ) -> Tuple[List[List[int]], List[Dict[str, Any]]]:
        original_selection = dict(self.agent_path_selection)
        original_delays = dict(self.agent_delay_offsets)
        try:
            if overrides:
                self.agent_path_selection.update(overrides)
            if delay_overrides is not None:
                for handle, value in delay_overrides.items():
                    delay = max(0.0, float(value))
                    if delay > 0:
                        self.agent_delay_offsets[handle] = delay
                    else:
                        self.agent_delay_offsets.pop(handle, None)
                    self.agent_schedules.pop(handle, None)
            matrix = self.conflict_matrix()
            conflicts = list(self.detected_conflicts)
            return matrix, conflicts
        finally:
            if overrides is not None or delay_overrides is not None:
                self.agent_path_selection = original_selection
                self.agent_delay_offsets = original_delays
                self._assign_agent_paths()
                self.conflict_matrix()


    def cell_time_window(self, cell: Tuple[int, int], train_speed: float) -> Tuple[float, float]:
        """
        Calculate the time window for a given cell based on the train's speed.

        Parameters:
            - cell: Tuple[int, int], the cell coordinates (x, y)
            - train_speed: float, the speed of the train

        Returns:
            - Tuple[float, float]: the time window (start_time, end_time)   
        """
        if train_speed is None or train_speed <= 0:
            raise ValueError("Train speed must be a positive value to compute a time window.")
        duration = 1.0 / train_speed
        return (0.0, duration)

    
    def edge_time_window(self, edge: Tuple[Any, Any], train_speed: float) -> Tuple[int, int]:
        """
        Calculate the time window for a given edge based on the train's speed.

        Parameters:
            - edge: Tuple[Any, Any], the edge represented by its two nodes (u, v)
            - train_speed: float, the speed of the train

        Returns:
            - Tuple[int, int]: the time window (start_time, end_time)
        """
        duration = self._edge_travel_time(edge, train_speed)
        return (0.0, duration)


    def path_time_windows(self, path: list, train_speed: float) -> List[Tuple[int, int]]:
        """
        Calculate the time windows for a given path based on the train's speed.

        Parameters:
            - path: list, the sequence of nodes representing the path
            - train_speed: float, the speed of the train

        Returns:
            - List[Tuple[int, int]]: the list of time windows (start_time, end_time) for each segment of the path
        """
        windows: List[Tuple[int, int]] = []
        current_time = 0.0
        for edge in path:
            _, edge_duration = self.edge_time_window(edge, train_speed)
            start_time = current_time
            current_time += edge_duration
            windows.append((start_time, current_time))
        return windows

    
    def _calculate_conflict_time(self, path_A: List[Tuple[int, int]], path_B: List[Tuple[int, int]],
                                 speed_A: float, speed_B: float, t_A: float, t_B: float) -> bool:
        """
        Determine whether two agents with planned paths A and B, speeds s_A, s_B and departure times 
        t_A and t_B will conflict on overlapping paths.
        """
        schedule_A = self._build_resource_schedule(path_A, speed_A, t_A)
        schedule_B = self._build_resource_schedule(path_B, speed_B, t_B)
        conflict_detail = self._schedules_conflict(schedule_A, schedule_B)
        if conflict_detail:
            conflict_detail.update({
                'schedule_A': schedule_A,
                'schedule_B': schedule_B,
                'speed_A': speed_A,
                'speed_B': speed_B,
                'departure_A': t_A,
                'departure_B': t_B,
            })
            self._latest_conflict_detail = conflict_detail
            return True

        self._latest_conflict_detail = None
        return False


    def conflict_matrix(self):
        """
        Calculate the conflict matrix for the paths of all station pairs
        """
        self._init_conflict_predictor()
        self._assign_agent_paths()
        agent_handles = list(self.env.get_agent_handles())
        agent_count = len(agent_handles)
        self.agent_index = {handle: idx for idx, handle in enumerate(agent_handles)}
        matrix: List[List[int]] = [[0 for _ in range(agent_count)] for _ in range(agent_count)]
        conflict_records: List[Dict[str, Any]] = []

        for idx_a, handle_a in enumerate(agent_handles):
            path_info_a = self.agent_paths.get(handle_a)
            if not path_info_a:
                continue

            agent_a = self.env.agents[handle_a]
            speed_a = self._get_agent_speed(agent_a)
            departure_a = self._get_departure_time(handle_a, agent_a)
            path_a = path_info_a['edges']

            for idx_b in range(idx_a + 1, agent_count):
                handle_b = agent_handles[idx_b]
                path_info_b = self.agent_paths.get(handle_b)
                if not path_info_b:
                    continue

                agent_b = self.env.agents[handle_b]
                speed_b = self._get_agent_speed(agent_b)
                departure_b = self._get_departure_time(handle_b, agent_b)
                path_b = path_info_b['edges']

                conflict = self._calculate_conflict_time(path_a, path_b, speed_a, speed_b, departure_a, departure_b)
                if conflict:
                    matrix[idx_a][idx_b] = matrix[idx_b][idx_a] = 1
                    detail = dict(self._latest_conflict_detail) if self._latest_conflict_detail else {}
                    if detail:
                        detail.update({
                            'agents': (handle_a, handle_b),
                            'paths': (path_info_a['path_id'], path_info_b['path_id']),
                        })
                        conflict_records.append(detail)

        self.detected_conflicts = conflict_records
        self.agent_conflict_matrix = matrix
        return matrix

    # ---------------------------------------------------------------------
    # Helper functions
    # ---------------------------------------------------------------------
    def select_agent_path(self, agent_handle: int, path_index: int) -> None:
        """
        Override the selected path for a given agent by choosing an alternative from the available paths.
        """
        available_paths = self._get_available_paths_for_agent(agent_handle)
        if not available_paths:
            raise ValueError(f"Agent {agent_handle} has no available paths to choose from.")

        if path_index < 0 or path_index >= len(available_paths):
            raise IndexError(f"Path index {path_index} is out of range for agent {agent_handle}.")

        self.agent_path_selection[agent_handle] = path_index
        self._assign_agent_paths()
        if agent_handle not in self.agent_paths:
            raise ValueError(f"Failed to assign selected path for agent {agent_handle}.")
        self.agent_schedules.pop(agent_handle, None)

    def set_agent_delay(self, agent_handle: int, delay_steps: float) -> None:
        delay = max(0.0, float(delay_steps))
        if delay <= 0:
            self.agent_delay_offsets.pop(agent_handle, None)
        else:
            self.agent_delay_offsets[agent_handle] = delay
        self.agent_schedules.pop(agent_handle, None)

    def clear_agent_delay(self, agent_handle: int) -> None:
        if agent_handle in self.agent_delay_offsets:
            self.agent_delay_offsets.pop(agent_handle, None)
            self.agent_schedules.pop(agent_handle, None)

    def _extract_waypoint_position(self, waypoint_entry: Any) -> Tuple[int, int]:
        waypoint = waypoint_entry
        if isinstance(waypoint_entry, (list, tuple)) and waypoint_entry:
            waypoint = waypoint_entry[0]
        position = getattr(waypoint, 'position', waypoint)
        return tuple(position)

    def _get_agent_speed(self, agent) -> float:
        speed = getattr(agent.speed_counter, 'speed', None)
        if speed is None or speed <= 0:
            speed = getattr(agent.speed_counter, 'max_speed', 1.0)
        return float(speed if speed and speed > 0 else 1.0)

    def _get_departure_time(self, agent_handle: int, agent) -> float:
        departures = getattr(agent, 'waypoints_earliest_departure', None)
        base = 0.0
        if departures:
            for value in departures:
                if value is not None:
                    base = float(value)
                    break
        delay = float(self.agent_delay_offsets.get(agent_handle, 0.0))
        return base + delay

    def _build_resource_schedule(self, path: List[Tuple[Any, Any, Any]],
                                 train_speed: float,
                                 departure_time: float) -> List[Dict[str, Any]]:
        schedule: List[Dict[str, Any]] = []
        if train_speed <= 0:
            return schedule
        current_time = float(departure_time if departure_time is not None else 0.0)

        for edge in path:
            travel_time = self._edge_travel_time(edge, train_speed)
            if travel_time <= 0:
                continue
            u, v, key = edge
            attr = self.graph.graph[u][v][key]['attr']
            resource_id = self._edge_resource_id(edge, attr)
            entry = {
                'edge': edge,
                'resource_id': resource_id,
                'start': current_time,
                'end': current_time + travel_time,
            }
            schedule.append(entry)
            current_time += travel_time

        return schedule

    def _schedules_conflict(self,
                            schedule_A: List[Dict[str, Any]],
                            schedule_B: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for entry_A in schedule_A:
            resource_A = entry_A.get('resource_id')
            if resource_A is None:
                continue
            start_A, end_A = entry_A['start'], entry_A['end']
            for entry_B in schedule_B:
                if resource_A != entry_B.get('resource_id'):
                    continue
                start_B, end_B = entry_B['start'], entry_B['end']
                if start_A < end_B and start_B < end_A:
                    return {
                        'resource_id': resource_A,
                        'interval_A': (start_A, end_A),
                        'interval_B': (start_B, end_B),
                        'edge_A': entry_A['edge'],
                        'edge_B': entry_B['edge'],
                    }
        return None

    def _edge_travel_time(self, edge: Tuple[Any, Any, Any], train_speed: float) -> float:
        if train_speed <= 0:
            raise ValueError("Train speed must be positive.")
        u, v, key = edge
        attr = self.graph.graph[u][v][key]['attr']
        length = attr.get('length')
        if length is None or length <= 0:
            length = len(attr.get('resources', []))
        if length <= 0:
            length = 1
        return length / train_speed

    def _edge_resource_id(self, edge: Tuple[Any, Any, Any], attr: Dict[str, Any]) -> Any:
        resources = attr.get('resources')
        if resources:
            resource_cells = frozenset(pos for pos, _ in resources)
            if resource_cells:
                return ('cells', resource_cells)
        rail_id = attr.get('rail_ID')
        if rail_id is not None:
            return ('rail', int(rail_id))
        u, v, key = edge
        undirected = frozenset({u, v})
        return ('edge', undirected, key)
