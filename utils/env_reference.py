from flatland.envs.rail_env import RailEnv

class EnvReference(): 
    """ Central reference for the environment, allows all widgets to refer to the current environment without individual update functions """
    def __init__(self):
        self.env: RailEnv = None