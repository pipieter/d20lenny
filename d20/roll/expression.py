import abc
import math
import random
from collections.abc import Callable, Mapping
from typing import Sequence
import typing

from .. import diceast as ast, errors as errors
from ..diceast import Node as ASTNode

# region ===== RollContext =====


class RollContext:
    """
    A class to track information about rolls to ensure all rolls halt eventually.

    To use this class, pass an instance to the constructor of :class:`d20.Roller`.
    """

    def __init__(self, rng: random.Random, max_rolls: int = 1000):
        self.rng = rng
        self.max_rolls = max_rolls
        self.rolls = 0

    def _increment(self, n: int = 1) -> None:
        """Called each time a die is about to be rolled to avoid too many rolls."""
        self.rolls += n
        if self.rolls > self.max_rolls:
            raise errors.TooManyRolls("Too many dice rolled.")

    def roll(self, size: ast.DiceSize) -> int:
        """Roll a dice and return its value."""

        if size == 0:
            raise errors.RollValueError("Cannot roll zero-sided die.")

        self._increment(1)
        if size == "%":
            return self.rng.randrange(10) * 10
        else:
            return self.rng.randrange(size) + 1


# endregion ===== RollContext  =====

# region ===== Number ======


class Number(abc.ABC):
    """The base class for all rolled values."""

    _ast: ast.Node

    def __init__(self, ast: ast.Node) -> None:
        self._ast = ast

    @property
    @abc.abstractmethod
    def total(self) -> int:
        """The total value of the Number."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def children(self) -> Sequence["Number"]:
        """The children of the node."""
        raise NotImplementedError

    @abc.abstractmethod
    def __repr__(self) -> str:
        """A Python representation of the Number."""
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self) -> "Number":
        """Return a copy of the Number. The original AST nodes will not be copied to still allow find_from_ast."""
        raise NotImplementedError

    def find_from_ast(self, ast: ASTNode | None) -> "Number | None":
        """Find the child of the evaluated Number from its original AST node, or None if it could not be found."""

        if ast is None:
            return None

        if self._ast == ast:
            return self

        for child in self.children:
            found = child.find_from_ast(ast)
            if found is not None:
                return found

        return None


class Expression(Number):
    """Expressions are usually the root of all Number trees."""

    value: Number

    def __init__(self, value: Number, ast: ast.Node) -> None:
        super().__init__(ast)
        self.value = value

    @property
    def total(self) -> int:
        return self.value.total

    @property
    def children(self) -> Sequence[Number]:
        return [self.value]

    def __repr__(self) -> str:
        return f"<Expression roll={repr(self.value)}/>"

    def copy(self) -> "Expression":
        return Expression(self.value.copy(), self._ast)


class Literal(Number):
    """A literal integer or float."""

    value: int | float

    def __init__(self, value: int | float, ast: ast.Node) -> None:
        super().__init__(ast)
        self.value = value

    @property
    def total(self) -> int:
        return math.floor(self.value)

    @property
    def children(self) -> Sequence[Number]:
        return []

    def __repr__(self) -> str:
        return f"<Literal value={self.value}/>"

    def copy(self) -> "Literal":
        return Literal(self.value, self._ast)


class Parenthetical(Number):
    """Represents a value inside parentheses."""

    value: Number

    def __init__(self, value: Number, ast: ast.Node) -> None:
        super().__init__(ast)
        self.value = value

    @property
    def total(self) -> int:
        return self.value.total

    @property
    def children(self) -> Sequence[Number]:
        return [self.value]

    def __repr__(self) -> str:
        return f"<Parenthetical value={repr(self.value)}/>"

    def copy(self) -> "Parenthetical":
        return Parenthetical(self.value.copy(), self._ast)


class UnOp(Number):
    """Represents a unary operation."""

    op: str  # TODO typing.Literal["+", "-"]
    value: Number

    def __init__(self, op: str, value: Number, ast: ast.Node) -> None:
        super().__init__(ast)
        self.op = op
        self.value = value

    @property
    def total(self) -> int:
        if self.op == "-":
            return -self.value.total
        else:
            return self.value.total

    @property
    def children(self) -> Sequence[Number]:
        return [self.value]

    def __repr__(self) -> str:
        return f"<UnOp op={self.op} value={repr(self.value)}/>"

    def copy(self) -> "UnOp":
        return UnOp(self.op, self.value.copy(), self._ast)


class BinOp(Number):
    """Represents a binary operation."""

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

    def __init__(self, left: Number, op: str, right: Number, ast: ast.Node) -> None:
        super().__init__(ast)
        self.op = op
        self.left = left
        self.right = right

    @property
    def total(self) -> int:
        if self.op not in self.BINARY_OPS:
            raise ValueError(f"Invalid binary operator: '{self.op}'")

        try:
            result = self.BINARY_OPS[self.op](self.left.total, self.right.total)
            return math.floor(result)
        except ZeroDivisionError:
            raise errors.RollValueError("Cannot divide by zero.")

    @property
    def children(self) -> Sequence[Number]:
        return [self.left, self.right]

    def __repr__(self) -> str:
        return f"<BinOp op={self.op} left={repr(self.left)} right={repr(self.right)}/>"

    def copy(self) -> "BinOp":
        return BinOp(self.left.copy(), self.op, self.right.copy(), self._ast)


class Die:
    """Represents a single die that can be rerolled or dropped."""

    kept: bool
    exploded: bool
    size: ast.DiceSize
    values: list[int]  # history of values, the last one is the most recent one
    _context: RollContext

    def __init__(
        self,
        value: int | list[int],
        size: ast.DiceSize,
        context: RollContext,
        kept: bool = True,
        exploded: bool = False,
    ) -> None:
        self.size = size
        self._context = context
        self.kept = kept
        self.exploded = exploded

        if isinstance(value, int):
            self.values = [value]
        else:
            self.values = value

    @property
    def value(self) -> int:
        """The final value of the die."""
        return self.values[-1]

    def reroll(self) -> None:
        """Re-roll the current die."""
        roll = self._context.roll(self.size)
        self.values.append(roll)

    def set_value(self, value: int) -> None:
        """Set the current value of the die forcibly."""
        self.values.append(value)

    def drop(self) -> None:
        """Mark the die as dropped."""
        self.kept = False

    def explode(self) -> None:
        """Mark the die as exploded."""
        self.exploded = True

    @staticmethod
    def new(size: ast.DiceSize, context: RollContext, kept: bool = True, exploded: bool = False) -> "Die":
        """Roll a new die."""
        value = context.roll(size)
        return Die(value, size, context, kept=kept, exploded=exploded)

    def copy(self) -> "Die":
        """Return a copy of the die."""
        return Die(value=[*self.values], size=self.size, context=self._context, kept=self.kept, exploded=self.exploded)


class Dice(Number):
    """Represents a set of dice."""

    dice: list[Die]
    num: int
    size: ast.DiceSize
    operators: list["Operator"]
    _context: RollContext

    def __init__(
        self,
        dice: list[Die],
        num: int,
        size: ast.DiceSize,
        operators: list["Operator"],
        ast: ast.Node,
        context: RollContext,
    ) -> None:
        super().__init__(ast)
        self.dice = dice
        self._context = context

        self.num = num
        self.size = size
        self.operators = operators

    @classmethod
    def _new_single(cls, ast: ast.Dice, context: RollContext) -> "Dice":
        num = ast.num
        size = ast.size
        dice: list[Die] = []
        operators = [Operator.from_ast(op) for op in ast.operations]

        for _ in range(num):
            die = Die.new(size, context)
            dice.append(die)

        result = cls(dice, num, size, operators, ast, context)
        for operator in operators:
            # Skip adv and dis operators, this should be handled by Dice.new
            if operator.op in ["adv", "dis"]:
                continue
            operator.operate(result)

        return result

    @classmethod
    def new(cls, ast: ast.Dice, context: RollContext) -> tuple["Dice", list["Dice"]]:
        """Roll a new set of dice."""
        operators = [Operator.from_ast(op) for op in ast.operations]

        adv: typing.Literal["adv", "dis", None] = None
        roll_count = 1
        for operator in operators:
            if operator.op == "adv" or operator.op == "dis":
                if adv is not None:
                    raise ValueError(f"Encountered {operator.op} in expression, but expression already has {adv}.")
                if len(operator.sels) != 1:
                    raise ValueError(f"Operator {operator.op} expected one selector.")
                if operator.sels[0].cat is not None:
                    raise ValueError(f"Operator {operator.op} only works with .")

                adv = operator.op
                roll_count = operator.sels[0].num

        if roll_count < 1:
            raise ValueError(f"Operator {adv} expected at least one roll.")

        rolls: list[Dice] = []
        for _ in range(roll_count):
            rolls.append(Dice._new_single(ast, context))

        if adv is None:
            roll = rolls[0]
        elif adv == "adv":
            roll = sorted(rolls, key=lambda r: r.total, reverse=True)[0]
        elif adv == "dis":
            roll = sorted(rolls, key=lambda r: r.total, reverse=False)[0]

        return roll, rolls

    @property
    def keptset(self) -> Sequence[Die]:
        """Return a list of all dice that were not dropped."""
        return [die for die in self.dice if die.kept]

    @property
    def total(self) -> int:
        return sum(die.value for die in self.keptset)

    @property
    def children(self) -> Sequence[Number]:
        return []

    def roll_another(self, negative: bool = False) -> None:
        """Roll another die and add it to the dice set."""
        die = Die.new(self.size, self._context)

        if negative:
            die.set_value(-die.value)

        self.dice.append(die)

    def operate(self, operator: "Operator") -> None:
        """Apply an operator to the dice set."""
        operator.operate(self)

    def __repr__(self) -> str:
        operators = "".join(repr(operator) for operator in self.operators)
        return f"<Dice num={self.num} size={self.size} operators={operators} total={self.total}/>"

    def copy(self) -> "Dice":
        dice = [die.copy() for die in self.dice]
        return Dice(dice, self.num, self.size, self.operators, self._ast, self._context)


# endregion ====== Number ======

# region ====== Operators ======


class Operator:
    op: str
    sels: list["Selector"]

    def __init__(self, op: str, sels: list["Selector"]) -> None:
        self.op = op
        self.sels = sels

    @classmethod
    def from_ast(cls, ast: ast.Operator) -> "Operator":
        op = ast.op
        sels = [Selector.from_ast(sel) for sel in ast.sels]
        return cls(op, sels)

    def operate(self, target: Dice) -> None:
        operations: Mapping[str, Callable[[Dice], None]] = {
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

    def select(self, target: Dice) -> set[Die]:
        """Selects the operands in a target set."""

        out: set[Die] = set()
        for selector in self.sels:
            out.update(selector.select(target))

        return out

    def keep(self, target: Dice) -> None:
        for value in target.keptset:
            if value not in self.select(target):
                value.drop()

    def drop(self, target: Dice) -> None:
        for value in self.select(target):
            value.drop()

    def reroll(self, target: Dice) -> None:
        to_reroll = self.select(target)

        while to_reroll:
            for die in to_reroll:
                die.reroll()

            to_reroll = self.select(target)

    def reroll_once(self, target: Dice) -> None:
        for die in self.select(target):
            die.reroll()

    def explode(self, target: Dice) -> None:
        to_explode = self.select(target)
        already_exploded: set[Die] = set()

        while to_explode:
            for die in to_explode:
                if not die.exploded:
                    die.explode()
                    target.roll_another()

            already_exploded.update(to_explode)
            to_explode = (self.select(target)).difference(already_exploded)

    def explode_once(self, target: Dice) -> None:
        for die in self.select(target):
            if not die.exploded:
                die.explode()
                target.roll_another()
                return

    def reroll_and_subtract(self, target: Dice) -> None:
        for die in self.select(target):
            if not die.exploded:
                die.explode()
                target.roll_another(negative=True)
                return

    def explode_red(self, target: Dice) -> None:
        if target.size == "%":
            size = 100
        else:
            size = target.size

        rolled_values = [die.value for die in target.dice]
        rs_count = rolled_values.count(1)
        ra_count = rolled_values.count(size)

        if ra_count > 0:
            target.roll_another(negative=False)
        if rs_count > 0:
            target.roll_another(negative=True)

    def minimum(self, target: Dice) -> None:
        """
        :type target: Dice
        """
        selector = self.sels[-1]
        if selector.cat is not None:
            raise errors.RollValueError(f"{str(selector)} is not a valid selector for minimums.")
        the_min = selector.num
        for die in target.keptset:
            if die.value < the_min:
                die.set_value(the_min)

    def maximum(self, target: Dice) -> None:
        """
        :type target: Dice
        """
        selector = self.sels[-1]
        if selector.cat is not None:
            raise errors.RollValueError(f"{str(selector)} is not a valid selector for maximums.")
        the_max = selector.num
        for die in target.keptset:
            if die.value > the_max:
                die.set_value(the_max)

    def __str__(self):
        if len(self.sels) == 0:
            return self.op
        return "".join([f"{self.op}{str(sel)}" for sel in self.sels])

    def __repr__(self):
        return f"<SetOperator op={self.op} sels={self.sels}>"


class Selector:
    """Represents a selection on a dice set."""

    cat: str | None
    num: int

    def __init__(self, cat: str | None, num: int) -> None:
        self.cat = cat
        self.num = num

    @classmethod
    def from_ast(cls, ast: ast.Selector) -> "Selector":
        cat = ast.cat
        num = ast.num
        return cls(cat, num)

    def select(self, target: Dice) -> set[Die]:
        selectors = {"l": self.lowestn, "h": self.highestn, "<": self.lessthan, ">": self.morethan, None: self.literal}
        selected = selectors[self.cat](target)

        return set(selected)

    def lowestn(self, target: Dice) -> Sequence[Die]:
        return sorted(target.keptset, key=lambda n: n.value)[: self.num]

    def highestn(self, target: Dice) -> Sequence[Die]:
        return sorted(target.keptset, key=lambda n: n.value, reverse=True)[: self.num]

    def lessthan(self, target: Dice) -> Sequence[Die]:
        return [n for n in target.keptset if n.value < self.num]

    def morethan(self, target: Dice) -> Sequence[Die]:
        return [n for n in target.keptset if n.value > self.num]

    def literal(self, target: Dice) -> Sequence[Die]:
        return [n for n in target.keptset if n.value == self.num]

    def __str__(self):
        if self.cat:
            return f"{self.cat}{self.num}"
        return str(self.num)

    def __repr__(self):
        return f"<SetSelector cat={self.cat} num={self.num}>"


# endregion ===== Operators ======
