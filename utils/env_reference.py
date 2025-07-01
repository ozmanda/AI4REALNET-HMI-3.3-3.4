from flatland.envs.rail_env import RailEnv

class EnvReference(): 
    """ Central reference for the environment, allows all widgets to refer to the current environment without individual update functions """
    def __init__(self, env: RailEnv = None):
        self.env: RailEnv = env

    def get_agent_handles(self):
        """Get the agent handles from the current environment."""
        if self.env:
            return self.env.get_agent_handles()
        return []

    def get_environment_info(self) -> dict:
        """Get information about the current environment."""
        if self.env:
            return {'info 1': 'value1', 'info 2': 'value2'}  # Example info, replace with actual logic
        return {}

    def get_metrics(self) -> dict:
        """Get evaluation metrics from the current environment."""
        if self.env:
            return {'metric 1': 0.5, 'metric 2': 1.0}  # Example metrics, replace with actual logic
        return {}