from collections.abc import Sequence

from . import diceast as ast
from .enums import Advantage as Advantage, Critical as Critical
from .roll import expression as expression

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

def determine_crit_type(root: expression.Number, d20: expression.Number | None) -> Critical: ...
def determine_final_roll(rolls: list[expression.Number], advantage: Advantage) -> expression.Number: ...
def copy_number_with_d20_rerolled(roll: expression.Number, d20: ast.Node) -> expression.Number: ...
def extract_dice(node: expression.Number) -> Sequence[expression.Die]: ...
def expression_is_comparison(node: ast.Node) -> bool: ...
