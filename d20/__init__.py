import os

from . import diceast as ast
from .enums import *
from .errors import *
from .rand import random_impl
from .roll import Roller, RollResult
from .roll.stringifier import Stringifier

_grammar_path = os.path.join(os.path.dirname(__file__), "grammar.lark")
_parser = ast.Parser(_grammar_path)
_roller = Roller(random_impl)


def parse(expr: str | ast.Expression) -> ast.Expression:
    if isinstance(expr, str):
        return _parser.parse(expr)
    return expr


def roll(expr: str | ast.Expression, stringifier: Stringifier | None = None, advantage: Advantage = Advantage.NONE) -> RollResult:
    tree = parse(expr)
    return _roller.roll(tree, stringifier, advantage)


def seed(s: int | float | str | bytes | bytearray | None = None) -> None:
    _roller.seed(s)
