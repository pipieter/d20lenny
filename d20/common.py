from enum import IntEnum

__all__ = ("CritType", "AdvType")


class CritType(IntEnum):
    """
    Integer enumeration representing the crit type of a roll.
    """

    NONE = 0
    CRIT = 1
    FAIL = 2


class AdvType(IntEnum):
    """
    Integer enumeration representing at what advantage a roll should be made at.
    """

    NONE = 0
    ADV = 1
    DIS = -1
