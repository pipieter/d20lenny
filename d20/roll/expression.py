import abc
import math
from collections.abc import Callable, Mapping
from typing import Sequence

from .. import diceast as ast, errors as errors
from ..context import RollContext
from ..diceast import Node as ASTNode

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
        raise NotImplementedError

    def find_from_ast(self, ast: ASTNode) -> "Number | None":
        if self._ast == ast:
            return self

        for child in self.children:
            found = child.find_from_ast(ast)
            if found is not None:
                return found

        return None


class Expression(Number):
    """Expressions are usually the root of all Number trees."""

    roll: Number

    def __init__(self, roll: Number, ast: ast.Node) -> None:
        super().__init__(ast)
        self.roll = roll

    @property
    def total(self) -> int:
        return self.roll.total

    @property
    def children(self) -> Sequence[Number]:
        return [self.roll]

    def __repr__(self) -> str:
        return f"<Expression roll={repr(self.roll)}/>"

    def copy(self) -> "Expression":
        return Expression(self.roll.copy(), self._ast)


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
    """Represents a single die."""

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
    def value(self):
        return self.values[-1]

    def reroll(self) -> None:
        roll = self._context.roll(self.size)
        self.values.append(roll)

    def set_value(self, value: int):
        self.values.append(value)

    def drop(self):
        self.kept = False

    def explode(self):
        self.exploded = True

    @staticmethod
    def new(size: ast.DiceSize, context: RollContext, kept: bool = True, exploded: bool = False) -> "Die":
        value = context.roll(size)
        return Die(value, size, context, kept=kept, exploded=exploded)

    def copy(self) -> "Die":
        return Die(value=[*self.values], size=self.size, context=self._context, kept=self.kept, exploded=self.exploded)


class Dice(Number):
    """Represents a set of dice."""

    dice: list[Die]
    num: int
    size: ast.DiceSize
    _context: RollContext

    def __init__(self, dice: list[Die], num: int, size: ast.DiceSize, ast: ast.Node, context: RollContext) -> None:
        super().__init__(ast)
        self.dice = dice
        self._context = context

        self.num = num
        self.size = size

    @classmethod
    def new(cls, ast: ast.Dice, context: RollContext) -> "Dice":
        num = ast.num
        size = ast.size
        dice: list[Die] = []

        for _ in range(num):
            die = Die.new(size, context)
            dice.append(die)

        return cls(dice, num, size, ast, context)

    @property
    def total(self) -> int:
        return sum(die.value for die in self.dice)

    @property
    def children(self) -> Sequence[Number]:
        return []

    def __repr__(self) -> str:
        return f"<OperatedDice num={self.num} size={self.size} />"

    def copy(self) -> "Dice":
        dice = [die.copy() for die in self.dice]
        return Dice(dice, self.num, self.size, self._ast, self._context)


class OperatedDice(Number):
    """Represents a set of dice with operations."""

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
        self.num = num
        self.size = size
        self.operators = operators
        self._context = context

    @classmethod
    def new(cls, ast: ast.OperatedDice, context: RollContext) -> "OperatedDice":
        num = ast.num
        size = ast.size
        dice: list[Die] = []
        operators = [Operator.from_ast(op) for op in ast.operations]

        for _ in range(num):
            die = Die.new(size, context)
            dice.append(die)

        result = cls(dice, num, size, operators, ast, context)
        for operator in operators:
            operator.operate(result)

        return result

    def roll_another(self, negative: bool = False):
        die = Die.new(self.size, self._context)

        if negative:
            die.set_value(-die.value)

        self.dice.append(die)

    @property
    def total(self) -> int:
        return sum(die.value for die in self.keptset)

    @property
    def children(self) -> Sequence[Number]:
        return []

    @property
    def keptset(self) -> Sequence[Die]:
        return [die for die in self.dice if die.kept]

    def operate(self, operator: "Operator"):
        operator.operate(self)

    def __repr__(self) -> str:
        operators = "".join(repr(operator) for operator in self.operators)
        return f"<OperatedDice num={self.num} size={self.size} operators={operators}/>"

    def copy(self) -> "OperatedDice":
        dice = [die.copy() for die in self.dice]
        return OperatedDice(dice, self.num, self.size, self.operators, self._ast, self._context)


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

    def operate(self, target: OperatedDice) -> None:
        operations: Mapping[str, Callable[[OperatedDice], None]] = {
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

    def select(self, target: OperatedDice) -> set[Die]:
        """Selects the operands in a target set."""

        out: set[Die] = set()
        for selector in self.sels:
            out.update(selector.select(target))

        return out

    def keep(self, target: OperatedDice):
        for value in target.keptset:
            if value not in self.select(target):
                value.drop()

    def drop(self, target: OperatedDice):
        for value in self.select(target):
            value.drop()

    def reroll(self, target: OperatedDice):
        to_reroll = self.select(target)

        while to_reroll:
            for die in to_reroll:
                die.reroll()

            to_reroll = self.select(target)

    def reroll_once(self, target: OperatedDice):
        for die in self.select(target):
            die.reroll()

    def explode(self, target: OperatedDice):
        to_explode = self.select(target)
        already_exploded: set[Die] = set()

        while to_explode:
            for die in to_explode:
                if not die.exploded:
                    die.explode()
                    target.roll_another()

            already_exploded.update(to_explode)
            to_explode = (self.select(target)).difference(already_exploded)

    def explode_once(self, target: OperatedDice):
        for die in self.select(target):
            if not die.exploded:
                die.explode()
                target.roll_another()
                return

    def reroll_and_subtract(self, target: OperatedDice):
        for die in self.select(target):
            if not die.exploded:
                die.explode()
                target.roll_another(negative=True)
                return

    def explode_red(self, target: OperatedDice):
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

    def minimum(self, target: OperatedDice):
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

    def maximum(self, target: OperatedDice):
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

    def select(self, target: OperatedDice) -> set[Die]:
        selectors = {"l": self.lowestn, "h": self.highestn, "<": self.lessthan, ">": self.morethan, None: self.literal}
        selected = selectors[self.cat](target)

        return set(selected)

    def lowestn(self, target: OperatedDice):
        return sorted(target.keptset, key=lambda n: n.value)[: self.num]

    def highestn(self, target: OperatedDice):
        return sorted(target.keptset, key=lambda n: n.value, reverse=True)[: self.num]

    def lessthan(self, target: OperatedDice):
        return [n for n in target.keptset if n.value < self.num]

    def morethan(self, target: OperatedDice):
        return [n for n in target.keptset if n.value > self.num]

    def literal(self, target: OperatedDice):
        return [n for n in target.keptset if n.value == self.num]

    def __str__(self):
        if self.cat:
            return f"{self.cat}{self.num}"
        return str(self.num)

    def __repr__(self):
        return f"<SetSelector cat={self.cat} num={self.num}>"


# endregion ===== Operators ======
