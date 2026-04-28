import dataclasses
import random
from .. import diceast as ast
from ..enums import Advantage, Critical
from .expression import BinOp as BinOp, Dice as Dice, Expression as Expression, Literal as Literal, Number as Number, Parenthetical as Parenthetical, RollContext as RollContext, UnOp as UnOp
from .stringifier import SimpleStringifier as SimpleStringifier, Stringifier as Stringifier
from _typeshed import Incomplete

@dataclasses.dataclass
class SingleRollResult:
    ast: ast.Node
    roll: Number
    crit: Critical
    stringifier: Stringifier
    @property
    def expr(self) -> str: ...
    @property
    def total(self) -> int: ...
    @property
    def is_comparison(self) -> bool: ...

@dataclasses.dataclass
class RollResult:
    ast: ast.Node
    roll: SingleRollResult
    rolls: list[SingleRollResult]
    advantage: Advantage
    stringifier: Stringifier
    warnings: list[str]
    @property
    def total(self) -> int: ...
    @property
    def result(self) -> str: ...
    @property
    def expression(self) -> str: ...
    def __int__(self) -> int: ...
    def __float__(self) -> float: ...

class Roller:
    rng: Incomplete
    def __init__(self, rng: random.Random = ...) -> None: ...
    def roll(self, node: ast.Node, stringifier: Stringifier | None = None, advantage: Advantage = ...) -> RollResult: ...
