import pytest

import d20
from d20 import parse
from d20.enums import AdvType
from d20.context import Context


@pytest.mark.parametrize(
    "d20,type,expr",
    [
        (True, d20.ast.Dice, "1d20+3"),
        (True, d20.ast.Dice, "1d20+1d4+3"),
        (True, d20.ast.Dice, "1d10+1d20"),
        (True, d20.ast.Dice, "1d20+1d20"),
        (True, d20.ast.Dice, "(1d20+1d20)+3"),
        (True, d20.ast.Dice, "1d20+1d20mi2"),
        (True, d20.ast.OperatedDice, "(1d20*1d20)+1d20mi2"),
        (True, d20.ast.OperatedDice, "1d20mi2"),
        (True, d20.ast.OperatedDice, "1d20mi2+1d20"),
        (False, None, "1d20*4"),
        (False, None, "2d20"),
    ],
)
def test_context_d20(d20: bool, type: type, expr: str):
    tree = parse(expr)
    context = Context(tree, AdvType.NONE)

    if d20:
        assert context.d20 is not None
        assert isinstance(context.d20, type)
    else:
        assert context.d20 is None
