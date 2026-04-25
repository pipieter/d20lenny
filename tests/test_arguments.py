from d20 import *


def test_advantage():
    r = roll("1d20", advantage=AdvType.ADV)
    assert 1 <= r.total <= 20
    assert r.result.startswith("2d20kh1 ")

    r = roll("1d20", advantage=AdvType.DIS)
    assert 1 <= r.total <= 20
    assert r.result.startswith("2d20kl1 ")

    r = roll("1d20", advantage=AdvType.NONE)
    assert 1 <= r.total <= 20
    assert r.result.startswith("1d20 ")

    # adv/dis should do nothing on non-d20s
    r = roll("1d6", advantage=AdvType.ADV)
    assert 1 <= r.total <= 6
    assert r.result.startswith("1d6 ")

    r = roll("1d6", advantage=AdvType.DIS)
    assert 1 <= r.total <= 6
    assert r.result.startswith("1d6 ")


def test_rolling_ast():
    the_ast = parse("1d20")
    r = roll(the_ast)

    assert 1 <= r.total <= 20
    assert r.result.startswith("1d20 ")
