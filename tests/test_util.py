import pytest

import d20
from d20 import parse
import d20.utils as utils


@pytest.mark.parametrize(
    "has_d20,type,expr",
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
def test_context_d20(has_d20: bool, type: type, expr: str):
    tree = parse(expr)
    d20 = utils.find_d20(tree)

    if has_d20:
        assert d20 is not None
        assert isinstance(d20, type)
    else:
        assert d20 is None
