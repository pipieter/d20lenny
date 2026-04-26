import random
import typing
from enum import IntEnum
from typing import Any, Callable, Mapping, Optional, Type


from . import diceast as ast, rand, utils
from .context import *
from .errors import *
from .expression import *
from .stringifiers import MarkdownStringifier, Stringifier

__all__ = ("CritType", "AdvType", "RollResult", "Roller")


class CritType(IntEnum):
    """
    Integer enumeration representing the crit type of a roll.
    """

    NONE = 0
    CRIT = 1
    FAIL = 2


class AdvType(IntEnum):
    """
    Integer enumeration representing at what advantage a roll should be made at.
    """

    NONE = 0
    ADV = 1
    DIS = -1


class RollResult:
    """
    Holds information about the result of a roll. This should generally not be constructed manually.
    """

    def __init__(self, the_ast: ast.Node, the_roll: Expression, stringifier: Stringifier):
        """
        :type the_ast: ast.Node
        :type the_roll: d20.Expression
        :type stringifier: d20.Stringifier
        """
        self.ast = the_ast
        self.expr = the_roll
        self.stringifier = stringifier

    @property
    def total(self) -> int:
        return int(self.expr.total)

    @property
    def result(self) -> str:
        return self.stringifier.stringify(self.expr)

    @property
    def crit(self) -> CritType:
        """
        If the leftmost node was Xd20kh1, returns :class:`CritType.CRIT` if the roll was a 20 and
        :class:`CritType.FAIL` if the roll was a 1.
        Returns :class:`CritType.NONE` otherwise.

        :rtype: CritType
        """
        # find the left most node in the dice expression
        left = self.expr
        while left.children:
            left = left.children[0]

        # ensure the node is dice
        if not isinstance(left, Dice):
            return CritType.NONE

        # ensure only one die of size 20 is kept
        if not (len(left.keptset) == 1 and left.size == 20):
            return CritType.NONE

        if left.total == 1:
            return CritType.FAIL
        elif left.total == 20:
            return CritType.CRIT
        return CritType.NONE

    def __str__(self):
        return self.result

    def __int__(self):
        return self.total

    def __float__(self):
        return self.expr.total

    def __repr__(self):
        return f"<RollResult total={self.total}>"


# noinspection PyMethodMayBeStatic
class Roller:
    """The main class responsible for parsing dice into an AST and evaluating that AST."""

    def __init__(self, context: Optional[RollContext] = None, rng: random.Random = rand.random_impl):
        if context is None:
            context = RollContext()

        self._nodes: Mapping[Type[ast.Node], Callable[[Any], Number]] = {
            ast.Expression: self._eval_expression,
            ast.AnnotatedNumber: self._eval_annotatednumber,
            ast.Literal: self._eval_literal,
            ast.Parenthetical: self._eval_parenthetical,
            ast.UnOp: self._eval_unop,
            ast.BinOp: self._eval_binop,
            ast.OperatedSet: self._eval_operatedset,
            ast.NumberSet: self._eval_numberset,
            ast.OperatedDice: self._eval_operateddice,
            ast.Dice: self._eval_dice,
        }
        self.context = context
        self.rng = rng

    def roll(
        self,
        dice_tree: ast.Node,
        stringifier: Optional[Stringifier] = None,
        advantage: AdvType = AdvType.NONE,
    ) -> RollResult:
        """
        Rolls the dice.

        :param dice_tree: The parsed tree of the dice to roll.
        :type expr: ast.Node
        :param stringifier: The stringifier to stringify the result. Defaults to MarkdownStringifier.
        :type stringifier: d20.Stringifier
        :param AdvType advantage: If the roll should be made at advantage. Only applies if the leftmost node is 1d20.
        :rtype: RollResult
        """
        if stringifier is None:
            stringifier = MarkdownStringifier()

        self.context.reset()

        if advantage != AdvType.NONE:
            dice_tree = utils.ast_adv_copy(dice_tree, advantage)

        dice_expr = self._eval(dice_tree)
        dice_expr = typing.cast(Expression, dice_expr)
        return RollResult(dice_tree, dice_expr, stringifier)

    # evaluator
    def _eval(self, node: ast.Node) -> Number:
        # noinspection PyUnresolvedReferences
        # for some reason pycharm thinks this isn't a valid dict operation
        handler = self._nodes[type(node)]
        return handler(node)

    def _eval_expression(self, node: ast.Expression) -> Expression:
        return Expression(self._eval(node.roll), kept=True, annotation=None)

    def _eval_annotatednumber(self, node: ast.AnnotatedNumber) -> Number:
        target = self._eval(node.value)
        target.annotation = "".join(node.annotations)
        return target

    def _eval_literal(self, node: ast.Literal) -> Literal:
        return Literal(node.value, kept=True, annotation=None)

    def _eval_parenthetical(self, node: ast.Parenthetical) -> Parenthetical:
        return Parenthetical(self._eval(node.value), kept=True, annotation=None)

    def _eval_unop(self, node: ast.UnOp) -> UnOp:
        return UnOp(node.op, self._eval(node.value), kept=True, annotation=None)

    def _eval_binop(self, node: ast.BinOp) -> BinOp:
        return BinOp(self._eval(node.left), node.op, self._eval(node.right), kept=True, annotation=None)

    def _eval_operatedset(self, node: ast.OperatedSet) -> Number:
        target = self._eval(node.value)
        target = typing.cast(Set, target)
        for op in node.operations:
            the_op = SetOperator.from_ast(op)
            the_op.operate(target)
            target.operations.append(the_op)
        return target

    def _eval_numberset(self, node: ast.NumberSet) -> Set:
        return Set([self._eval(n) for n in node.values], kept=True, annotation=None)

    def _eval_operateddice(self, node: ast.OperatedDice) -> Number:
        return self._eval_operatedset(node)

    def _eval_dice(self, node: ast.Dice) -> Dice:
        return Dice.new(node.num, node.size, context=self.context, rng=self.rng, kept=True, annotation=None)
