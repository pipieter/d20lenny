from hypothesis import Verbosity, given, settings

from d20 import RollError, ast, parse, roll
from d20.roll import Expression, RollResult
from . import custom_strategies as cst

if False:

    @given(cst.expr())
    @settings(verbosity=Verbosity.verbose, max_examples=1000, deadline=3000)
    def test_any_valid_roll(expr: str):
        """Every valid dice expression should either return a valid result or raise a handled error"""
        parsed = parse(expr)
        try:
            result = roll(parsed)
            assert result
            assert isinstance(result, RollResult)
            assert isinstance(result.result, str)
            assert isinstance(result.total, (int, float))
            assert isinstance(result.ast, ast.Node)
            assert isinstance(result.expr, Expression)
        except RollError:
            return
