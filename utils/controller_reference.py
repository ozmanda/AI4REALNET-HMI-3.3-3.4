from typing import List, Dict, Union
from torch import Tensor
from numpy.random import randint

class ControllerRef():
    def __init__(self, controllertype: str = None, modelname: str = None):
        self.controllertype: str = controllertype
        self._init_controller(controllertype)

        self.modelname: str = modelname
        self._load_model_state_dict(modelname)


    def _init_controller(self, controllertype: str = None):
        if controllertype:
            self.controllertype = controllertype
        if self.controllertype:
            print(f"Initializing {self.controllertype} controller")
            raise NotImplementedError("Controller initialization not implemented")


    def _load_model_state_dict(self, modelname: str = None):
        if modelname:
            self.modelname = modelname
        if self.modelname:
            # Load the model state dictionary from a file or database
            print(f"Loading model state dictionary for {self.modelname}")
            raise NotImplementedError("Model state loading not implemented")
        

    def get_controller_info(self):
        """Get information about the controller."""
        raise NotImplementedError("Controller info retrieval not implemented")


    def get_actions(self, states: Dict[Union[str, int], Tensor]) -> List[int]:
        """Get actions based on the current states."""
        n_agents = len(states)
        actions = [0] * n_agents  # Default action for each agent
        for i in range(n_agents):
            if states[i] is not None:
                actions[i] = randint(0, 5)  # Random action between 0 and 4
        return actions