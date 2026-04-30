# region ===== Roller ======

import dataclasses
import random
from collections.abc import Mapping, Sequence
from typing import Callable, Optional, Type

from .expression import BinOp, Dice, Expression, Literal, Number, Parenthetical, RollContext, UnOp
from .stringifier import SimpleStringifier, Stringifier
from .. import diceast as ast, utils
from ..enums import Advantage, Critical
from ..errors import RollError
from ..rand import random_impl


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
        return self.stringifier.stringify(self.roll)

    @property
    def total(self) -> int:
        """Return the total value of the roll."""
        return self.roll.total

    @property
    def is_comparison(self) -> bool:
        """Checks if the roll is a top-level comparison."""
        return utils.expression_is_comparison(self.ast)


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
        return self.roll.total

    @property
    def result(self) -> str:
        """Return the stringified expression of the result, e.g. 1d20 (5) + 2 = 7"""
        return self.roll.expr

    @property
    def expression(self) -> str:
        """Return the original form of the expression, e.g. 1d20 + 2"""
        return str(self.ast)

    def __int__(self) -> int:
        """Return the total value of the expression, as an integer."""
        return int(self.total)

    def __float__(self) -> float:
        """Return the total value of the expression, as an floating point number.."""
        return float(self.total)

    def __repr__(self) -> str:
        return f"<RollResult total={self.total}/>"


class Roller:
    """The main class responsible for evaluating and rolling dice expressions."""

    _rng: random.Random

    def __init__(self, rng: random.Random = random_impl):
        self._nodes: Mapping[Type[ast.Node], Callable[[ast.Node, RollContext], tuple[Number, Sequence[Number]]]] = {  # type: ignore
            ast.Expression: self._eval_expression,
            ast.Literal: self._eval_literal,
            ast.Parenthetical: self._eval_parenthetical,
            ast.UnOp: self._eval_unop,
            ast.BinOp: self._eval_binop,
            ast.Dice: self._eval_dice,
        }
        self._rng = rng

    def seed(self, s: int | float | str | bytes | bytearray | None = None) -> None:
        """Set the seed of the rng."""
        self._rng.seed(s)

    def roll(
        self,
        node: ast.Node,
        stringifier: Optional[Stringifier] = None,
        advantage: Advantage = Advantage.NONE,
    ) -> RollResult:
        """Rolls the dice."""

        # It's possible for the node to be edited for advantage, so a copy is made
        node = node.copy()

        if stringifier is None:
            stringifier = SimpleStringifier()

        d20 = utils.find_d20(node)
        context = RollContext(self._rng)
        warnings: list[str] = []

        first_roll = self._eval(node, context)
        rolls = [first_roll]

        # Add the advantage operator
        if advantage != Advantage.NONE:
            if d20 is None:
                warnings.append(f"Rolled with {advantage.value}, but expression did not contain a valid d20.")
            else:
                if not utils.add_adv_operator_to_dice(d20, advantage.adv, advantage.rolls):
                    warnings.append(f"The d20 in the expression already had an advantage operator.")

        # Roll the actual die
        roll, rolls = self._eval(node, context)

        # Add die warning
        die = utils.extract_dice(roll)
        if len(die) == 0:
            warnings.append("Expression did not contain any dice.")

        results = [
            SingleRollResult(
                ast=node,
                roll=roll,
                stringifier=stringifier,
                crit=utils.determine_crit_type(roll, roll.find_from_ast(d20)),
            )
            for roll in rolls
        ]
        result = results[rolls.index(roll)]

        return RollResult(
            ast=node,
            roll=result,
            rolls=results,
            advantage=advantage,
            stringifier=stringifier,
            warnings=warnings,
        )

    # evaluator
    def _eval(self, node: ast.Node, context: RollContext) -> tuple[Number, Sequence[Number]]:
        """Evaluate a node, returning a list of all possible rolls and the final roll of the expression."""
        handler = self._nodes[type(node)]
        return handler(node, context)

    def _eval_expression(self, node: ast.Expression, context: RollContext) -> tuple[Number, Sequence[Number]]:
        value, values = self._eval(node.roll, context)
        assert value in values

        expressions = [Expression(val, node) for val in values]
        expression = expressions[values.index(value)]

        return expression, expressions

    def _eval_literal(self, node: ast.Literal, context: RollContext) -> tuple[Number, Sequence[Number]]:
        literal = Literal(node.value, node)
        return literal, [literal]

    def _eval_parenthetical(self, node: ast.Parenthetical, context: RollContext) -> tuple[Number, Sequence[Number]]:
        value, values = self._eval(node.value, context)
        assert value in values

        parentheticals = [Parenthetical(val, node) for val in values]
        parenthetical = parentheticals[values.index(value)]

        return parenthetical, parentheticals

    def _eval_unop(self, node: ast.UnOp, context: RollContext) -> tuple[Number, Sequence[Number]]:
        value, values = self._eval(node.value, context)
        assert value in values

        unops = [UnOp(node.op, val, node) for val in values]
        unop = unops[values.index(value)]

        return unop, unops

    def _eval_binop(self, node: ast.BinOp, context: RollContext) -> tuple[Number, Sequence[Number]]:
        left_value, left_values = self._eval(node.left, context)
        right_value, right_values = self._eval(node.right, context)

        assert left_value in left_values
        assert right_value in right_values

        binops: list[BinOp] = []

        binop = None
        for lval in left_values:
            for rval in right_values:
                value = BinOp(lval, node.op, rval, node)
                binops.append(value)
                if lval is left_value and rval is right_value:
                    binop = value

        # Should never occur if every other function is implemented correctly, but this is required for the linter
        if binop is None:
            raise RollError("Could not construct roller binop")

        return binop, binops

    def _eval_dice(self, node: ast.Dice, context: RollContext) -> tuple[Number, Sequence[Number]]:
        value, values = Dice.new(node, context)

        assert value in values

        return value, values
