import httpx
import pytest

from app.errors import describe_exception


def test_describe_exception_includes_type_and_message():
    exc = ValueError("bad value")
    assert describe_exception(exc) == "ValueError: bad value"


def test_describe_exception_never_blank_for_httpx_timeout():
    exc = httpx.ReadTimeout("")
    result = describe_exception(exc)
    assert result
    assert "ReadTimeout" in result


def test_describe_exception_bare_exception_with_no_message():
    exc = RuntimeError()
    assert describe_exception(exc) == "RuntimeError"
