import abc
import random
from collections.abc import Callable as Callable, Mapping
from typing import Sequence

from _typeshed import Incomplete

from .. import diceast as ast
from ..diceast import Node as ASTNode

class RollContext:
    """
    A class to track information about rolls to ensure all rolls halt eventually.

    To use this class, pass an instance to the constructor of :class:`d20.Roller`.
    """

    rng: Incomplete
    max_rolls: Incomplete
    rolls: int
    def __init__(self, rng: random.Random, max_rolls: int = 1000) -> None: ...
    def roll(self, size: ast.DiceSize) -> int:
        """Roll a dice and return its value."""

class Number(abc.ABC, metaclass=abc.ABCMeta):
    """The base class for all rolled values."""

    def __init__(self, ast: ast.Node) -> None: ...
    @property
    @abc.abstractmethod
    def total(self) -> int:
        """The total value of the Number."""
    @property
    @abc.abstractmethod
    def children(self) -> Sequence["Number"]:
        """The children of the node."""
    @abc.abstractmethod
    def copy(self) -> Number:
        """Return a copy of the Number. The original AST nodes will not be copied to still allow find_from_ast."""
    def find_from_ast(self, ast: ASTNode | None) -> Number | None:
        """Find the child of the evaluated Number from its original AST node, or None if it could not be found."""

class Expression(Number):
    """Expressions are usually the root of all Number trees."""

    value: Number
    def __init__(self, roll: Number, ast: ast.Node) -> None: ...
    @property
    def total(self) -> int: ...
    @property
    def children(self) -> Sequence[Number]: ...
    def copy(self) -> Expression: ...

class Literal(Number):
    """A literal integer or float."""

    value: int | float
    def __init__(self, value: int | float, ast: ast.Node) -> None: ...
    @property
    def total(self) -> int: ...
    @property
    def children(self) -> Sequence[Number]: ...
    def copy(self) -> Literal: ...

class Parenthetical(Number):
    """Represents a value inside parentheses."""

    value: Number
    def __init__(self, value: Number, ast: ast.Node) -> None: ...
    @property
    def total(self) -> int: ...
    @property
    def children(self) -> Sequence[Number]: ...
    def copy(self) -> Parenthetical: ...

class UnOp(Number):
    """Represents a unary operation."""

    op: str
    value: Number
    def __init__(self, op: str, value: Number, ast: ast.Node) -> None: ...
    @property
    def total(self) -> int: ...
    @property
    def children(self) -> Sequence[Number]: ...
    def copy(self) -> UnOp: ...

class BinOp(Number):
    """Represents a binary operation."""

    op: str
    left: Number
    right: Number
    BINARY_OPS: Mapping[str, Callable[[int | float, int | float], int | float]]
    def __init__(self, left: Number, op: str, right: Number, ast: ast.Node) -> None: ...
    @property
    def total(self) -> int: ...
    @property
    def children(self) -> Sequence[Number]: ...
    def copy(self) -> BinOp: ...

class Die:
    """Represents a single die that can be rerolled or dropped."""

    kept: bool
    exploded: bool
    size: ast.DiceSize
    values: list[int]
    def __init__(
        self,
        value: int | list[int],
        size: ast.DiceSize,
        context: RollContext,
        kept: bool = True,
        exploded: bool = False,
    ) -> None: ...
    @property
    def value(self) -> int:
        """The final value of the die."""
    def reroll(self) -> None:
        """Re-roll the current die."""
    def set_value(self, value: int) -> None:
        """Set the current value of the die forcibly."""
    def drop(self) -> None:
        """Mark the die as dropped."""
    def explode(self) -> None:
        """Mark the die as exploded."""
    @staticmethod
    def new(size: ast.DiceSize, context: RollContext, kept: bool = True, exploded: bool = False) -> Die:
        """Roll a new die."""
    def copy(self) -> Die:
        """Return a copy of the die."""

class Dice(Number):
    """Represents a set of dice."""

    dice: list[Die]
    num: int
    size: ast.DiceSize
    operators: list["Operator"]
    def __init__(
        self,
        dice: list[Die],
        num: int,
        size: ast.DiceSize,
        operators: list["Operator"],
        ast: ast.Node,
        context: RollContext,
    ) -> None: ...
    @classmethod
    def new(cls, ast: ast.Dice, context: RollContext) -> Dice:
        """Roll a new set of dice."""
    @property
    def keptset(self) -> Sequence[Die]:
        """Return a list of all dice that were not dropped."""
    @property
    def total(self) -> int: ...
    @property
    def children(self) -> Sequence[Number]: ...
    def roll_another(self, negative: bool = False) -> None:
        """Roll another die and add it to the dice set."""
    def operate(self, operator: Operator) -> None:
        """Apply an operator to the dice set."""
    def copy(self) -> Dice: ...

class Operator:
    op: str
    sels: list["Selector"]
    def __init__(self, op: str, sels: list["Selector"]) -> None: ...
    @classmethod
    def from_ast(cls, ast: ast.Operator) -> Operator: ...
    def operate(self, target: Dice) -> None: ...
    def select(self, target: Dice) -> set[Die]:
        """Selects the operands in a target set."""
    def keep(self, target: Dice) -> None: ...
    def drop(self, target: Dice) -> None: ...
    def reroll(self, target: Dice) -> None: ...
    def reroll_once(self, target: Dice) -> None: ...
    def explode(self, target: Dice) -> None: ...
    def explode_once(self, target: Dice) -> None: ...
    def reroll_and_subtract(self, target: Dice) -> None: ...
    def explode_red(self, target: Dice) -> None: ...
    def minimum(self, target: Dice) -> None:
        """
        :type target: Dice
        """
    def maximum(self, target: Dice) -> None:
        """
        :type target: Dice
        """

class Selector:
    """Represents a selection on a dice set."""

    cat: str | None
    num: int
    def __init__(self, cat: str | None, num: int) -> None: ...
    @classmethod
    def from_ast(cls, ast: ast.Selector) -> Selector: ...
    def select(self, target: Dice) -> set[Die]: ...
    def lowestn(self, target: Dice) -> Sequence[Die]: ...
    def highestn(self, target: Dice) -> Sequence[Die]: ...
    def lessthan(self, target: Dice) -> Sequence[Die]: ...
    def morethan(self, target: Dice) -> Sequence[Die]: ...
    def literal(self, target: Dice) -> Sequence[Die]: ...
