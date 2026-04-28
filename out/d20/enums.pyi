from enum import Enum

__all__ = ['Critical', 'Advantage']

class Critical(str, Enum):
    NONE = 'none'
    CRIT = 'crit'
    FAIL = 'fail'
    DIRTY = 'dirty'

class Advantage(str, Enum):
    NONE = 'none'
    ADVANTAGE = 'advantage'
    DISADVANTAGE = 'disadvantage'
    ELVEN_ACCURACY = 'elven accuracy'
    @property
    def rolls(self) -> int: ...
