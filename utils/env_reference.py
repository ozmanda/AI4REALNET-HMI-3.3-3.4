from flatland.envs.rail_env import RailEnv
from typing import NamedTuple, List

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
        """Get the agent handles from the current environment."""
        

    def get_environment_info(self) -> dict:
        """Get information about the current environment."""
        if self.env:
            return {'info 1': 'value1', 'info 2': 'value2'}  # Example info, replace with actual logic
        return {}

    def get_metrics(self) -> dict:
        """Get evaluation metrics from the current environment."""
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
    
    def init_environment(self, env: RailEnv = None):
        if not self.env:
            self.env = env 
        state, info = self.env.reset()
        self.state = state
        self.info = info
        self.transitions: List[Transition] = []

    def get_agent_handles(self):
        """Get the agent handles from the Flatland environment."""
        if self.env:
                return self.env.get_agent_handles()
        return []
    
    def get_environment_info(self) -> dict:
        """Get information about the Flatland environment."""
        if self.env:
            return {'info 1': 'value1', 'info 2': 'value2'}  # Example info, replace with actual logic
        return {}
    
    def get_metrics(self) -> dict:
        """Get evaluation metrics from the Flatland environment."""
        if self.env:
            metrics = {}
            metrics['total_agents'] = len(self.env.agents)
            rewards = self.env.rewards_dict.values()
            avg_reward = sum(rewards) / len(rewards) if rewards else 0
            metrics['average_agent_reward'] = avg_reward
            metrics['total_steps'] = self.env._elapsed_steps
            return metrics
        return {}
    

    def step_environment(self, action_dict):
        """Step the Flatland environment with the given action dictionary."""
        if self.env:
            next_state, rewards, dones, infos = self.env.step(action_dict)
            transition = Transition(
                state=self.env.get_state(),
                action=action_dict,
                reward=rewards,
                next_state=next_state,
                done=dones
            )
            self.transitions.append(transition)
            return 
        return None
    
    
    def reset_environment(self):
        """Reset the Flatland environment."""
        if self.env:
            self.state, self.info = self.env.reset()
            self.transitions.clear()
            return self.state, self.info
        return None, None