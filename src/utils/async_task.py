"""模块名称：async_task
主要功能：异步任务管理基础架构

定义 AsyncTask 基类和 AsyncTaskManager，用于统一管理后台周期性任务。
"""

import asyncio
import time
import traceback
from abc import ABC, abstractmethod
from typing import List, Optional

from src.logger import get_logger

logger = get_logger(__name__)


class AsyncTask(ABC):
    """异步任务基类

    所有周期性后台任务应继承此类。

    Attributes:
        name (str): 任务名称
        interval (float): 执行间隔（秒）
        _running (bool): 运行状态标志
        _task (asyncio.Task): 任务协程对象
    """

    def __init__(self, name: str, interval: float = 60.0):
        """初始化异步任务

        Args:
            name: 任务名称
            interval: 执行间隔（秒），默认 60 秒
        """
        self.name = name
        self.interval = interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动任务"""
        if self._running:
            logger.warning(f"任务 '{self.name}' 已经在运行中")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"任务 '{self.name}' 已启动，间隔 {self.interval} 秒")

    async def stop(self) -> None:
        """停止任务"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info(f"任务 '{self.name}' 已停止")

    async def _run_loop(self) -> None:
        """任务运行循环"""
        while self._running:
            try:
                start_time = time.time()
                await self.run()
                elapsed = time.time() - start_time

                # 计算剩余等待时间
                wait_time = max(0.0, self.interval - elapsed)
                await asyncio.sleep(wait_time)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"任务 '{self.name}' 执行异常: {e}")
                logger.debug(traceback.format_exc())
                # 发生异常后等待一段时间再重试，避免死循环刷日志
                await asyncio.sleep(min(self.interval, 10.0))

    @abstractmethod
    async def run(self) -> None:
        """任务具体逻辑

        子类必须实现此方法。
        """
        pass


class AsyncTaskManager:
    """异步任务管理器

    统一管理所有 AsyncTask 实例的启动和停止。

    Attributes:
        _tasks (List[AsyncTask]): 任务列表
    """

    def __init__(self):
        """初始化管理器"""
        self._tasks: List[AsyncTask] = []

    def add_task(self, task: AsyncTask) -> None:
        """添加任务

        Args:
            task: AsyncTask 实例
        """
        self._tasks.append(task)
        logger.debug(f"已添加任务: {task.name}")

    async def start_all(self) -> None:
        """启动所有任务"""
        logger.info("正在启动所有后台任务...")
        for task in self._tasks:
            await task.start()

    async def stop_all(self) -> None:
        """停止所有任务"""
        logger.info("正在停止所有后台任务...")
        for task in self._tasks:
            await task.stop()


# 全局任务管理器实例
async_task_manager = AsyncTaskManager()
