from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


STEP_INTERVAL_MS = 500
DEFAULT_MALFUNCTION_RATE = 1 / 40
DEFAULT_MALFUNCTION_MIN = 4
DEFAULT_MALFUNCTION_MAX = 8
SCENARIO_DIRECTORY = Path(
    r"C:\Users\ma1198656\OneDrive - FHNW\Dokumente\VSCode\AI4REALNET-T3.4\src\environments"
)


@dataclass
class SimulationConfig:
    model_path: Optional[str]
    scenario_path: Optional[str]
    width: int
    height: int
    agents: int
    malfunction_rate: float
    malfunction_min: int
    malfunction_max: int
