from typing import List, Dict

class EnvHistory:
    def __init__(self):
        self.history: List = []
        self.history_imgs: List[Dict] = []

    def add_entry(self, entry):
        """Add a new entry to the environment history."""
        self.history.append(entry)

    def get_history(self):
        """Return the complete history of the environment."""
        return self.history

    def clear_history(self):
        """Clear the environment history."""
        self.history.clear()