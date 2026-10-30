"""Trying a Google call again when Google says "try again later".

The one rule for which answers are worth a retry and how long to wait,
shared by the Drive door (``coding/drive_door.py``, every command's Drive
call) and ``planars.from_sheets`` (the Colab notebooks, which install only
what they import and have no door). It lives in ``planars/`` so the
notebooks can use it; the door passes its own ``waits`` and ``sleep`` so
tests can make it instant.

Retried: Google's "busy" and server-error answers (``RETRYABLE``: a read
limit reached, a gateway or backend error) and a connection that broke or
timed out before an answer came. Anything else is raised at once.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional, Sequence

RETRYABLE = (429, 500, 502, 503, 504)

# Seconds to wait before each retry. Google's read limit is not a plain
# per-minute window: on 2026-10-21 the status-sheet step was still refused
# after 90s of silence and got through only on the fourth wait, the last the
# old schedule (15, 30, 45, 60) allowed. The longer tail costs nothing when
# Google answers sooner.
WAITS = (15, 30, 45, 60, 60, 60, 60)


def status_of(exc: Exception) -> Optional[int]:
    """The HTTP status of a gspread or Google API client error, else None."""
    try:
        import gspread
    except ImportError:  # pragma: no cover - gspread is installed wherever this runs
        gspread = None
    if gspread is not None and isinstance(exc, gspread.exceptions.APIError):
        return getattr(exc.response, "status_code", None)
    resp = getattr(exc, "resp", None)  # googleapiclient.errors.HttpError
    status = getattr(resp, "status", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def dropped_connection(exc: Exception) -> bool:
    """The connection to Google broke or timed out before an answer came
    (the status-sheet step, 2026-10-22: "Connection reset by peer"; an
    upload of English's chart PDF, 2026-10-25: an SSLError "unexpected eof
    while reading", which the Drive API client raises as is). A certificate
    that fails to verify is an SSLError too, but no retry mends it."""
    import ssl

    import requests  # gspread's transport; imported here, as only this needs it
    if isinstance(exc, ssl.SSLError):
        return not isinstance(exc, ssl.SSLCertVerificationError)
    return isinstance(exc, (ConnectionError, TimeoutError,
                            requests.exceptions.ConnectionError,
                            requests.exceptions.Timeout))


def retry(fn: Callable[[], Any], landed: Optional[Callable[[], Any]] = None, *,
          waits: Optional[Sequence[float]] = None,
          sleep: Optional[Callable[[float], None]] = None) -> Any:
    """Call ``fn``, waiting (``waits``, else ``WAITS``) and trying again on a
    status in ``RETRYABLE`` or a dropped connection.

    ``landed``, for a call that creates something: asked before each retry
    whether the failed attempt went through anyway. If it returns something,
    that is the result and nothing is created a second time.
    """
    waits = WAITS if waits is None else waits
    sleep = sleep or time.sleep
    retries = len(waits) + 1
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - re-raised unless retryable
            status = status_of(exc)
            dropped = dropped_connection(exc)
            if (status not in RETRYABLE and not dropped) or attempt == retries - 1:
                raise
            wait = waits[attempt]
            what = "connection dropped" if dropped else f"API error {status}"
            print(f"    ({what} — waiting {wait}s before retry {attempt + 2}/{retries})")
            sleep(wait)
            if landed is not None:
                found = landed()
                if found is not None:
                    return found
    raise AssertionError("unreachable")
