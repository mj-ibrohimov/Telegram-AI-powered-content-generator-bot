def describe_exception(exc: BaseException) -> str:
    """Formats an exception for logging. Many exceptions (httpx timeouts in
    particular) have an empty str() even though they're meaningful, which
    made past failures show up as blank 'error=' log lines -- always include
    the exception type so the log line is never empty."""
    message = str(exc)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__
