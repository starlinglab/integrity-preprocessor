from .context import validate


def test_shorten():
    shorten = validate.Validate._shorten
    short_len = validate.Validate.short_len
    assert shorten([]) == []
    assert shorten({}) == {}
    assert shorten({"test": "a" * short_len}) == {"test": "a" * short_len}
    assert shorten({"test": "a" * (short_len + 1)}) == {
        "test": "a" * short_len + "[...]"
    }
    assert shorten({"test": ["a" * (short_len + 1), "b"]}) == {
        "test": ["a" * short_len + "[...]", "b"]
    }
    assert shorten({"a": {"b": "c" * (short_len + 1)}}) == {
        "a": {"b": "c" * short_len + "[...]"}
    }
    assert shorten([{"a": {"b": "c" * (short_len + 1)}}]) == [
        {"a": {"b": "c" * short_len + "[...]"}}
    ]
