import dataclasses
import random

from .expression import (
    BinOp as BinOp,
    Dice as Dice,
    Expression as Expression,
    Literal as Literal,
    Number as Number,
    Parenthetical as Parenthetical,
    RollContext as RollContext,
    UnOp as UnOp,
)
from .stringifier import SimpleStringifier as SimpleStringifier, Stringifier as Stringifier
from .. import diceast as ast
from ..enums import Advantage, Critical

@dataclasses.dataclass
class SingleRollResult:
    """Holds information of a single roll result."""

    ast: ast.Node
    roll: Number
    crit: Critical
    stringifier: Stringifier
    @property
    def expr(self) -> str:
        """Return the string representation of the evaluated expression."""
    @property
    def total(self) -> int:
        """Return the total value of the roll."""
    @property
    def is_comparison(self) -> bool:
        """Checks if the roll is a top-level comparison."""

@dataclasses.dataclass
class RollResult:
    """Holds information about the result of a roll. This should generally not be constructed manually."""

    ast: ast.Node
    roll: SingleRollResult
    rolls: list[SingleRollResult]
    advantage: Advantage
    stringifier: Stringifier
    warnings: list[str]
    @property
    def total(self) -> int:
        """Return the total value of the roll."""
    @property
    def result(self) -> str:
        """Return the stringified expression of the result, e.g. 1d20 (5) + 2 = 7"""
    @property
    def expression(self) -> str:
        """Return the original form of the expression, e.g. 1d20 + 2"""
    def __int__(self) -> int:
        """Return the total value of the expression, as an integer."""
    def __float__(self) -> float:
        """Return the total value of the expression, as an floating point number.."""

class Roller:
    """The main class responsible for evaluating and rolling dice expressions."""

    def __init__(self, rng: random.Random = ...) -> None: ...
    def seed(self, s: int | float | str | bytes | bytearray | None = None) -> None:
        """Set the seed of the rng."""
    def roll(self, node: ast.Node, stringifier: Stringifier | None = None, advantage: Advantage = ...) -> RollResult:
        """Rolls the dice."""
