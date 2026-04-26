import pytest

from d20 import *


def test_advantage():
    r = roll("1d20", advantage=AdvType.NONE)
    assert 1 <= r.total <= 20
    assert len(r.rolls) == 1
    assert len(r.warnings) == 0

    r = roll("1d20", advantage=AdvType.ADV)
    assert 1 <= r.total <= 20
    assert len(r.rolls) == 2
    assert len(r.warnings) == 0
    assert r.total == max(rr.total for rr in r.rolls)

    r = roll("1d20", advantage=AdvType.DIS)
    assert 1 <= r.total <= 20
    assert len(r.rolls) == 2
    assert len(r.warnings) == 0
    assert r.total == min(rr.total for rr in r.rolls)

    # adv/dis should do nothing on non-d20s
    r = roll("1d6", advantage=AdvType.ADV)
    assert 1 <= r.total <= 6
    assert len(r.rolls) == 1
    assert len(r.warnings) == 1

    r = roll("1d6", advantage=AdvType.DIS)
    assert 1 <= r.total <= 6
    assert len(r.rolls) == 1
    assert len(r.warnings) == 1


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
    r = roll(expr, advantage=AdvType.ADV)
    assert len(r.rolls) == rolls
    assert r.total == max(rr.total for rr in r.rolls)
