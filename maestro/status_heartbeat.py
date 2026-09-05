"""Live status updates while long cursor-agent / NL work runs."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

import discord

logger = logging.getLogger(__name__)

StatusCallback = Callable[[str], Awaitable[None]]

_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


def format_elapsed(seconds: float) -> str:
    s = max(0, int(seconds))
    if s < 60:
        return f"{s}s"
    m, rem = divmod(s, 60)
    if m < 60:
        return f"{m}m {rem:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


class StatusHeartbeat:
    """Edit a Discord status line on an interval so the operator sees activity.

    Edits are serialized. After ``stop()``, heartbeat ticks must not overwrite
    the final status (fixes a race where an in-flight ``still running`` edit
    landed after the agent reply).
    """

    def __init__(
        self,
        set_status: StatusCallback,
        *,
        headline: str,
        detail: str = "Working",
        interval_seconds: float = 8.0,
        channel: discord.abc.Messageable | None = None,
    ) -> None:
        self._set_status = set_status
        self.headline = headline
        self.detail = detail
        self.interval_seconds = interval_seconds
        self._channel = channel
        self._done = False
        self._started = time.monotonic()
        self._tick = 0
        self._task: asyncio.Task[None] | None = None
        self._typing_task: asyncio.Task[None] | None = None
        self._edit_lock = asyncio.Lock()
        self._generation = 0

    def _line(self) -> str:
        frame = _FRAMES[self._tick % len(_FRAMES)]
        elapsed = format_elapsed(time.monotonic() - self._started)
        return (
            f"{self.headline}\n"
            f"{frame} **{self.detail}** · `{elapsed}` elapsed · still running…"
        )

    async def _heartbeat_edit(self, content: str, *, generation: int) -> None:
        """Apply a heartbeat edit only if this generation is still active."""
        async with self._edit_lock:
            if self._done or generation != self._generation:
                return
            await self._set_status(content)

    async def start(self) -> None:
        self._started = time.monotonic()
        self._done = False
        self._generation += 1
        gen = self._generation
        try:
            await self._heartbeat_edit(self._line(), generation=gen)
        except Exception as e:
            logger.warning("status heartbeat initial edit failed: %s", e)
        self._task = asyncio.create_task(self._loop(gen), name="maestro-status-heartbeat")
        if self._channel is not None:
            self._typing_task = asyncio.create_task(
                self._typing_loop(), name="maestro-typing"
            )

    async def _loop(self, generation: int) -> None:
        try:
            while not self._done and generation == self._generation:
                await asyncio.sleep(self.interval_seconds)
                if self._done or generation != self._generation:
                    return
                self._tick += 1
                try:
                    await self._heartbeat_edit(self._line(), generation=generation)
                except Exception as e:
                    logger.warning("status heartbeat edit failed: %s", e)
        except asyncio.CancelledError:
            return

    async def _typing_loop(self) -> None:
        ch = self._channel
        if ch is None:
            return
        try:
            while not self._done:
                try:
                    async with ch.typing():
                        await asyncio.sleep(7.5)
                except (discord.HTTPException, AttributeError) as e:
                    logger.debug("typing indicator failed: %s", e)
                    await asyncio.sleep(self.interval_seconds)
        except asyncio.CancelledError:
            return

    def update_detail(self, detail: str) -> None:
        self.detail = detail

    async def stop(self) -> None:
        """Stop ticks and wait so no in-flight heartbeat edit can land later."""
        self._done = True
        self._generation += 1
        for task in (self._task, self._typing_task):
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._task = None
        self._typing_task = None
        # Drain any heartbeat edit that held the lock before _done flipped.
        async with self._edit_lock:
            return
