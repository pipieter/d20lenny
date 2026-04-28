import abc
from collections.abc import Sequence
from typing import Any

from _typeshed import Incomplete
from lark import Token, Transformer

from d20.errors import RollSyntaxError as RollSyntaxError

DiceSize: Incomplete

class RollTransformer(Transformer[Any, Any]):
    def expr(self, num: Any) -> Expression: ...
    def comparison(self, binop: Any) -> BinOp: ...
    def a_num(self, binop: Any) -> BinOp: ...
    def m_num(self, binop: Any) -> BinOp: ...
    def u_num(self, unop: Any) -> UnOp: ...
    def literal(self, num: Any) -> Literal: ...
    def parenthetical(self, num: Any) -> Parenthetical: ...
    def dice(self, opdice: Any) -> Dice: ...
    def dice_op(self, opsel: Any) -> Operator: ...
    def dice_expr(self, dice: Any) -> Dice: ...
    def selector(self, sel: Any) -> Selector: ...

class Node(abc.ABC, metaclass=abc.ABCMeta):
    """The base class for all AST nodes."""

    @property
    @abc.abstractmethod
    def children(self) -> Sequence["Node"]: ...

class Expression(Node):
    """Expressions are usually the root of all ASTs."""

    roll: Node
    def __init__(self, roll: Node) -> None: ...
    @property
    def children(self) -> Sequence[Node]: ...

class Literal(Node):
    value: int | float
    def __init__(self, value: Token | int | float) -> None:
        """
        :type value: lark.Token or int or float
        """
    @property
    def children(self) -> Sequence[Node]: ...

class Parenthetical(Node):
    value: Node
    def __init__(self, value: Node) -> None:
        """
        :type value: Node
        """
    @property
    def children(self) -> Sequence[Node]: ...

class UnOp(Node):
    op: str
    value: Node
    def __init__(self, op: str | Token, value: Node) -> None:
        """
        :type op: lark.Token or str
        :type value: Node
        """
    @property
    def children(self) -> Sequence[Node]: ...

class BinOp(Node):
    op: str
    left: Node
    right: Node
    def __init__(self, left: Node, op: Token | str, right: Node) -> None:
        """
        :type op: lark.Token or str
        :type left: Node
        :type right: Node
        """
    @property
    def children(self) -> Sequence[Node]: ...

class Operator:
    IMMEDIATE: Incomplete
    op: str
    sels: list["Selector"]
    def __init__(self, op: str | Token, sels: list["Selector"]) -> None:
        """
        :type op: lark.Token or str
        :type sels: list of SetSelector
        """
    @classmethod
    def new(cls, op: str | Token, sel: Selector | None = None) -> Operator:
        """Create an operator from an op and a selector"""
    def add_sels(self, sels: list["Selector"]) -> None:
        """Add selectors to the operator."""

class Selector:
    cat: str | None
    num: int
    def __init__(self, cat: str | Token | None, num: int) -> None:
        """
        :type cat: str or lark.Token or None
        :type num: int
        """

class Dice(Node):
    num: int
    size: DiceSize
    operations: list[Operator]
    def __init__(self, num: int | Token, size: int | str | Token, *operations: Operator) -> None: ...
    @property
    def children(self) -> Sequence[Node]: ...

class Parser:
    def __init__(self, grammar_path: str) -> None: ...
    def parse(self, expr: str | bytes, start: str | None = None) -> Expression:
        """Parse an expression string to an expression AST tree."""
