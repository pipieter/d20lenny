import random

from . import diceast as ast
from .errors import RollValueError, TooManyRolls

__all__ = ("RollContext",)


class Context:
    expr: ast.Node
    d20: ast.Dice | ast.OperatedDice | None

    def __init__(self, expr: ast.Node) -> None:
        self.expr = expr
        self.d20 = self._find_d20(expr)

    @staticmethod
    def _find_d20(node: ast.Node) -> ast.Dice | ast.OperatedDice | None:
        """
        Find the first fitting node that represents a d20 in a standard d20 plus modifiers roll.

        Args:
            node (ast.Node): The root node of the tree to search in.

        Raises:
            NotImplementedError: If an unknown node type is encountered.

        Returns:
            ast.Dice | ast.OperatedDice | None: A dice or operated dice object representing the d20, or None if none could be found.
        """
        if isinstance(node, ast.Expression):
            return Context._find_d20(node.roll)

        if isinstance(node, ast.Parenthetical):
            return Context._find_d20(node.value)

        if isinstance(node, ast.Literal):
            return None

        if isinstance(node, ast.UnOp):
            return Context._find_d20(node.value)

        if isinstance(node, ast.BinOp):
            if node.op not in ["+", "-"]:
                return None

            left = Context._find_d20(node.left)
            if left is not None:
                return left

            right = Context._find_d20(node.right)
            if right is not None:
                return right

            return None

        if isinstance(node, ast.OperatedDice):
            if node.dice.num == 1 and node.dice.size == 20:
                return node
            return None

        if isinstance(node, ast.Dice):
            if node.num == 1 and node.size == 20:
                return node
            return None

        raise NotImplementedError(f"_find_d20 not implemented for {type(node)}")


class RollContext(Context):
    """
    A class to track information about rolls to ensure all rolls halt eventually.

    To use this class, pass an instance to the constructor of :class:`d20.Roller`.
    """

    def __init__(self, expr: ast.Node, rng: random.Random, max_rolls: int = 1000):
        super().__init__(expr)
        self.rng = rng
        self.max_rolls = max_rolls
        self.rolls = 0

    def count_roll(self, n: int = 1):
        """
        Called each time a die is about to be rolled.

        :param int n: The number of rolls about to be made.
        :raises d20.TooManyRolls: if the roller should stop rolling dice because too many have been rolled.
        """
        self.rolls += n
        if self.rolls > self.max_rolls:
            raise TooManyRolls("Too many dice rolled.")

    def roll(self, size: ast.DiceSize) -> int:
        if size == 0:
            raise RollValueError("Cannot roll zero-sided die.")

        self.count_roll(1)
        if size == "%":
            return self.rng.randrange(10) * 10
        else:
            return self.rng.randrange(size) + 1
