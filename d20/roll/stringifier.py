import abc
from typing import Any, Callable, Mapping, Type

from .expression import BinOp, Dice, Die, Expression, Literal, Number, OperatedDice, Parenthetical, UnOp
from .. import diceast as ast

__all__ = ("Stringifier", "SimpleStringifier")


class Stringifier(abc.ABC):
    """
    ABC for string builder from dice result.
    Children should implement all ``_str_*`` methods to transform an Expression into a str.
    """

    def __init__(self):
        self._nodes: Mapping[Type[Number[ast.Node]], Callable[[Any], str]] = {
            Expression: self._str_expression,
            Literal: self._str_literal,
            UnOp: self._str_unop,
            BinOp: self._str_binop,
            Parenthetical: self._str_parenthetical,
            Dice: self._str_dice,
            OperatedDice: self._str_operated_dice,
        }

    def stringify(self, roll: Number[ast.Node]) -> str:
        """
        Transforms a rolled expression into a string recursively, bottom-up.

        :param the_roll: The expression to stringify.
        :type the_roll: d20.Expression
        :rtype: str
        """
        return self._stringify(roll)

    def _stringify(self, node: Number[ast.Node]) -> str:
        """
        Called on each node that needs to be stringified.

        :param node: The node to stringify.
        :type node: d20.Number
        :rtype: str
        """
        handler = self._nodes[type(node)]
        return handler(node)

    @abc.abstractmethod
    def _str_expression(self, node: Expression) -> str:
        """
        :param node: The node to stringify.
        :type node: d20.Expression
        :rtype: str
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _str_literal(self, node: Literal) -> str:
        """
        :param node: The node to stringify.
        :type node: d20.Literal
        :rtype: str
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _str_unop(self, node: UnOp) -> str:
        """
        :param node: The node to stringify.
        :type node: d20.UnOp
        :rtype: str
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _str_binop(self, node: BinOp) -> str:
        """
        :param node: The node to stringify.
        :type node: d20.BinOp
        :rtype: str
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _str_parenthetical(self, node: Parenthetical) -> str:
        """
        :param node: The node to stringify.
        :type node: d20.Parenthetical
        :rtype: str
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _str_dice(self, node: Dice) -> str:
        """
        :param node: The node to stringify.
        :type node: d20.Dice
        :rtype: str
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _str_operated_dice(self, node: OperatedDice) -> str:
        """
        :param node: The node to stringify.
        :type node: d20.Die
        :rtype: str
        """
        raise NotImplementedError


class SimpleStringifier(Stringifier):
    """
    Example stringifier.
    """

    def _str_expression(self, node: Expression):
        return f"{self._stringify(node.roll)} = {int(node.total)}"

    def _str_literal(self, node: Literal):
        return str(node.value)

    def _str_unop(self, node: UnOp):
        return f"{node.op}{self._stringify(node.value)}"

    def _str_binop(self, node: BinOp):
        return f"{self._stringify(node.left)} {node.op} {self._stringify(node.right)}"

    def _str_parenthetical(self, node: Parenthetical):
        return f"({self._stringify(node.value)})"

    def _str_dice(self, node: Dice):
        dice = [self._str_die(die, node.size) for die in node.dice]
        return f"{node.num}d{node.size} ({', '.join(dice)})"

    def _str_operated_dice(self, node: OperatedDice):
        dice = [self._str_die(die, node.size) for die in node.dice]
        operators = "".join(str(op) for op in node.operators)
        return f"{node.num}d{node.size}{operators} ({', '.join(dice)})"

    def _str_die(self, die: Die, size: ast.DiceSize) -> str:
        exploded_suffix = "!" if die.exploded else ""
        formatted = f"{die.value}{exploded_suffix}"

        if not die.kept:
            return f"~~{formatted}~~"

        if die.value == size:
            return f"**{formatted}**"

        return formatted
