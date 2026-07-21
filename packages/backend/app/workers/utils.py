import asyncio
import concurrent.futures
from typing import TypeVar

T = TypeVar("T")

_RUN_ASYNC_POOL: concurrent.futures.ThreadPoolExecutor = (
    concurrent.futures.ThreadPoolExecutor(
        max_workers=4,
        thread_name_prefix="run_async",
    )
)


def _run_async(coro) -> T:
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            future = _RUN_ASYNC_POOL.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        pass
    return asyncio.run(coro)
