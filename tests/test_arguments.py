import pytest

from d20 import roll
from d20.enums import Advantage


def test_advantage_d20():
    r = roll("1d20", advantage=Advantage.NONE)
    assert 1 <= r.total <= 20
    assert len(r.rolls) == 1
    assert len(r.warnings) == 0
    assert r.expression == "1d20"

    r = roll("1d20", advantage=Advantage.ADVANTAGE)
    assert 1 <= r.total <= 20
    assert len(r.rolls) == 2
    assert len(r.warnings) == 0
    assert r.total == max(rr.total for rr in r.rolls)
    assert r.expression == "1d20adv2"

    r = roll("1d20", advantage=Advantage.ELVEN_ACCURACY)
    assert 1 <= r.total <= 20
    assert len(r.rolls) == 3
    assert len(r.warnings) == 0
    assert r.total == max(rr.total for rr in r.rolls)
    assert r.expression == "1d20adv3"

    r = roll("1d20", advantage=Advantage.DISADVANTAGE)
    assert 1 <= r.total <= 20
    assert len(r.rolls) == 2
    assert len(r.warnings) == 0
    assert r.total == min(rr.total for rr in r.rolls)
    assert r.expression == "1d20dis2"

    r = roll("1d20+1d20+6", advantage=Advantage.ADVANTAGE)
    assert 8 <= r.total <= 46
    assert len(r.rolls) == 2
    assert len(r.warnings) == 0
    assert r.expression == "1d20adv2 + 1d20 + 6"


# adv/dis should do nothing on non-d20s
def test_advantage_non_d20():
    r = roll("1d6", advantage=Advantage.ADVANTAGE)
    assert 1 <= r.total <= 6
    assert len(r.rolls) == 1
    assert len(r.warnings) == 1
    assert r.expression == "1d6"

    r = roll("1d6", advantage=Advantage.DISADVANTAGE)
    assert 1 <= r.total <= 6
    assert len(r.rolls) == 1
    assert len(r.warnings) == 1
    assert r.expression == "1d6"


@pytest.mark.parametrize(
    "rolls,expr",
    [
        (2, "1d20+4"),
        (2, "4+1d20"),
        (2, "1d20+1d20*4"),
        (2, "1d20*4+1d20"),
        (1, "1d20*4"),
        (1, "1d6"),
        (1, "4"),
    ],
)
def test_advantage_roll_count(rolls: int, expr: str):
    r = roll(expr, advantage=Advantage.ADVANTAGE)
    assert len(r.rolls) == rolls
    assert r.total == max(rr.total for rr in r.rolls)


# if advantage is requested for an expression that already has advantage, a warning is thrown
def test_advantage_and_argument():
    r = roll("1d20adv", advantage=Advantage.ADVANTAGE)
    assert 1 <= r.total <= 20
    assert len(r.rolls) == 2
    assert len(r.warnings) == 1
    assert r.expression == "1d20adv"

    # The first d20 roll already has advantage, give a warning
    r = roll("1d20adv+1d20", advantage=Advantage.ADVANTAGE)
    assert 2 <= r.total <= 40
    assert len(r.rolls) == 2
    assert len(r.warnings) == 1
    assert r.expression == "1d20adv + 1d20"

    # The second d20 roll has advantage, but the first one doesn't
    r = roll("1d20+1d20adv", advantage=Advantage.ADVANTAGE)
    assert 2 <= r.total <= 40
    assert len(r.rolls) == 4
    assert len(r.warnings) == 0
    assert r.expression == "1d20adv2 + 1d20adv"
