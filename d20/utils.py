from . import diceast as ast
from .enums import AdvType, CritType
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


def determine_crit_type(node: expression.Number | None) -> CritType:
    if isinstance(node, expression.Dice):
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


def determine_final_roll(rolls: list[expression.Number], advantage: AdvType) -> expression.Number:
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


def copy_number_with_d20_rerolled(roll: expression.Number, d20: ast.Node) -> expression.Number:
    copy = roll.copy()
    d20_number = copy.find_from_ast(d20)
    if d20_number is None:
        return copy

    if not isinstance(d20_number, expression.Dice):
        return copy

    d20_number.dice[0].reroll()
    return copy
