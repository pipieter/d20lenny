import abc

from .expression import Number

__all__ = ["Stringifier", "SimpleStringifier"]

class Stringifier(abc.ABC, metaclass=abc.ABCMeta):
    """
    ABC for string builder from dice result.
    Children should implement all ``_str_*`` methods to transform an Expression into a str.
    """

    def __init__(self) -> None: ...
    def stringify(self, roll: Number) -> str:
        """
        Transforms a rolled expression into a string recursively, bottom-up.

        :param the_roll: The expression to stringify.
        :type the_roll: d20.Expression
        :rtype: str
        """

class SimpleStringifier(Stringifier):
    """
    Example stringifier.
    """
