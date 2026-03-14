from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future
from typing import Any, Coroutine


class BackgroundRunner:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="mailbot-worker")
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if not self._loop:
            raise RuntimeError("Background loop is not running.")
        return self._loop

    def submit(self, coro: Coroutine[Any, Any, Any]) -> Future:
        self.start()
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self) -> None:
        if not self._loop:
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2)
        self._loop = None
        self._thread = None
        self._ready.clear()

