import os

from . import diceast as ast, rand, utils  # type: ignore
from .dice import *
from .errors import *
from .expression import *
from .stringifiers import *

_grammar_path = os.path.join(os.path.dirname(__file__), "grammar.lark")
_parser = ast.Parser(_grammar_path)
_roller = Roller()


def parse(expr: str | ast.Expression) -> ast.Expression:
    if isinstance(expr, str):
        return _parser.parse(expr)
    return expr


def roll(expr: str | ast.Expression, stringifier: Stringifier | None = None, advantage: AdvType = AdvType.NONE):
    tree = parse(expr)
    return _roller.roll(tree, stringifier, advantage)


def seed(s: int | float | str | bytes | bytearray | None = None):
    _roller.rng.seed(s)
