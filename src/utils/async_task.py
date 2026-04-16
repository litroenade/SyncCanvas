import asyncio
import time
import traceback
from abc import ABC, abstractmethod
from typing import List, Optional

from src.infra.logging import get_logger

logger = get_logger(__name__)


class AsyncTask(ABC):
    """Base class for simple periodic background tasks."""

    def __init__(self, name: str, interval: float = 60.0) -> None:
        self.name = name
        self.interval = interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the periodic task loop if it is not already running."""

        if self._running:
            logger.warning("Task %s is already running", self.name)
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Started task %s with interval=%s", self.name, self.interval)

    async def stop(self) -> None:
        """Stop the task loop and await task cancellation."""

        if not self._running:
            return

        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Stopped task %s", self.name)

    async def _run_loop(self) -> None:
        """Run the task repeatedly until stopped."""

        while self._running:
            try:
                start_time = time.time()
                await self.run()
                elapsed = time.time() - start_time
                await asyncio.sleep(max(0.0, self.interval - elapsed))
            except asyncio.CancelledError:
                break
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Task %s failed: %s", self.name, exc)
                logger.debug(traceback.format_exc())
                await asyncio.sleep(min(self.interval, 10.0))

    @abstractmethod
    async def run(self) -> None:
        """Execute one task iteration."""


class AsyncTaskManager:
    """Manage a collection of periodic async tasks."""

    def __init__(self) -> None:
        self._tasks: List[AsyncTask] = []

    def add_task(self, task: AsyncTask) -> None:
        self._tasks.append(task)
        logger.debug("Registered async task %s", task.name)

    async def start_all(self) -> None:
        logger.info("Starting %s async task(s)", len(self._tasks))
        for task in self._tasks:
            await task.start()

    async def stop_all(self) -> None:
        logger.info("Stopping %s async task(s)", len(self._tasks))
        for task in self._tasks:
            await task.stop()


async_task_manager = AsyncTaskManager()
