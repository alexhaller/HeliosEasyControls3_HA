# ruff: noqa: N999 -- module/package names are fixed by the HA domain and the upstream project
from enum import Enum


class KWLState(Enum):
    AtHome = 1
    Away = 2
    Intensive = 3
    Individual = 4


class CellState(Enum):
    HeatRecovery = 0
    CoolRecovery = 1
    Bypass = 2
    Defrost = 3
