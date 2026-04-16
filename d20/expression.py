import abc
from collections.abc import Callable, Iterable, Mapping, Sequence
import random

from typing import Optional


from .context import RollContext

from . import diceast as ast, errors, rand

__all__ = (
    "Number",
    "Expression",
    "Literal",
    "UnOp",
    "BinOp",
    "Parenthetical",
    "Set",
    "Dice",
    "Die",
    "SetOperator",
    "SetSelector",
)


# ===== ast -> expression models =====
class Number(abc.ABC, ast.ChildMixin["Number"]):  # num
    """
    The base class for all expression objects.

    Note that Numbers implement all the methods of a :class:`~d20.ast.ChildMixin`.
    """

    __slots__ = ("kept", "annotation")

    kept: bool
    annotation: Optional[str]

    def __init__(self, kept: bool = True, annotation: Optional[str] = None):
        self.kept = kept
        self.annotation = annotation

    @property
    def number(self) -> int | float:
        """
        Returns the numerical value of this object.

        :rtype: int or float
        """
        return sum(n.number for n in self.keptset)

    @property
    def total(self) -> int | float:
        """
        Returns the numerical value of this object with respect to whether it's kept.
        Generally, this is preferred to use over ``number``, as this will return 0 if
        the number node was dropped.

        :rtype: int or float
        """
        return self.number if self.kept else 0

    @property
    @abc.abstractmethod
    def set(self) -> Sequence["Number"]:
        """
        Returns the set representation of this object.

        :rtype: list[Number]
        """
        raise NotImplementedError

    @property
    def keptset(self):
        """
        Returns the set representation of this object, but only including children whose values
        were not dropped.

        :rtype: list[Number]
        """
        return [n for n in self.set if n.kept]

    def drop(self):
        """
        Makes the value of this Number node not count towards a total.
        """
        self.kept = False

    def __int__(self):
        return int(self.total)

    def __float__(self):
        return float(self.total)

    def __repr__(self):
        return f"<Number total={self.total} kept={self.kept}>"


class Expression(Number):
    """Expressions are usually the root of all Number trees."""

    __slots__ = ("roll", "comment")

    roll: Number
    comment: Optional[str]

    def __init__(self, roll: Number, comment: Optional[str], kept: bool = True, annotation: Optional[str] = None):
        """
        :type roll: Number
        """
        super().__init__(kept, annotation)
        self.roll = roll
        self.comment = comment

    @property
    def number(self):
        return self.roll.number

    @property
    def set(self):
        return self.roll.set

    @property
    def children(self):
        return [self.roll]

    def set_child(self, index: int, value: Number):
        self._child_set_check(index)
        self.roll = value

    def __repr__(self):
        return f"<Expression roll={self.roll} comment={self.comment}>"


class Literal(Number):
    """A literal integer or float."""

    __slots__ = ("values", "exploded")

    values: list[int | float]  # history is tracked to support mi/ma op
    exploded: bool

    def __init__(
        self,
        value: int | float | list[int | float],
        exploded: bool = False,
        kept: bool = True,
        annotation: Optional[str] = None,
    ):
        """
        :type value: int or float
        """
        super().__init__(kept, annotation)
        if isinstance(value, list):
            self.values = value
        else:
            self.values = [value]
        self.exploded = exploded

    @property
    def number(self):
        return self.values[-1]

    @property
    def set(self) -> list[Number]:
        return [self]

    @property
    def children(self) -> list[Number]:
        return []

    def explode(self):
        self.exploded = True

    def update(self, value: int | float):
        """
        :type value: int or float
        """
        self.values.append(value)

    def set_child(self, index: int, value: Number) -> None:
        raise ValueError(f"Cannot set the child of a Literal")

    def __repr__(self):
        return f"<Literal {self.number}>"

    def __neg__(self):
        copy = Literal(self.values, self.exploded, self.kept, self.annotation)
        copy.values[-1] *= -1
        return copy


class UnOp(Number):
    """Represents a unary operation."""

    __slots__ = ("op", "value")

    op: str
    value: Number

    UNARY_OPS: Mapping[str, Callable[[int | float], int | float]] = {"-": lambda v: -v, "+": lambda v: +v}

    def __init__(self, op: str, value: Number, kept: bool = True, annotation: Optional[str] = None):
        """
        :type op: str
        :type value: Number
        """
        super().__init__(kept, annotation)
        self.op = op
        self.value = value

    @property
    def number(self):
        return self.UNARY_OPS[self.op](self.value.total)

    @property
    def set(self) -> list[Number]:
        return [self]

    @property
    def children(self):
        return [self.value]

    def set_child(self, index: int, value: Number):
        self._child_set_check(index)
        self.value = value

    def __repr__(self):
        return f"<UnOp op={self.op} value={self.value}>"


class BinOp(Number):
    """Represents a binary operation."""

    __slots__ = ("op", "left", "right")

    op: str
    left: Number
    right: Number

    BINARY_OPS: Mapping[str, Callable[[int | float, int | float], int | float]] = {
        "+": lambda l, r: l + r,
        "-": lambda l, r: l - r,
        "*": lambda l, r: l * r,
        "/": lambda l, r: l / r,
        "//": lambda l, r: l // r,
        "%": lambda l, r: l % r,
        "<": lambda l, r: int(l < r),
        ">": lambda l, r: int(l > r),
        "==": lambda l, r: int(l == r),
        ">=": lambda l, r: int(l >= r),
        "<=": lambda l, r: int(l <= r),
        "!=": lambda l, r: int(l != r),
    }

    def __init__(self, left: Number, op: str, right: Number, kept: bool = True, annotation: Optional[str] = None):
        """
        :type op: str
        :type left: Number
        :type right: Number
        """
        super().__init__(kept, annotation)
        self.op = op
        self.left = left
        self.right = right

    @property
    def number(self):
        try:
            return self.BINARY_OPS[self.op](self.left.total, self.right.total)
        except ZeroDivisionError:
            raise errors.RollValueError("Cannot divide by zero.")

    @property
    def set(self) -> list[Number]:
        return [self]

    @property
    def children(self):
        return [self.left, self.right]

    def set_child(self, index: int, value: Number):
        self._child_set_check(index)
        if self.children[index] is self.left:
            self.left = value  # type: ignore
        else:
            self.right = value  # type: ignore

    def __repr__(self):
        return f"<BinOp left={self.left} op={self.op} right={self.right}>"


class Parenthetical(Number):
    """Represents a value inside parentheses."""

    __slots__ = ("value", "operations")

    value: Number
    operations: list["SetOperator"]

    def __init__(
        self,
        value: Number,
        operations: Optional[list["SetOperator"]] = None,
        kept: bool = True,
        annotation: Optional[str] = None,
    ):
        """
        :type value: Number
        :type operations: list[SetOperator]
        """
        super().__init__(kept, annotation)
        if operations is None:
            operations = []
        self.value = value
        self.operations = operations

    @property
    def total(self):
        return self.value.total if self.kept else 0

    @property
    def set(self):
        return self.value.set

    @property
    def children(self):
        return [self.value]

    def set_child(self, index: int, value: Number):
        self._child_set_check(index)
        self.value = value

    def __repr__(self):
        return f"<Parenthetical value={self.value} operations={self.operations}>"


class Set(Number):
    """Represents a set of values."""

    __slots__ = ("values", "operations")

    values: list[Number]
    operations: list["SetOperator"]

    def __init__(
        self,
        values: list[Number],
        operations: Optional[list["SetOperator"]] = None,
        kept: bool = True,
        annotation: Optional[str] = None,
    ):
        """
        :type values: list[Number]
        :type operations: list[SetOperator]
        """
        super().__init__(kept, annotation)
        if operations is None:
            operations = []
        self.values = values
        self.operations = operations

    @property
    def set(self) -> list[Number]:
        return self.values

    @property
    def children(self) -> list[Number]:
        return self.values

    def set_child(self, index: int, value: Number):
        self._child_set_check(index)
        self.values[index] = value

    def __repr__(self):
        return f"<Set values={self.values} operations={self.operations}>"

    def __copy__(self):
        return Set(
            values=self.values.copy(),
            operations=self.operations.copy(),
            kept=self.kept,
            annotation=self.annotation,
        )


class Dice(Set):
    """A set of Die."""

    __slots__ = ("num", "size", "_context", "_rng")

    num: int
    size: int | str
    values: list["Number"]
    operations: list["SetOperator"]
    _context: Optional[RollContext]
    _rng: random.Random

    def __init__(
        self,
        num: int,
        size: int | str,
        values: list[Number],
        operations: Optional[list["SetOperator"]] = None,
        context: Optional[RollContext] = None,
        rng: random.Random = rand.random_impl,
        kept: bool = True,
        annotation: Optional[str] = None,
    ):
        """
        :type num: int
        :type size: int|str
        :type values: list of Die
        :type operations: list[SetOperator]
        :type context: dice.RollContext
        :type rng: random.Random
        """
        super().__init__(values, operations, kept, annotation)
        self.num = num
        self.size = size
        self._context = context
        self._rng = rng

    @classmethod
    def new(
        cls,
        num: int,
        size: int | str,
        context: Optional[RollContext] = None,
        rng: random.Random = rand.random_impl,
        kept: bool = True,
        annotation: Optional[str] = None,
    ):
        return cls(
            num,
            size,
            [Die.new(size, context=context, rng=rng) for _ in range(num)],
            context=context,
            rng=rng,
            kept=kept,
            annotation=annotation,
        )

    def roll_another(self, negative: bool = False):
        die = Die.new(self.size, context=self._context, rng=self._rng)
        if negative:
            die = -die
        self.values.append(die)

    @property
    def children(self) -> list[Number]:
        return []

    def __repr__(self):
        return f"<Dice num={self.num} size={self.size} values={self.values} operations={self.operations}>"

    def __copy__(self):
        return Dice(
            num=self.num,
            size=self.size,
            context=self._context,
            rng=self._rng,
            values=self.values.copy(),
            operations=self.operations.copy(),
            kept=self.kept,
            annotation=self.annotation,
        )


class Die(Number):  # part of diceexpr
    """Represents a single die."""

    __slots__ = ("size", "values", "_context", "_rng")

    size: int | str
    values: list[Literal]
    _context: Optional[RollContext]
    _rng: random.Random

    def __init__(
        self,
        size: int | str,
        values: list[Literal],
        context: Optional[RollContext] = None,
        rng: random.Random = rand.random_impl,
    ):
        """
        :type size: int
        :type values: list of Literal
        :type context: dice.RollContext
        :type rng: random.Random
        """
        super().__init__()
        self.size = size
        self.values = values
        self._context = context
        self._rng = rng

    @classmethod
    def new(
        cls, size: int | str, context: Optional[RollContext] = None, rng: random.Random = rand.random_impl
    ) -> "Die":
        inst = cls(size, [], context=context, rng=rng)
        inst._add_roll()
        return inst

    @property
    def number(self):
        return self.values[-1].total

    @property
    def set(self) -> list[Number]:
        return [self.values[-1]]

    @property
    def children(self) -> list[Number]:
        return []

    def _add_roll(self):
        if self.size != "%" and isinstance(self.size, int) and self.size < 1:
            raise errors.RollValueError("Cannot roll a 0-sided die.")
        if self._context:
            self._context.count_roll()
        if self.size == "%":
            n = Literal(self._rng.randrange(10) * 10, kept=self.kept, annotation=self.annotation)
        elif isinstance(self.size, int):
            # 200ns faster than randint(1, self._size)
            n = Literal(self._rng.randrange(self.size) + 1, kept=self.kept, annotation=self.annotation)
        else:
            raise ValueError(f"Invalid die size value: '{self.size}'")
        self.values.append(n)

    def reroll(self) -> None:
        if self.values:
            self.values[-1].drop()
        self._add_roll()

    def explode(self):
        if self.values:
            self.values[-1].explode()
        # another Die is added by the explode operator

    def force_value(self, new_value: int | float):
        if self.values:
            self.values[-1].update(new_value)

    def __repr__(self):
        return f"<Die size={self.size} values={self.values}>"

    def __neg__(self):
        copy = Die(self.size, self.values, self._context, self._rng)
        copy.values = [-value for value in copy.values]
        return copy

    def set_child(self, index: int, value: Number) -> None:
        raise NotImplementedError


# noinspection PyUnresolvedReferences
# selecting on Dice will always return Die
class SetOperator:  # set_op, dice_op
    """Represents an operation on a set."""

    __slots__ = ("op", "sels")

    op: str
    sels: list["SetSelector"]

    def __init__(self, op: str, sels: list["SetSelector"]):
        """
        :type op: str
        :type sels: list[SetSelector]
        """
        self.op = op
        self.sels = sels

    @classmethod
    def from_ast(cls, node: ast.SetOperator):
        return cls(node.op, [SetSelector.from_ast(n) for n in node.sels])

    @staticmethod
    def filter_die(target: Iterable[Number]) -> set[Die]:
        return set(die for die in target if isinstance(die, Die))

    def select(self, target: Set, max_targets: Optional[int] = None) -> set[Number]:
        """
        Selects the operands in a target set.

        :param target: The source of the operands.
        :type target: Number
        :param max_targets: The maximum number of targets to select.
        :type max_targets: Optional[int]
        """
        out: set[Number] = set()
        for selector in self.sels:
            batch_max = None
            if max_targets is not None:
                batch_max = max_targets - len(out)
                if batch_max == 0:
                    break

            out.update(selector.select(target, max_targets=batch_max))
        return out

    def operate(self, target: Set):
        """
        Operates in place on the values in a target set.

        :param target: The source of the operands.
        :type target: Set
        """
        operations: Mapping[str, Callable[[Set], None]] = {
            # set only
            "k": self.keep,
            "p": self.drop,
            # dice only
            "rr": self.reroll,
            "ro": self.reroll_once,
            "ra": self.explode_once,
            "rs": self.reroll_and_subtract,
            "e": self.explode,
            "mi": self.minimum,
            "ma": self.maximum,
            # expr only
            "red": self.explode_red,
        }

        operations[self.op](target)

    def keep(self, target: Set):
        """
        :type target: Set
        """
        for value in target.keptset:
            if value not in self.select(target):
                value.drop()

    def drop(self, target: Set):
        """
        :type target: Set
        """
        for value in self.select(target):
            value.drop()

    def reroll(self, target: Set):
        """
        :type target: Dice
        """
        if not isinstance(target, Dice):
            return

        to_reroll = self.filter_die(self.select(target))

        while to_reroll:
            for die in to_reroll:
                die.reroll()

            to_reroll = self.filter_die(self.select(target))

    def reroll_once(self, target: Set):
        """
        :type target: Dice
        """
        for die in self.filter_die(self.select(target)):
            die.reroll()

    def explode(self, target: Set):
        """
        :type target: Dice
        """
        if not isinstance(target, Dice):
            return

        to_explode = self.filter_die(self.select(target))
        already_exploded: set[Die] = set()

        while to_explode:
            for die in to_explode:
                die.explode()
                target.roll_another()

            already_exploded.update(to_explode)
            to_explode = self.filter_die(self.select(target)).difference(already_exploded)

    def explode_once(self, target: Set):
        """
        :type target: Dice
        """
        if not isinstance(target, Dice):
            return

        for die in self.filter_die(self.select(target, max_targets=1)):
            die.explode()
            target.roll_another()

    def reroll_and_subtract(self, target: Set):
        if not isinstance(target, Dice):
            return

        for die in self.filter_die(self.select(target, max_targets=1)):
            die.explode()
            target.roll_another(negative=True)

    def explode_red(self, target: Set):
        if not isinstance(target, Dice):
            return

        if not isinstance(target.size, int):
            raise errors.RollValueError(f"{str(target.size)} is not a dice value for red.")

        rolled_values = [value.total for value in target.values]
        rs_count = rolled_values.count(1)
        ra_count = rolled_values.count(target.size)

        if ra_count > 0:
            target.roll_another(negative=False)
        if rs_count > 0:
            target.roll_another(negative=True)

    def minimum(self, target: Set):  # immediate
        """
        :type target: Dice
        """
        selector = self.sels[-1]
        if selector.cat is not None:
            raise errors.RollValueError(f"{str(selector)} is not a valid selector for minimums.")
        the_min = selector.num
        for die in self.filter_die(target.keptset):
            if die.number < the_min:
                die.force_value(the_min)

    def maximum(self, target: Set):  # immediate
        """
        :type target: Dice
        """
        selector = self.sels[-1]
        if selector.cat is not None:
            raise errors.RollValueError(f"{str(selector)} is not a valid selector for maximums.")
        the_max = selector.num
        for die in self.filter_die(target.keptset):
            if die.number > the_max:
                die.force_value(the_max)

    def __str__(self):
        if len(self.sels) == 0:
            return self.op
        return "".join([f"{self.op}{str(sel)}" for sel in self.sels])

    def __repr__(self):
        return f"<SetOperator op={self.op} sels={self.sels}>"


class SetSelector:  # selector
    """Represents a selection on a set."""

    __slots__ = ("cat", "num")

    cat: str | None
    num: int

    def __init__(self, cat: str | None, num: int):
        """
        :type cat: str or None
        :type num: int
        """
        self.cat = cat
        self.num = num

    @classmethod
    def from_ast(cls, node: ast.SetSelector):
        return cls(node.cat, node.num)

    def select(self, target: Set, max_targets: Optional[int] = None) -> set[Number]:
        """
        Selects operands from a target set.

        :param target: The source of the operands.
        :type target: Set
        :param int max_targets: The maximum number of targets to select.
        :return: The targets in the set.
        :rtype: set of Number
        """
        selectors = {"l": self.lowestn, "h": self.highestn, "<": self.lessthan, ">": self.morethan, None: self.literal}

        selected = selectors[self.cat](target)
        if max_targets is not None:
            selected = selected[:max_targets]
        return set(selected)

    def lowestn(self, target: Set):
        return sorted(target.keptset, key=lambda n: n.total)[: self.num]

    def highestn(self, target: Set):
        return sorted(target.keptset, key=lambda n: n.total, reverse=True)[: self.num]

    def lessthan(self, target: Set):
        return [n for n in target.keptset if n.total < self.num]

    def morethan(self, target: Set):
        return [n for n in target.keptset if n.total > self.num]

    def literal(self, target: Set):
        return [n for n in target.keptset if n.total == self.num]

    def __str__(self):
        if self.cat:
            return f"{self.cat}{self.num}"
        return str(self.num)

    def __repr__(self):
        return f"<SetSelector cat={self.cat} num={self.num}>"
