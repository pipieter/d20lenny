from . import diceast as ast, rand, utils  # type: ignore
from .dice import *
from .errors import *
from .expression import *
from .stringifiers import *

# useful top-level functions to get started quickly
_roller = Roller()
roll = _roller.roll
parse = _roller.parse


def seed(s: int | float | str | bytes | bytearray | None = None):
    _roller.rng.seed(s)
