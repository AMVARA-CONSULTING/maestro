"""Per-thread busy flag + FIFO queue for persisted cursor-agent sessions."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

QueueHandler = Callable[[int, str], Awaitable[None]]  # thread_id, text
IdleHandler = Callable[[int], None]  # thread_id


@dataclass
class ThreadQueueState:
    busy: bool = False
    queue: deque[str] = field(default_factory=deque)
    worker: asyncio.Task[None] | None = None


class ThreadQueueManager:
    def __init__(self, *, max_queue: int = 5) -> None:
        self.max_queue = max_queue
        self._states: dict[int, ThreadQueueState] = {}
        self._lock = asyncio.Lock()
        self._handler: QueueHandler | None = None
        self._on_idle: IdleHandler | None = None

    def set_handler(self, handler: QueueHandler) -> None:
        self._handler = handler

    def set_on_idle(self, handler: IdleHandler) -> None:
        self._on_idle = handler

    def _state(self, thread_id: int) -> ThreadQueueState:
        if thread_id not in self._states:
            self._states[thread_id] = ThreadQueueState()
        return self._states[thread_id]

    def is_busy(self, thread_id: int) -> bool:
        return self._state(thread_id).busy

    def queue_len(self, thread_id: int) -> int:
        return len(self._state(thread_id).queue)

    def busy_count(self) -> int:
        return sum(1 for st in self._states.values() if st.busy)

    async def drop_pending(self, thread_id: int) -> tuple[bool, int]:
        """Clear pending FIFO for one thread. Returns (was_busy, dropped_count).

        Does not cancel the asyncio worker: the caller stops that thread's
        cursor-agent process so the handler exits cleanly (AgentCancelled).
        """
        async with self._lock:
            st = self._state(thread_id)
            dropped = len(st.queue)
            st.queue.clear()
            return st.busy, dropped

    async def enqueue(self, thread_id: int, text: str) -> tuple[str, int]:
        """Enqueue work. Returns (status, queue_position).

        status: started | queued | full
        queue_position: 1-based position in queue when queued; 0 if started immediately.
        """
        task = text.strip()
        if not task:
            return "full", 0

        async with self._lock:
            st = self._state(thread_id)
            if not st.busy and not st.queue:
                st.busy = True
                st.worker = asyncio.create_task(
                    self._run_loop(thread_id, task),
                    name=f"maestro-thread-{thread_id}",
                )
                return "started", 0
            if len(st.queue) >= self.max_queue:
                return "full", len(st.queue)
            st.queue.append(task)
            pos = len(st.queue)
            return "queued", pos

    async def _run_loop(self, thread_id: int, first: str) -> None:
        handler = self._handler
        if handler is None:
            async with self._lock:
                self._state(thread_id).busy = False
            self._emit_idle(thread_id)
            return

        current = first
        while current is not None:
            try:
                await handler(thread_id, current)
            except Exception:
                logger.exception("thread queue handler failed thread=%s", thread_id)
            became_idle = False
            async with self._lock:
                st = self._state(thread_id)
                if st.queue:
                    current = st.queue.popleft()
                else:
                    st.busy = False
                    st.worker = None
                    current = None
                    became_idle = True
            if became_idle:
                self._emit_idle(thread_id)

    def _emit_idle(self, thread_id: int) -> None:
        if self._on_idle is None:
            return
        try:
            self._on_idle(thread_id)
        except Exception:
            logger.exception("thread queue on_idle failed thread=%s", thread_id)

    def clear(self, thread_id: int) -> None:
        st = self._states.pop(thread_id, None)
        if st is None:
            return
        st.queue.clear()
        if st.worker is not None and not st.worker.done():
            st.worker.cancel()
