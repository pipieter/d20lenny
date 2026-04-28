from _typeshed import Incomplete
from typing import Any

__all__ = ['RollError', 'RollSyntaxError', 'RollValueError', 'TooManyRolls']

class RollError(Exception):
    def __init__(self, msg: str) -> None: ...

class RollSyntaxError(RollError):
    line: Incomplete
    col: Incomplete
    got: Incomplete
    expected: Incomplete
    def __init__(self, line: int, col: int, got: Any, expected: Any) -> None: ...

class RollValueError(RollError): ...
class TooManyRolls(RollError): ...
