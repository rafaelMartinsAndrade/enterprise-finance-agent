import asyncio
import time
from collections.abc import Awaitable, Callable

from app.schemas.jobs import AsyncTaskResult


async def run_limited_concurrency(
    *,
    delays_ms: list[int],
    max_concurrency: int,
    timeout_ms: int,
    worker: Callable[[str, int, int, asyncio.Semaphore], Awaitable[AsyncTaskResult]],
) -> list[AsyncTaskResult]:
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [
        asyncio.create_task(worker(f"task-{index + 1}", delay_ms, timeout_ms, semaphore))
        for index, delay_ms in enumerate(delays_ms)
    ]
    return await asyncio.gather(*tasks)


async def simulate_io_task(
    task_id: str,
    delay_ms: int,
    timeout_ms: int,
    semaphore: asyncio.Semaphore,
) -> AsyncTaskResult:
    start = time.perf_counter()
    try:
        async with semaphore:
            await asyncio.wait_for(asyncio.sleep(delay_ms / 1000), timeout=timeout_ms / 1000)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return AsyncTaskResult(
                task_id=task_id,
                delay_ms=delay_ms,
                status="completed",
                elapsed_ms=elapsed_ms,
                detail="I/O-style task finished within timeout.",
            )
    except asyncio.TimeoutError:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return AsyncTaskResult(
            task_id=task_id,
            delay_ms=delay_ms,
            status="timed_out",
            elapsed_ms=elapsed_ms,
            detail="Task exceeded timeout and was interrupted safely.",
        )
    except asyncio.CancelledError:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return AsyncTaskResult(
            task_id=task_id,
            delay_ms=delay_ms,
            status="cancelled",
            elapsed_ms=elapsed_ms,
            detail="Task was cancelled before finishing.",
        )
