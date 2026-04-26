# region ===== Roller ======

import random
from collections.abc import Mapping
from typing import Callable, Optional, Type

from .expression import BinOp, Dice, Expression, Literal, Number, OperatedDice, Parenthetical, UnOp
from .stringifier import SimpleStringifier, Stringifier
from .. import diceast as ast
from ..common import AdvType, CritType
from ..context import RollContext
from ..rand import random_impl


class RollResult:
    """
    Holds information about the result of a roll. This should generally not be constructed manually.
    """

    def __init__(
        self,
        ast: ast.Node,
        rolls: list[Number[ast.Node]],
        result: Number[ast.Node],
        context: RollContext,
        stringifier: Stringifier,
        warnings: list[str],
    ):
        """
        :type the_ast: ast.Node
        :type the_roll: d20.Expression
        :type stringifier: d20.Stringifier
        """
        self.ast = ast
        self.rolls = rolls
        self.result = result
        self.context = context
        self.stringifier = stringifier
        self.warnings = warnings

    @property
    def total(self) -> int | float:
        return self.result.total

    @property
    def crit(self) -> CritType:
        """
        If the leftmost node was Xd20kh1, returns :class:`CritType.CRIT` if the roll was a 20 and
        :class:`CritType.FAIL` if the roll was a 1.
        Returns :class:`CritType.NONE` otherwise.

        :rtype: CritType
        """

        d20 = self.context.d20
        if d20 is None:
            return CritType.NONE

        node = self.result.find_from_ast(d20)

        if isinstance(node, Dice):
            dice = node.dice
        elif isinstance(node, OperatedDice):
            dice = node.keptset
        else:
            return CritType.NONE

        if len(dice) != 1 or node.size != 20:
            return CritType.NONE

        if dice[0].value == 1:
            return CritType.FAIL

        if dice[0].value == 20:
            return CritType.CRIT

        return CritType.NONE

    @property
    def expr(self) -> str:
        return self.stringifier.stringify(self.result)

    def __int__(self):
        return int(self.total)

    def __float__(self):
        return self.total

    def __repr__(self):
        return f"<RollResult total={self.total}>"


# noinspection PyMethodMayBeStatic
class Roller:
    """The main class responsible for parsing dice into an AST and evaluating that AST."""

    def __init__(self, rng: random.Random = random_impl):
        self._nodes: Mapping[Type[ast.Node], Callable[[ast.Node, RollContext], Number[ast.Node]]] = {  # type: ignore
            ast.Expression: self._eval_expression,
            ast.Literal: self._eval_literal,
            ast.Parenthetical: self._eval_parenthetical,
            ast.UnOp: self._eval_unop,
            ast.BinOp: self._eval_binop,
            ast.OperatedDice: self._eval_operateddice,
            ast.Dice: self._eval_dice,
        }
        self.rng = rng

    def roll(
        self,
        node: ast.Node,
        stringifier: Optional[Stringifier] = None,
        advantage: AdvType = AdvType.NONE,
    ) -> RollResult:
        """Rolls the dice."""
        if stringifier is None:
            stringifier = SimpleStringifier()

        context = RollContext(node, advantage, self.rng)
        warnings: list[str] = []

        roll = self._eval(node, context)
        rolls = [roll]

        if advantage != AdvType.NONE:
            d20 = context.d20
            if d20 is None:
                warnings.append(f"Rolled with {advantage.name}, but expression did not contain a valid d20.")
            else:
                for _ in range(advantage.rolls - 1):
                    copy = self._copy_with_d20_rerolled(roll, d20)
                    rolls.append(copy)

        result = self._get_advantage_roll(rolls, advantage)

        return RollResult(
            ast=node,
            rolls=rolls,
            result=result,
            context=context,
            stringifier=stringifier,
            warnings=warnings,
        )

    # evaluator
    def _eval(self, node: ast.Node, context: RollContext) -> Number[ast.Node]:
        handler = self._nodes[type(node)]
        return handler(node, context)

    def _eval_expression(self, node: ast.Expression, context: RollContext) -> Expression:
        return Expression(self._eval(node.roll, context), node)

    def _eval_literal(self, node: ast.Literal, context: RollContext) -> Literal:
        return Literal(node.value, node)

    def _eval_parenthetical(self, node: ast.Parenthetical, context: RollContext) -> Parenthetical:
        return Parenthetical(self._eval(node.value, context), node)

    def _eval_unop(self, node: ast.UnOp, context: RollContext) -> UnOp:
        return UnOp(node.op, self._eval(node.value, context), node)

    def _eval_binop(self, node: ast.BinOp, context: RollContext) -> BinOp:
        return BinOp(self._eval(node.left, context), node.op, self._eval(node.right, context), node)

    def _eval_operateddice(self, node: ast.OperatedDice, context: RollContext) -> OperatedDice:
        return OperatedDice.new(node, context)

    def _eval_dice(self, node: ast.Dice, context: RollContext) -> Dice:
        return Dice.new(node, context)

    # advantage util

    @staticmethod
    def _copy_with_d20_rerolled(roll: Number[ast.Node], d20: ast.Node):
        copy = roll.copy()
        d20_number = copy.find_from_ast(d20)
        if d20_number is None:
            return copy

        if not isinstance(d20_number, (OperatedDice, Dice)):
            return copy

        d20_number.dice[0].reroll()
        return copy

    @staticmethod
    def _get_advantage_roll(rolls: list[Number[ast.Node]], advantage: AdvType) -> Number[ast.Node]:
        match advantage.value:
            case AdvType.NONE.value:
                return rolls[0]

            # In case of advantage, return the one with the highest total
            case AdvType.ADV.value:
                roll = rolls[0]
                for i in range(1, len(rolls)):
                    if rolls[i].total > roll.total:
                        roll = rolls[i]
                return roll

            # In case of advantage, return the one with the lowest total
            case AdvType.DIS.value:
                roll = rolls[0]
                for i in range(1, len(rolls)):
                    if rolls[i].total < roll.total:
                        roll = rolls[i]
                return roll
