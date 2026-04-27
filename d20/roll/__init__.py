# region ===== Roller ======

import dataclasses
import random
from collections.abc import Mapping
from typing import Callable, Optional, Type

from .expression import BinOp, Dice, Expression, Literal, Number, Parenthetical, UnOp
from .stringifier import SimpleStringifier, Stringifier
from .. import diceast as ast, utils
from ..context import RollContext
from ..enums import AdvType, CritType
from ..rand import random_impl


@dataclasses.dataclass
class SingleRollResult:
    """Holds information of a single roll result."""

    ast: ast.Node
    roll: Number
    crit: CritType
    stringifier: Stringifier

    @property
    def expr(self) -> str:
        return self.stringifier.stringify(self.roll)

    @property
    def total(self) -> int:
        return self.roll.total

    @property
    def is_comparison(self) -> bool:
        return utils.expression_is_comparison(self.ast)


@dataclasses.dataclass
class RollResult:
    """Holds information about the result of a roll. This should generally not be constructed manually."""

    ast: ast.Node
    result: SingleRollResult
    rolls: list[SingleRollResult]
    advantage: AdvType
    stringifier: Stringifier
    warnings: list[str]
    crit: CritType

    @property
    def total(self) -> int:
        return self.result.total

    @property
    def expr(self) -> str:
        return self.result.expr

    def __int__(self):
        return int(self.total)

    def __float__(self):
        return self.total

    def __repr__(self):
        return f"<RollResult total={self.total}/>"


# noinspection PyMethodMayBeStatic
class Roller:
    """The main class responsible for parsing dice into an AST and evaluating that AST."""

    def __init__(self, rng: random.Random = random_impl):
        self._nodes: Mapping[Type[ast.Node], Callable[[ast.Node, RollContext], Number]] = {  # type: ignore
            ast.Expression: self._eval_expression,
            ast.Literal: self._eval_literal,
            ast.Parenthetical: self._eval_parenthetical,
            ast.UnOp: self._eval_unop,
            ast.BinOp: self._eval_binop,
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

        d20 = utils.find_d20(node)
        context = RollContext(self.rng)
        warnings: list[str] = []

        first_roll = self._eval(node, context)
        rolls = [first_roll]

        # Roll with advantage
        if advantage != AdvType.NONE:
            if d20 is None:
                warnings.append(f"Rolled with {advantage.name}, but expression did not contain a valid d20.")
            else:
                for _ in range(advantage.rolls - 1):
                    next_roll = utils.copy_number_with_d20_rerolled(first_roll, d20)
                    rolls.append(next_roll)

        result = utils.determine_final_roll(rolls, advantage)
        crit = CritType.NONE
        die = utils.extract_dice(result)

        if len(die) == 0:
            warnings.append("Expression did not contain any dice.")

        if d20:
            result_d20 = result.find_from_ast(d20)
            crit = utils.determine_crit_type(result_d20)

        result = SingleRollResult(
            ast=node,
            roll=result,
            stringifier=stringifier,
            crit=utils.determine_crit_type(result.find_from_ast(d20)),
        )
        rolls = [
            SingleRollResult(
                ast=node,
                roll=roll,
                stringifier=stringifier,
                crit=utils.determine_crit_type(roll.find_from_ast(d20)),
            )
            for roll in rolls
        ]

        return RollResult(
            ast=node,
            rolls=rolls,
            result=result,
            advantage=advantage,
            stringifier=stringifier,
            warnings=warnings,
            crit=crit,
        )

    # evaluator
    def _eval(self, node: ast.Node, context: RollContext) -> Number:
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

    def _eval_dice(self, node: ast.Dice, context: RollContext) -> Dice:
        return Dice.new(node, context)
