import pytest

import d20.utils as utils
from d20 import diceast as ast, parse


@pytest.mark.parametrize(
    "has_d20,expr",
    [
        (True, "1d20+3"),
        (True, "1d20+1d4+3"),
        (True, "1d10+1d20"),
        (True, "1d20+1d20"),
        (True, "(1d20+1d20)+3"),
        (True, "1d20+1d20mi2"),
        (True, "(1d20*1d20)+1d20mi2"),
        (True, "1d20mi2"),
        (True, "1d20mi2+1d20"),
        (False, "1d20*4"),
        (False, "2d20"),
    ],
)
def test_context_d20(has_d20: bool, expr: str):
    tree = parse(expr)
    d20 = utils.find_d20(tree)

    if has_d20:
        assert d20 is not None
        assert isinstance(d20, ast.Dice)
    else:
        assert d20 is None


@pytest.mark.parametrize(
    "is_comparison, expr",
    [
        (True, "1d20 > 3"),
        (True, "1d20 - 1d4> 3"),
        (True, "((1d20 > 4))"),
        (False, "1d20"),
        (False, "(1d20 > 3) * 4"),
    ],
)
def test_is_comparison(is_comparison: bool, expr: str):
    tree = parse(expr)
    assert utils.expression_is_comparison(tree) == is_comparison
