import abc
import os
import typing
from collections.abc import MutableMapping, Sequence
from typing import Any

import cachetools
import lark
from lark import Lark, Token, Transformer

from d20.errors import RollError, RollSyntaxError

# ===== transformer, parser -> ast =====

DiceSize = int | typing.Literal["%"]


# noinspection PyMethodMayBeStatic
class RollTransformer(Transformer[Any, Any]):
    def expr(self, num: Any) -> "Expression":
        return Expression(*num)

    def comparison(self, binop: Any) -> "BinOp":
        return BinOp(*binop)

    def a_num(self, binop: Any) -> "BinOp":
        return BinOp(*binop)

    def m_num(self, binop: Any) -> "BinOp":
        return BinOp(*binop)

    def u_num(self, unop: Any) -> "UnOp":
        return UnOp(*unop)

    def literal(self, num: Any) -> "Literal":
        return Literal(*num)

    def parenthetical(self, num: Any) -> "Parenthetical":
        return Parenthetical(*num)

    def dice(self, opdice: Any) -> "Dice":
        dice, *operations = opdice
        return Dice(dice.num, dice.size, *operations)

    def dice_op(self, opsel: Any) -> "Operator":
        return Operator.new(*opsel)

    def dice_expr(self, dice: Any) -> "Dice":
        if len(dice) == 1:
            return Dice(1, *dice)
        return Dice(*dice)

    def selector(self, sel: Any) -> "Selector":
        return Selector(*sel)

    def num_selector(self, sel: Any) -> "Selector":
        return Selector(None, *sel)


# ===== ast classes =====


class Node(abc.ABC):
    """The base class for all AST nodes."""

    @abc.abstractmethod
    def copy(self) -> "Node":
        """Create a copy of the node."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def children(self) -> Sequence["Node"]:
        raise NotImplementedError

    @abc.abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError


class Expression(Node):  # expr
    """Expressions are usually the root of all ASTs."""

    __slots__ = "roll"

    roll: Node

    def __init__(self, roll: Node):
        self.roll = roll

    def copy(self) -> Node:
        return Expression(self.roll.copy())

    @property
    def children(self) -> Sequence[Node]:
        return [self.roll]

    def __str__(self):
        return str(self.roll)


class Literal(Node):  # literal
    __slots__ = ("value",)

    value: int | float

    def __init__(self, value: Token | int | float):
        """
        :type value: lark.Token or int or float
        """
        super().__init__()
        if isinstance(value, Token):
            self.value = int(value) if value.type == "INTEGER" else float(value)
        else:
            self.value = value

    def copy(self) -> Node:
        return Literal(self.value)

    @property
    def children(self) -> Sequence[Node]:
        return []

    def __str__(self):
        return str(self.value)


class Parenthetical(Node):
    __slots__ = "value"

    value: Node

    def __init__(self, value: Node):
        """
        :type value: Node
        """
        super().__init__()
        self.value = value

    def copy(self) -> Node:
        return Parenthetical(self.value.copy())

    @property
    def children(self) -> Sequence[Node]:
        return [self.value]

    def __str__(self):
        return f"({str(self.value)})"


class UnOp(Node):  # u_num
    __slots__ = ("op", "value")

    op: str
    value: Node

    def __init__(self, op: str | Token, value: Node):
        """
        :type op: lark.Token or str
        :type value: Node
        """
        super().__init__()
        self.op = str(op)
        self.value = value

    def copy(self) -> Node:
        return UnOp(self.op, self.value.copy())

    @property
    def children(self) -> Sequence[Node]:
        return [self.value]

    def __str__(self):
        return f"{self.op}{str(self.value)}"


class BinOp(Node):  # a_num, m_num
    __slots__ = ("op", "left", "right")

    op: str
    left: Node
    right: Node

    def __init__(self, left: Node, op: Token | str, right: Node):
        """
        :type op: lark.Token or str
        :type left: Node
        :type right: Node
        """
        super().__init__()
        self.op = str(op)
        self.left = left
        self.right = right

    def copy(self) -> Node:
        return BinOp(self.left.copy(), self.op, self.right.copy())

    @property
    def children(self) -> Sequence[Node]:
        return [self.left, self.right]

    def __str__(self):
        return f"{str(self.left)} {self.op} {str(self.right)}"


class Operator:  # set_op, dice_op
    __slots__ = ("op", "sels")

    IMMEDIATE = {"mi", "ma"}

    op: str
    sels: list["Selector"]

    def __init__(self, op: str | Token, sels: list["Selector"]):
        """
        :type op: lark.Token or str
        :type sels: list of SetSelector
        """
        self.op = str(op)
        self.sels = sels

    @classmethod
    def new(cls, op: str | Token, sel: "Selector | None" = None) -> "Operator":
        """Create an operator from an op and a selector"""
        if sel is None:
            sels = []
        else:
            sels = [sel]
        return cls(op, sels)

    def add_sels(self, sels: list["Selector"]) -> None:
        """Add selectors to the operator."""
        self.sels.extend(sels)

    def copy(self) -> "Operator":
        sels = [sel.copy() for sel in self.sels]
        return Operator(self.op, sels)

    def __str__(self):
        if len(self.sels) == 0:
            return self.op
        return "".join([f"{self.op}{str(sel)}" for sel in self.sels])


class Selector:  # selector
    __slots__ = ("cat", "num")

    cat: str | None
    num: int

    def __init__(self, cat: str | Token | None, num: int):
        """
        :type cat: str or lark.Token or None
        :type num: int
        """
        self.cat = str(cat) if cat is not None else None
        self.num = int(num)

    def copy(self) -> "Selector":
        return Selector(self.cat, self.num)

    def __str__(self):
        if self.cat:
            return f"{self.cat}{self.num}"
        return str(self.num)


class Dice(Node):  # dice_expr
    num: int
    size: DiceSize
    operations: list[Operator]

    def __init__(self, num: int | Token, size: int | str | Token, *operations: Operator):
        super().__init__()
        self.num = int(num)
        if str(size) == "%":
            self.size = "%"
        else:
            self.size = int(size)
        self.operations = list(operations)
        self._validate_operations()
        self._simplify_operations()

    @property
    def children(self) -> Sequence[Node]:
        return []

    def _simplify_operations(self):
        """Simplifies expressions like k1k2k3 into k(1,2,3)."""
        new_operations: list[Operator] = []

        for operation in self.operations:
            if operation.op in Operator.IMMEDIATE or not new_operations:
                new_operations.append(operation)
            else:
                last_op = new_operations[-1]
                if operation.op == last_op.op:
                    last_op.add_sels(operation.sels)
                else:
                    new_operations.append(operation)

        self.operations = new_operations

    def _validate_operations(self):
        """Validates if the operations are valid."""
        # Only one adv or dis allowed per expression
        adv_count = 0
        for op in self.operations:
            if op.op in ["adv", "dis"]:
                adv_count += 1
                # adv or dis selector must a numeric value greater than zero
                for sel in op.sels:
                    if sel.cat is not None or sel.num < 1:
                        raise RollError(f"Selector for {op} must be a numeric value greater than zero.")

        if adv_count > 1:
            raise RollError("Only one adv or dis operator is allowed per dice expression.")

    def copy(self) -> Node:
        operations = [op.copy() for op in self.operations]
        return Dice(self.num, self.size, *operations)

    def __str__(self):
        operations = "".join([str(op) for op in self.operations])
        return f"{self.num}d{self.size}{operations}"


class Parser:
    _lark: Lark
    _cache: MutableMapping[str, Expression]
    _transformer: RollTransformer

    def __init__(self, grammar_path: str) -> None:
        with open(grammar_path, "r") as grammar_file:
            grammar = grammar_file.read()

        self._transformer = RollTransformer()
        self._cache = cachetools.LFUCache(256)
        self._lark = Lark(
            grammar,
            start=["expr"],
            parser="lalr",
            transformer=self._transformer,
            maybe_placeholders=True,
        )

    def parse(self, expr: str | bytes, start: str | None = None) -> Expression:
        """Parse an expression string to an expression AST tree."""
        if start is None:
            start = "expr"

        try:
            expr = str(expr)
            # see if this expr is in cache
            clean_expr = expr.replace(" ", "")
            if clean_expr in self._cache:
                dice_tree = self._cache[clean_expr]
            else:
                dice_tree = self._lark.parse(expr, start=start)  # type: ignore
                dice_tree = typing.cast(Expression, dice_tree)
                self._cache[clean_expr] = dice_tree
            return dice_tree
        except lark.UnexpectedToken as ut:
            raise RollSyntaxError(ut.line, ut.column, ut.token, ut.expected)
        except lark.UnexpectedCharacters as uc:
            raise RollSyntaxError(uc.line, uc.column, expr[uc.pos_in_stream], uc.allowed)


if __name__ == "__main__":
    grammar_path = os.path.join(os.path.dirname(__file__), "grammar.lark")
    parser = Parser(grammar_path)

    while True:
        expr = parser.parse(input("> "), start="expr")
        print(str(expr))
