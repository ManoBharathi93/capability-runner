"""Run async browser/core operations on one persistent event loop."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from types import TracebackType
from typing import Any


class AsyncCoreRunner:
    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._timeout_seconds = timeout_seconds
        self._ready = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        self._ready.wait()

    def run[T](self, operation: Coroutine[Any, Any, T]) -> T:
        loop = self._loop
        if loop is None or loop.is_closed():
            operation.close()
            raise RuntimeError("async core runner is closed")
        future = asyncio.run_coroutine_threadsafe(operation, loop)
        return future.result(timeout=self._timeout_seconds)

    def close(self) -> None:
        loop = self._loop
        if loop is None:
            return
        loop.call_soon_threadsafe(loop.stop)
        self._thread.join(timeout=self._timeout_seconds)
        if self._thread.is_alive():
            raise RuntimeError("async core runner did not stop")
        self._loop = None

    def __enter__(self) -> AsyncCoreRunner:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _serve(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        try:
            loop.run_forever()
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
