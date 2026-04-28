import abc
from .expression import Number

__all__ = ['Stringifier', 'SimpleStringifier']

class Stringifier(abc.ABC, metaclass=abc.ABCMeta):
    def __init__(self) -> None: ...
    def stringify(self, roll: Number) -> str: ...

class SimpleStringifier(Stringifier): ...
