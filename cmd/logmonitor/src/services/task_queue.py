#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步任务队列模块
使用线程池实现异步任务处理
"""
import logging
import threading
import queue
import time
from typing import Callable, Any, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """任务数据类"""
    task_id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    callback: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    priority: int = 0


class TaskQueue:
    """异步任务队列类"""

    def __init__(self, max_workers: int = 4, max_queue_size: int = 1000):
        """
        初始化任务队列

        Args:
            max_workers: 最大工作线程数
            max_queue_size: 最大队列大小
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._task_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self._running = False
        self._worker_thread = None
        self._tasks: Dict[str, Future] = {}
        self._lock = threading.Lock()
        self._task_counter = 0

        # 任务统计
        self._stats = {
            'completed': 0,
            'failed': 0,
            'pending': 0
        }
        self._stats_lock = threading.Lock()

    def start(self):
        """启动任务队列"""
        if not self._running:
            self._running = True
            self._worker_thread = threading.Thread(target=self._process_tasks, daemon=True)
            self._worker_thread.start()
            logger.info(f"异步任务队列已启动，工作线程数: {self._executor._max_workers}")

    def stop(self, wait: bool = True, timeout: float = 30):
        """
        停止任务队列

        Args:
            wait: 是否等待任务完成
            timeout: 等待超时时间（秒）
        """
        if self._running:
            self._running = False

            if wait:
                self._task_queue.join()

            self._executor.shutdown(wait=wait)

            if self._worker_thread:
                self._worker_thread.join(timeout=timeout)

            logger.info("异步任务队列已停止")

    def submit(self, func: Callable, *args,
               callback: Optional[Callable] = None,
               priority: int = 0,
               **kwargs) -> str:
        """
        提交任务

        Args:
            func: 要执行的函数
            *args: 位置参数
            callback: 回调函数
            priority: 任务优先级
            **kwargs: 关键字参数

        Returns:
            任务ID
        """
        with self._lock:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}_{int(time.time() * 1000)}"

        task = Task(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            callback=callback,
            priority=priority
        )

        try:
            self._task_queue.put((-priority, task), block=False)

            with self._stats_lock:
                self._stats['pending'] = self._task_queue.qsize()

            logger.debug(f"任务已提交: {task_id}")
            return task_id
        except queue.Full:
            logger.error("任务队列已满，无法添加新任务")
            raise RuntimeError("任务队列已满")

    def submit_async(self, func: Callable, *args, **kwargs) -> Future:
        """
        异步提交任务（使用线程池）

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Future对象
        """
        future = self._executor.submit(func, *args, **kwargs)
        future.add_done_callback(self._handle_future_complete)
        return future

    def _handle_future_complete(self, future: Future):
        """处理Future完成回调"""
        try:
            result = future.result()
            with self._stats_lock:
                self._stats['completed'] += 1
            logger.debug(f"Future任务完成: {result}")
        except Exception as e:
            with self._stats_lock:
                self._stats['failed'] += 1
            logger.error(f"Future任务失败: {e}")

    def _process_tasks(self):
        """处理队列中的任务"""
        while self._running:
            try:
                priority, task = self._task_queue.get(timeout=1)

                with self._lock:
                    future = self._executor.submit(self._execute_task, task)
                    self._tasks[task.task_id] = future

                self._task_queue.task_done()

                with self._stats_lock:
                    self._stats['pending'] = self._task_queue.qsize()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"处理任务时出错: {e}")

    def _execute_task(self, task: Task) -> Any:
        """执行任务"""
        logger.debug(f"执行任务: {task.task_id}")

        try:
            result = task.func(*task.args, **task.kwargs)

            if task.callback:
                try:
                    task.callback(result)
                except Exception as e:
                    logger.error(f"任务回调执行失败: {e}")

            with self._stats_lock:
                self._stats['completed'] += 1

            logger.debug(f"任务完成: {task.task_id}")
            return result

        except Exception as e:
            with self._stats_lock:
                self._stats['failed'] += 1

            logger.error(f"任务执行失败: {task.task_id}, 错误: {e}")
            raise

        finally:
            # 任务结束（无论成功/失败）立即从字典移除，防止 Future 堆积导致内存泄漏
            with self._lock:
                self._tasks.pop(task.task_id, None)

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态（任务完成后会从字典移除，此时返回 completed）"""
        with self._lock:
            if task_id not in self._tasks:
                # 任务完成后会被移除，此处视为已完成
                return {'status': 'completed'}

            future = self._tasks[task_id]

            if future.done():
                if future.exception():
                    return {
                        'status': 'failed',
                        'error': str(future.exception())
                    }
                else:
                    return {
                        'status': 'completed',
                        'result': str(future.result())[:100]
                    }
            else:
                return {
                    'status': 'running'
                }

    def get_stats(self) -> Dict:
        """获取队列统计信息"""
        with self._stats_lock:
            return {
                **self._stats,
                'queue_size': self._task_queue.qsize(),
                'active_workers': len([f for f in self._tasks.values() if not f.done()])
            }

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            if task_id in self._tasks:
                future = self._tasks[task_id]
                cancelled = future.cancel()
                if cancelled:
                    logger.info(f"任务已取消: {task_id}")
                return cancelled
        return False


# 全局任务队列实例
_global_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """获取全局任务队列实例"""
    global _global_task_queue
    if _global_task_queue is None:
        _global_task_queue = TaskQueue(max_workers=4)
        _global_task_queue.start()
    return _global_task_queue


def submit_task(func: Callable, *args, **kwargs) -> str:
    """提交任务（便捷函数）"""
    return get_task_queue().submit(func, *args, **kwargs)


def submit_async(func: Callable, *args, **kwargs) -> Future:
    """异步提交任务（便捷函数）"""
    return get_task_queue().submit_async(func, *args, **kwargs)
