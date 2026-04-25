import abc
import os
from typing import Any, Generic, TypeVar

from lark import Lark, Token, Transformer

# ===== transformer, parser -> ast =====


# noinspection PyMethodMayBeStatic
class RollTransformer(Transformer[Any, Any]):
    _comma = object()

    def expr(self, num: Any):
        return Expression(*num)

    def comparison(self, binop: Any):
        return BinOp(*binop)

    def a_num(self, binop: Any):
        return BinOp(*binop)

    def m_num(self, binop: Any):
        return BinOp(*binop)

    def u_num(self, unop: Any):
        return UnOp(*unop)

    def numexpr(self, num_anno: Any):
        return AnnotatedNumber(*num_anno)

    def literal(self, num: Any):
        return Literal(*num)

    def set(self, opset: Any):
        return OperatedSet(*opset)

    def set_op(self, opsel: Any):
        return SetOperator.new(*opsel)

    def setexpr(self, the_set: Any):
        if len(the_set) == 1 and the_set[-1] is not self._comma:
            return Parenthetical(the_set[0])
        elif len(the_set) and the_set[-1] is self._comma:
            the_set = the_set[:-1]
        return NumberSet(the_set)

    def dice(self, opdice: Any):
        return OperatedDice(*opdice)

    def dice_op(self, opsel: Any):
        return SetOperator.new(*opsel)

    def diceexpr(self, dice: Any):
        if len(dice) == 1:
            return Dice(1, *dice)
        return Dice(*dice)

    def selector(self, sel: Any):
        return SetSelector(*sel)

    def comma(self, _):
        return self._comma


# ===== helper mixin =====
ChildType = TypeVar("ChildType", bound="ChildMixin")


class ChildMixin(Generic[ChildType]):
    """A mixin that tree nodes must implement to support tree traversal utilities."""

    @property
    @abc.abstractmethod
    def children(self) -> list[ChildType]:
        """
        Returns a list of this node's roll children.

        :rtype: list of ChildMixin
        """
        raise NotImplementedError

    @property
    def left(self) -> ChildType | None:
        """
        Returns the node's leftmost child, or None if there are no children.

        :rtype: ChildMixin or None
        """
        return self.children[0] if self.children else None

    @left.setter
    def left(self, value: ChildType) -> None:
        self.set_child(0, value)

    @property
    def right(self) -> ChildType | None:
        """
        Returns the node's rightmost child, or None if there are no children.

        :rtype: ChildMixin or None
        """
        return self.children[-1] if self.children else None

    @right.setter
    def right(self, value: ChildType) -> None:
        self.set_child(-1, value)

    def _child_set_check(self, index: int):
        if index > (len(self.children) - 1) or index < -len(self.children):
            raise IndexError

    @abc.abstractmethod
    def set_child(self, index: int, value: ChildType) -> None:
        """
        Sets the ith child of this object.

        :param int index: The index of the value to set.
        :param value: The new value to set it to.
        :type value: ChildMixin
        """
        self._child_set_check(index)
        raise NotImplementedError


# ===== ast classes =====
class Node(abc.ABC, ChildMixin["Node"]):
    """
    The base class for all AST nodes.

    A Node has no specific attributes, but supports all the methods in :class:`~d20.ast.ChildMixin` for traversal.
    """

    @abc.abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError


class Expression(Node):  # expr
    """Expressions are usually the root of all ASTs."""

    __slots__ = "roll"

    roll: Node

    def __init__(self, roll: Node):
        self.roll = roll

    @property
    def children(self):
        return [self.roll]

    def set_child(self, index: int, value: Node):
        self._child_set_check(index)
        self.roll = value

    def __str__(self):
        return str(self.roll)


class AnnotatedNumber(Node):  # numexpr
    """Represents a value with an annotation."""

    __slots__ = ("value", "annotations")

    value: Node
    annotations: list[str]

    def __init__(self, value: Node, *annotations: Token | str):
        """
        :type value: Node
        :type annotations: lark.Token or str
        """
        super().__init__()
        self.value = value
        self.annotations = [str(a).strip() for a in annotations]

    @property
    def children(self):
        return [self.value]

    def set_child(self, index: int, value: Node):
        self._child_set_check(index)
        self.value = value

    def __str__(self):
        return f"{str(self.value)} {''.join(self.annotations)}"


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

    @property
    def children(self) -> list[Node]:
        return []

    def set_child(self, index: int, value: Node) -> None:
        raise ValueError(f"Cannot set the child of a Literal")

    def __str__(self):
        return str(self.value)


class Parenthetical(Node):
    __slots__ = ("value",)

    value: Node

    def __init__(self, value: Node):
        """
        :type value: Node
        """
        super().__init__()
        self.value = value

    @property
    def children(self):
        return [self.value]

    def set_child(self, index: int, value: Node):
        self._child_set_check(index)
        self.value = value

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

    @property
    def children(self):
        return [self.value]

    def set_child(self, index: int, value: Node):
        self._child_set_check(index)
        self.value = value

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

    @property
    def children(self):
        return [self.left, self.right]

    def set_child(self, index: int, value: Node):
        self._child_set_check(index)
        if self.children[index] is self.left:
            self.left = value  # type: ignore
        else:
            self.right = value  # type: ignore

    def __str__(self):
        return f"{str(self.left)} {self.op} {str(self.right)}"


class SetOperator:  # set_op, dice_op
    __slots__ = ("op", "sels")

    IMMEDIATE = {"mi", "ma"}

    op: str
    sels: list["SetSelector"]

    def __init__(self, op: str | Token, sels: list["SetSelector"]):
        """
        :type op: lark.Token or str
        :type sels: list of SetSelector
        """
        self.op = str(op)
        self.sels = sels

    @classmethod
    def new(cls, op: str | Token, sel: "SetSelector | None" = None):
        if sel is None:
            sels = []
        else:
            sels = [sel]
        return cls(op, sels)

    def add_sels(self, sels: list["SetSelector"]):
        self.sels.extend(sels)

    def __str__(self):
        if len(self.sels) == 0:
            return self.op
        return "".join([f"{self.op}{str(sel)}" for sel in self.sels])


class SetSelector:  # selector
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

    def __str__(self):
        if self.cat:
            return f"{self.cat}{self.num}"
        return str(self.num)


class OperatedSet(Node):  # set
    __slots__ = ("value", "operations")

    set: "NumberSet | Dice"
    operations: list[SetOperator]

    def __init__(self, the_set: "NumberSet | Dice", *operations: SetOperator):
        """
        :type the_set: NumberSet or Dice
        :type operations: SetOperator
        """
        super().__init__()
        self.value = the_set
        self.operations = list(operations)
        self._simplify_operations()

    @property
    def children(self):
        return [self.value]

    def set_child(self, index: int, value: Node):
        self._child_set_check(index)
        self.value = value

    def _simplify_operations(self):
        """Simplifies expressions like k1k2k3 into k(1,2,3)."""
        new_operations: list[SetOperator] = []

        for operation in self.operations:
            if operation.op in SetOperator.IMMEDIATE or not new_operations:
                new_operations.append(operation)
            else:
                last_op = new_operations[-1]
                if operation.op == last_op.op:
                    last_op.add_sels(operation.sels)
                else:
                    new_operations.append(operation)

        self.operations = new_operations

    def __str__(self):
        return f"{str(self.value)}{''.join([str(op) for op in self.operations])}"


class NumberSet(Node):  # setexpr
    __slots__ = ("values",)

    values: list[Node]

    def __init__(self, values: list[Node]):
        """
        :type values: list of Node
        """
        super().__init__()
        self.values = list(values)

    @property
    def children(self):
        return self.values

    def set_child(self, index: int, value: Node):
        self._child_set_check(index)
        self.values[index] = value

    def __str__(self):
        out = f"{', '.join([str(v) for v in self.values])}"
        if len(self.values) == 1:
            return f"({out},)"
        return f"({out})"

    def __copy__(self):
        # we need to take a copy of the values list as well
        return NumberSet(values=self.values.copy())


class OperatedDice(OperatedSet):  # dice
    __slots__ = ()

    def __init__(self, the_dice: "Dice", *operations: SetOperator):
        """
        :type the_dice: Dice
        :type operations: SetOperator
        """
        super().__init__(the_dice, *operations)


class Dice(Node):  # diceexpr
    __slots__ = ("num", "size")

    num: int
    size: str | int

    def __init__(self, num: int | Token, size: int | str | Token):
        """
        :type num: lark.Token or int
        :type size: lark.Token or int or str
        """
        super().__init__()
        self.num = int(num)
        if str(size) == "%":
            self.size = str(size)
        else:
            self.size = int(size)

    @property
    def children(self) -> list[Node]:
        return []

    def set_child(self, index: int, value: Node) -> None:
        raise ValueError(f"Cannot set the child of a Dice")

    def __str__(self):
        return f"{self.num}d{self.size}"


with open(os.path.join(os.path.dirname(__file__), "grammar.lark")) as f:
    grammar = f.read()
parser = Lark(
    grammar, start=["expr"], parser="lalr", transformer=RollTransformer(), maybe_placeholders=True
)

if __name__ == "__main__":
    while True:
        parser = Lark(grammar, start=["expr"], parser="lalr", maybe_placeholders=True)
        result = parser.parse(input("> "), start="expr")  # type: ignore
        print(result.pretty())
        print(result)
        expr = RollTransformer().transform(result)
        print(str(expr))
