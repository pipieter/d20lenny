from collections.abc import Sequence
from typing import Literal

from . import diceast as ast
from .enums import Critical
from .roll import expression


def find_d20(node: ast.Node) -> ast.Dice | None:
    """
    Find the first fitting node that represents a d20 in a standard d20 plus modifiers roll.

    Args:
        node (ast.Node): The root node of the tree to search in.

    Raises:
        NotImplementedError: If an unknown node type is encountered.

    Returns:
        ast.Dice | None: A dice object representing the d20, or None if none could be found.
    """
    if isinstance(node, ast.Expression):
        return find_d20(node.roll)

    if isinstance(node, ast.Parenthetical):
        return find_d20(node.value)

    if isinstance(node, ast.Literal):
        return None

    if isinstance(node, ast.UnOp):
        return find_d20(node.value)

    if isinstance(node, ast.BinOp):
        if node.op not in ["+", "-"]:
            return None

        left = find_d20(node.left)
        if left is not None:
            return left

        right = find_d20(node.right)
        if right is not None:
            return right

        return None

    if isinstance(node, ast.Dice):
        if node.num == 1 and node.size == 20:
            return node
        return None

    raise NotImplementedError(f"find_d20 not implemented for {type(node)}")


def determine_crit_type(root: expression.Number, d20: expression.Number | None) -> Critical:
    if isinstance(d20, expression.Dice):
        dice = d20.keptset
    else:
        return Critical.NONE

    if len(dice) != 1 or d20.size != 20:
        return Critical.NONE

    if dice[0].value == 1:
        return Critical.FAIL

    if dice[0].value == 20:
        return Critical.CRIT

    if root.total == 20 and dice[0].value != 20:
        return Critical.DIRTY

    return Critical.NONE


def add_adv_operator_to_dice(dice: ast.Dice, adv: Literal["adv", "dis", None], count: int) -> bool:
    if adv is None:
        return True

    # Check if the dice already has adv or dis
    for operator in dice.operations:
        if operator.op in ["adv", "dis"]:
            return False

    dice.operations.append(ast.Operator(adv, [ast.Selector(None, count)]))
    return True


def extract_dice(node: expression.Number) -> Sequence[expression.Die]:
    if isinstance(node, expression.Expression):
        return extract_dice(node.value)
    if isinstance(node, expression.Literal):
        return []
    if isinstance(node, expression.Dice):
        return node.keptset
    if isinstance(node, expression.Parenthetical):
        return extract_dice(node.value)
    if isinstance(node, expression.UnOp):
        return extract_dice(node.value)
    if isinstance(node, expression.BinOp):
        return list(extract_dice(node.left)) + list(extract_dice(node.right))

    raise NotImplementedError(f"extract_dice not implemented for {type(node)}")


def expression_is_comparison(node: ast.Node) -> bool:
    if isinstance(node, ast.Expression):
        return expression_is_comparison(node.roll)
    if isinstance(node, ast.Parenthetical):
        return expression_is_comparison(node.value)
    if isinstance(node, ast.BinOp):
        return node.op in {">", "<", ">=", "<=", "==", "!="}

    return False
