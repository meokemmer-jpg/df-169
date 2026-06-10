import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
import importlib

mod = importlib.import_module("169")
factorize = mod.factorize
is_perfect_square = mod.is_perfect_square
mission_signature = mod.mission_signature


def test_df_169_core_behavior():
    assert factorize(169) == {13: 2}
    assert is_perfect_square(169) is True
    assert mission_signature(169) == "169=13^2;square=yes"


def test_additional_cases_and_validation():
    assert factorize(84) == {2: 2, 3: 1, 7: 1}
    assert is_perfect_square(170) is False

    try:
        factorize(0)
    except ValueError as exc:
        assert "positive integer" in str(exc)
    else:
        assert False, "factorize(0) should raise ValueError"
