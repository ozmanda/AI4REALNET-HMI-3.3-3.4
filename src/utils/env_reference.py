import numpy as np
from flatland.envs.rail_env import RailEnv
from typing import NamedTuple, List, Dict, Tuple, Any, Union

import networkx as nx
from networkx import DiGraph
from utils.flatland_railway_extension.RailroadSwitchAnalyser import RailroadSwitchAnalyser
from utils.flatland_railway_extension.RailroadSwitchCluster import RailroadSwitchCluster
from utils.flatland_railway_extension.FlatlandGraphBuilder import FlatlandGraphBuilder

class Transition(NamedTuple):
    state: dict
    action: dict
    reward: float
    next_state: dict
    done: bool

class EnvReference(): 
    """ Central reference for the environment, allows all widgets to refer to the current environment without individual update functions """
    def __init__(self, env: RailEnv = None):
        self.env: RailEnv = env

    def get_agent_handles(self):
        """ Get the agent handles from the current environment. """
        

    def get_environment_info(self) -> dict:
        """ Get information about the current environment. """
        if self.env:
            return {'info 1': 'value1', 'info 2': 'value2'}  # Example info, replace with actual logic
        return {}

    def get_metrics(self) -> Dict[str, Any]:
        """ Get evaluation metrics from the current environment. """
        if self.env:
            metrics = {}
            metrics['total_agents'] = len(self.env.agents)
            rewards = self.env.rewards_dict.values()
            avg_reward = sum(rewards) / len(rewards) if rewards else 0
            metrics['average_agent_reward'] = avg_reward
            metrics['total_steps'] = self.env._elapsed_steps
            return metrics
        return {}
    

class FlatlandEnvReference(EnvReference):
    """ Flatland specific environment reference, inherits from EnvReference """
    def __init__(self, env: RailEnv = None):
        super().__init__(env)
        self.env: RailEnv = env
        self.state: dict = {}
        self.info: dict = {}
        self.next_state: dict = {}
        self.network_graph: Union[DiGraph, None] = None
    
    def init_environment(self, env: RailEnv = None) -> None:
        if not self.env:
            self.env = env 
        state, info = self.env.reset()
        self.state = state
        self.info = info
        self.transitions: List[Transition] = []
        self._init_clusters()
        self._init_network_graph()

    def _init_clusters(self) -> None: 
        """ Initialize the switch and railroad clusters for the Flatland environment. """
        if self.env:
            # Initialize grids for rail and switch clusters
            self.rail_grid: np.ndarray = np.zeros((self.env.height, self.env.width), dtype=np.int8)
            self.switch_grid: np.ndarray = np.zeros((self.env.height, self.env.width), dtype=np.int8)

            self.switch_analyser = RailroadSwitchAnalyser(self.env)
            self.switch_cluster = RailroadSwitchCluster(self.switch_analyser, multi_directional=False)

            for id, positions in self.switch_cluster.connecting_edge_clusters.items():
                for pos in positions:
                    self.rail_grid[pos[0], pos[1]] = id
            
            for id, positions in self.switch_cluster.railroad_switch_clusters.items():
                for pos in positions:
                    self.switch_grid[pos[0], pos[1]] = id


    def _init_network_graph(self) -> None:
        """ Initialize the network graph for the Flatland environment. """
        if self.env:
            graphbuilder = FlatlandGraphBuilder(self.switch_analyser, activate_multi_directional=False)
            self.network_graph = graphbuilder.get_graph()
            # graphbuilder.render() #! Uncomment to visualize the graph

    def get_agent_handles(self) -> List[int | str]:
        """ Get the agent handles from the Flatland environment. """
        if self.env:
                return self.env.get_agent_handles()
        return []
    
    def get_environment_info(self) -> Dict[str, Any]:
        """ Get information about the Flatland environment. """
        if self.env:
            return {'info 1': 'value1', 'info 2': 'value2'}  # Example info, replace with actual logic
        return {}
    
    def get_metrics(self) -> Dict[str, Any]:
        """ Get evaluation metrics from the Flatland environment. """
        if self.env:
            metrics = {}
            metrics['total_agents'] = len(self.env.agents)
            rewards = self.env.rewards_dict.values()
            avg_reward = sum(rewards) / len(rewards) if rewards else 0
            metrics['average_agent_reward'] = avg_reward
            metrics['total_steps'] = self.env._elapsed_steps
            return metrics
        return {}
    

    def step_environment(self, action_dict) -> None:
        """ Step the Flatland environment with the given action dictionary. """
        if self.env:
            next_state, rewards, dones, _ = self.env.step(action_dict)
            transition = Transition(
                state=self.env._get_observations(),
                action=action_dict,
                reward=rewards,
                next_state=next_state,
                done=dones
            )
            self.transitions.append(transition)
    
    
    def reset_environment(self) -> Tuple:
        """ Reset the Flatland environment. """
        if self.env:
            self.state, self.info = self.env.reset()
            self.transitions.clear()
            return self.state, self.info
        return None, None