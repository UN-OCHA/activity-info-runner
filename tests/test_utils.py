from utils import build_nested_dict

def test_build_nested_dict():
    flat = {
        "foo.bar": 1,
        "foo.baz": 2,
        "qux": 3,
        "a.b.c": 4
    }
    expected = {
        "foo": {"bar": 1, "baz": 2},
        "qux": 3,
        "a": {"b": {"c": 4}}
    }
    assert build_nested_dict(flat) == expected
