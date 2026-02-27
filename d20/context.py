from .errors import TooManyRolls

__all__ = ("RollContext",)


class RollContext:
    """
    A class to track information about rolls to ensure all rolls halt eventually.

    To use this class, pass an instance to the constructor of :class:`d20.Roller`.
    """

    def __init__(self, max_rolls: int = 1000):
        self.max_rolls = max_rolls
        self.rolls = 0
        self.reset()

    def reset(self):
        """Called at the start of each new roll."""
        self.rolls = 0

    def count_roll(self, n: int = 1):
        """
        Called each time a die is about to be rolled.

        :param int n: The number of rolls about to be made.
        :raises d20.TooManyRolls: if the roller should stop rolling dice because too many have been rolled.
        """
        self.rolls += n
        if self.rolls > self.max_rolls:
            raise TooManyRolls("Too many dice rolled.")
