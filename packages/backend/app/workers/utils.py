"""Async bridging utilities for Celery workers.

Celery tasks are synchronous, but the ML engine client and several services
expose async APIs. ``run_async`` executes a coroutine to completion from a
synchronous context via :func:`asyncio.run`.

Security/reliability contract (fail-closed):

* If no event loop is running (the normal Celery worker case) the coroutine
  runs on a fresh loop via :func:`asyncio.run`. This is the only supported
  production path.
* If called from within a running event loop the helper raises
  :class:`RuntimeError` instead of silently bridging onto a thread pool. A
  thread-pool bridge would block the caller's loop while waiting on
  ``future.result()`` — a blocking event-loop bridge — and, worse, would
  hide misuse that should be fixed at the call site (callers inside a loop
  should ``await`` the coroutine directly).

The deprecated ``_run_async`` alias is kept for backward compatibility with
existing worker modules.
"""

import asyncio
from typing import Awaitable, TypeVar

T = TypeVar("T")


def run_async(coro: Awaitable[T]) -> T:
    """Run an awaitable to completion from a synchronous caller.

    Raises:
        RuntimeError: if called from within a running event loop. Use ``await``
            at the call site instead of bridging through a thread pool.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    raise RuntimeError(
        "run_async() must not be called from within a running event loop — "
        "await the coroutine directly instead of bridging onto a thread pool "
        "(blocking event-loop bridge detected)"
    )


# Backward-compatible alias kept for existing callers.
_run_async = run_async
