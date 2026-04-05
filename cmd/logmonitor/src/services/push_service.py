#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推送服务模块
负责将消息推送到各种渠道

变更说明:
  - 推送失败任务持久化到 SQLite（push_failed.db），重启后自动补发
  - 重试逻辑与主队列解耦，使用最小堆管理重试时间
"""
import logging
import requests
import urllib.parse
import threading
import queue
import heapq
import time
import sqlite3
import os
import json
from typing import Dict, Any, Optional, List, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PushChannel(ABC):
    """推送渠道抽象基类"""
    
    @abstractmethod
    def push(self, content: str) -> bool:
        """
        推送消息
        
        Args:
            content: 消息内容
            
        Returns:
            是否推送成功
        """
        pass


class WebhookPushChannel(PushChannel):
    """Webhook推送渠道"""
    
    def __init__(self, webhook_url: str):
        """
        初始化Webhook推送渠道
        
        Args:
            webhook_url: Webhook URL，支持 {content} 占位符或 JSON body 模式
        """
        self.webhook_url = webhook_url
        self._use_post = '{content}' not in webhook_url  # 无占位符时使用 POST
    
    def push(self, content: str) -> bool:
        """推送消息到Webhook"""
        try:
            if not self.webhook_url:
                logger.warning("Webhook URL未配置")
                return False
            
            if self._use_post:
                # POST 模式：将内容作为 JSON body 发送
                payload = {"content": content}
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                logger.debug(f"Webhook POST推送: {self.webhook_url[:50]}...")
            else:
                # GET 模式：使用 URL 占位符（向后兼容）
                encoded_content = urllib.parse.quote(content)
                url = self.webhook_url.replace('{content}', encoded_content)
                response = requests.get(url, timeout=10)
                logger.debug(f"Webhook GET推送: {url[:50]}...")
            
            if response.status_code in (200, 201):
                logger.info(f"Webhook推送成功，状态码: {response.status_code}")
                return True
            else:
                logger.error(f"Webhook推送失败，状态码: {response.status_code}, 响应: {response.text[:200]}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("Webhook推送超时")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Webhook连接失败")
            return False
        except Exception as e:
            logger.error(f"Webhook推送时出错: {e}")
            return False


class WecomPushChannel(PushChannel):
    """企业微信推送渠道"""
    
    def __init__(self, webhook_url: str, enabled: bool = True):
        """
        初始化企业微信推送渠道
        
        Args:
            webhook_url: 企业微信Webhook URL
            enabled: 是否启用
        """
        self.webhook_url = webhook_url
        self.enabled = enabled
    
    def push(self, content: str) -> bool:
        """推送消息到企业微信"""
        try:
            if not self.enabled:
                logger.warning("企业微信推送未启用")
                return False
            
            if not self.webhook_url:
                logger.warning("企业微信Webhook URL未配置")
                return False
            
            # 构建企业微信消息格式
            message = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # 解析响应
            result = response.json()
            if result.get('errcode') == 0:
                logger.info("企业微信推送成功")
                return True
            else:
                logger.error(f"企业微信推送失败，错误码: {result.get('errcode')}, 错误信息: {result.get('errmsg')}")
                return False
                
        except Exception as e:
            logger.error(f"企业微信推送时出错: {e}")
            return False


class DingtalkPushChannel(PushChannel):
    """钉钉推送渠道"""
    
    def __init__(self, webhook_url: str, secret: str = "", enabled: bool = True):
        """
        初始化钉钉推送渠道
        
        Args:
            webhook_url: 钉钉Webhook URL
            secret: 钉钉机器人安全密钥
            enabled: 是否启用
        """
        self.webhook_url = webhook_url
        self.secret = secret
        self.enabled = enabled
    
    def _generate_sign(self, timestamp: str) -> str:
        """生成钉钉签名"""
        import hmac
        import hashlib
        import base64
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode('utf-8')
    
    def push(self, content: str) -> bool:
        """推送消息到钉钉"""
        try:
            if not self.enabled:
                logger.warning("钉钉推送未启用")
                return False
            
            if not self.webhook_url:
                logger.warning("钉钉Webhook URL未配置")
                return False
            
            # 生成签名
            timestamp = str(int(time.time() * 1000))
            url = self.webhook_url
            if self.secret:
                sign = self._generate_sign(timestamp)
                url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
            
            # 构建钉钉消息格式
            message = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            # 发送请求
            response = requests.post(
                url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # 解析响应
            result = response.json()
            if result.get('errcode') == 0:
                logger.info("钉钉推送成功")
                return True
            else:
                logger.error(f"钉钉推送失败，错误码: {result.get('errcode')}, 错误信息: {result.get('errmsg')}")
                return False
                
        except Exception as e:
            logger.error(f"钉钉推送时出错: {e}")
            return False


class FeishuPushChannel(PushChannel):
    """飞书推送渠道"""
    
    def __init__(self, webhook_url: str, enabled: bool = True):
        """
        初始化飞书推送渠道
        
        Args:
            webhook_url: 飞书Webhook URL
            enabled: 是否启用
        """
        self.webhook_url = webhook_url
        self.enabled = enabled
    
    def push(self, content: str) -> bool:
        """推送消息到飞书"""
        try:
            if not self.enabled:
                logger.warning("飞书推送未启用")
                return False
            
            if not self.webhook_url:
                logger.warning("飞书Webhook URL未配置")
                return False
            
            # 构建飞书消息格式
            message = {
                "msg_type": "text",
                "content": {
                    "text": content
                }
            }
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # 解析响应
            result = response.json()
            if result.get('code') == 0:
                logger.info("飞书推送成功")
                return True
            else:
                logger.error(f"飞书推送失败，错误码: {result.get('code')}, 错误信息: {result.get('msg')}")
                return False
                
        except Exception as e:
            logger.error(f"飞书推送时出错: {e}")
            return False


class BarkPushChannel(PushChannel):
    """Bark推送渠道（iOS）"""
    
    def __init__(self, device_key: str, server: str = "https://api.day.app", enabled: bool = True):
        """
        初始化Bark推送渠道
        
        Args:
            device_key: Bark设备密钥
            server: Bark服务器地址
            enabled: 是否启用
        """
        self.device_key = device_key
        self.server = server.rstrip('/')
        self.enabled = enabled
    
    def push(self, content: str) -> bool:
        """推送消息到Bark"""
        try:
            if not self.enabled:
                logger.warning("Bark推送未启用")
                return False
            
            if not self.device_key:
                logger.warning("Bark设备密钥未配置")
                return False
            
            # 提取标题和内容
            lines = content.split('\n', 1)
            title = lines[0][:20] if lines else "通知"
            body = lines[1] if len(lines) > 1 else content
            
            # 构建Bark请求
            url = f"{self.server}/push"
            params = {
                "device_key": self.device_key,
                "title": title,
                "body": body,
                "sound": "default"
            }
            
            # 发送请求
            response = requests.post(url, json=params, timeout=10)
            
            # 解析响应
            result = response.json()
            if result.get('code') == 200:
                logger.info("Bark推送成功")
                return True
            else:
                logger.error(f"Bark推送失败，错误: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Bark推送时出错: {e}")
            return False


class PushPlusPushChannel(PushChannel):
    """PushPlus推送渠道"""
    
    def __init__(self, token: str, topic: str = "", enabled: bool = True):
        """
        初始化PushPlus推送渠道
        
        Args:
            token: PushPlus Token
            topic: PushPlus群组
            enabled: 是否启用
        """
        self.token = token
        self.topic = topic
        self.enabled = enabled
    
    def push(self, content: str) -> bool:
        """推送消息到PushPlus"""
        try:
            if not self.enabled:
                logger.warning("PushPlus推送未启用")
                return False
            
            if not self.token:
                logger.warning("PushPlus Token未配置")
                return False
            
            # 构建PushPlus消息数据
            data = {
                "token": self.token,
                "title": "FNLogPush通知",
                "content": content.replace('\n', '<br>'),
                "template": "html"
            }
            
            # 如果有群组则添加
            if self.topic:
                data["topic"] = self.topic
            
            # 发送请求
            response = requests.post(
                "https://www.pushplus.plus/send",
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # 解析响应
            result = response.json()
            if result.get('code') == 200:
                logger.info("PushPlus推送成功")
                return True
            else:
                logger.error(f"PushPlus推送失败，错误: {result.get('msg')}")
                return False
                
        except Exception as e:
            logger.error(f"PushPlus推送时出错: {e}")
            return False


class MeoWPushChannel(PushChannel):
    """MeoW推送渠道"""
    
    def __init__(self, nickname: str, enabled: bool = True, title: str = "", msgtype: str = ""):
        """
        初始化MeoW推送渠道
        
        Args:
            nickname: MeoW用户昵称
            enabled: 是否启用
            title: 标题模板
            msgtype: 消息类型 (text/html/markdown)
        """
        self.nickname = nickname
        self.enabled = enabled
        self.title = title
        self.msgtype = msgtype
        self.api_url = "https://api.chuckfang.com"
    
    def push(self, content: str) -> bool:
        """推送消息到MeoW"""
        try:
            if not self.enabled:
                logger.warning("MeoW推送未启用")
                return False
            
            if not self.nickname:
                logger.warning("MeoW昵称未配置")
                return False
            
            # 提取标题和内容
            lines = content.split('\n', 1)
            
            # 使用配置的标题或默认值
            if self.title:
                # 自定义标题：整个消息作为内容
                title = self.title[:50]
                msg = content
            else:
                # 无自定义标题：第一行作为标题，其余作为内容
                title = lines[0][:50] if lines else "日志哨兵"
                msg = lines[1] if len(lines) > 1 else ""
            
            # 构建请求URL和参数
            url = f"{self.api_url}/{self.nickname}"
            params = []
            if self.msgtype:
                params.append(f"msgType={self.msgtype}")
            
            if params:
                url = f"{url}?{'&'.join(params)}"
            
            # POST JSON 方式发送
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            payload = {
                'title': title,
                'msg': msg
            }
            
            logger.info(f"MeoW推送请求: {url}, payload={payload}")
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            result = response.json()
            logger.info(f"MeoW推送响应: {result}")
            
            if result.get('status') == 200:
                logger.info("MeoW推送成功")
                return True
            else:
                logger.error(f"MeoW推送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"MeoW推送时出错: {e}")
            return False


class PushTask:
    """推送任务类"""
    
    def __init__(self, content: str, enabled_channels: Dict[str, bool], retry_count: int = 0, failed_channels: Optional[Dict[str, bool]] = None):
        """
        初始化推送任务
        
        Args:
            content: 消息内容
            enabled_channels: 启用的渠道配置
            retry_count: 当前重试次数
            failed_channels: 失败的渠道配置，用于重试时只推送失败渠道
        """
        self.content = content
        self.enabled_channels = enabled_channels
        self.failed_channels = failed_channels  # 新增：记录失败的渠道
        self.retry_count = retry_count
        self.created_at = time.time()
        self.last_attempt: Optional[float] = None
        self.next_retry_at: float = 0

    def __lt__(self, other):
        """支持 heapq 比较（按创建时间排序作为 tiebreaker）"""
        return self.created_at < other.created_at
    
    def get_retry_channels(self) -> Dict[str, bool]:
        """获取需要重试的渠道，只返回失败的渠道"""
        return self.failed_channels if self.failed_channels else self.enabled_channels


class FailedPushStore:
    """推送失败持久化存储（SQLite），用于重启后自动补发"""

    DB_FILE = 'push_failed.db'

    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_FILE
        self._lock = threading.Lock()
        self._init_db()
        logger.info(f"推送失败持久化存储已初始化: {self.db_path}")

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS failed_push (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    enabled_channels TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    next_retry_at REAL NOT NULL
                )
            """)
            conn.commit()

    def save(self, task: 'PushTask'):
        """持久化一条失败任务"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT INTO failed_push (content, enabled_channels, retry_count, created_at, next_retry_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            task.content,
                            json.dumps(task.enabled_channels),
                            task.retry_count,
                            task.created_at,
                            task.next_retry_at,
                        )
                    )
                    conn.commit()
            except Exception as e:
                logger.error(f"持久化推送失败任务时出错: {e}")

    def load_pending(self) -> List['PushTask']:
        """加载所有待补发任务（用于重启恢复）"""
        tasks = []
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    rows = conn.execute(
                        "SELECT id, content, enabled_channels, retry_count, created_at, next_retry_at "
                        "FROM failed_push ORDER BY next_retry_at ASC"
                    ).fetchall()
                for row in rows:
                    task = PushTask(
                        content=row[1],
                        enabled_channels=json.loads(row[2]),
                        retry_count=row[3],
                    )
                    task.created_at = row[4]
                    task.next_retry_at = row[5]
                    task._db_id = row[0]
                    tasks.append(task)
            except Exception as e:
                logger.error(f"加载待补发推送任务时出错: {e}")
        return tasks

    def delete(self, task: 'PushTask'):
        """删除已完成（成功或超过最大重试）的持久化记录"""
        db_id = getattr(task, '_db_id', None)
        if db_id is None:
            return
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM failed_push WHERE id = ?", (db_id,))
                    conn.commit()
            except Exception as e:
                logger.error(f"删除持久化推送任务时出错: {e}")


class DeadLetterStore:
    """死信区：超过最大重试次数的推送任务持久化到 dead_letter 表，供 UI 查看和手动重发"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        logger.info(f"死信区已初始化: {self.db_path}")

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dead_letter (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    enabled_channels TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    failed_at REAL NOT NULL,
                    error_reason TEXT DEFAULT ''
                )
            """)
            conn.commit()

    def save(self, task: 'PushTask', reason: str = ''):
        """将任务写入死信区"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT INTO dead_letter "
                        "(content, enabled_channels, retry_count, created_at, failed_at, error_reason) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            task.content,
                            json.dumps(task.enabled_channels),
                            task.retry_count,
                            task.created_at,
                            time.time(),
                            reason,
                        )
                    )
                    conn.commit()
                logger.warning(f"推送任务已进入死信区: retry_count={task.retry_count}, reason={reason}")
            except Exception as e:
                logger.error(f"写入死信区时出错: {e}")

    def list_all(self) -> List[Dict]:
        """查询所有死信记录"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute(
                        "SELECT * FROM dead_letter ORDER BY failed_at DESC LIMIT 200"
                    ).fetchall()
                return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"查询死信区时出错: {e}")
                return []

    def delete(self, dlq_id: int):
        """删除一条死信记录"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM dead_letter WHERE id = ?", (dlq_id,))
                    conn.commit()
            except Exception as e:
                logger.error(f"删除死信记录时出错: {e}")

    def get_by_id(self, dlq_id: int) -> Optional[Dict]:
        """按 id 获取一条死信记录"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    row = conn.execute(
                        "SELECT * FROM dead_letter WHERE id = ?", (dlq_id,)
                    ).fetchone()
                return dict(row) if row else None
            except Exception as e:
                logger.error(f"查询死信记录时出错: {e}")
                return None

    def count(self) -> int:
        """返回死信区记录数"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    return conn.execute("SELECT COUNT(*) FROM dead_letter").fetchone()[0]
            except Exception:
                return 0


class PushService:
    """推送服务管理类"""

    # 队列和重试堆大小限制
    MAX_QUEUE_SIZE = 1000
    MAX_RETRY_HEAP_SIZE = 500
    QUEUE_WARNING_THRESHOLD = 800  # 80%水位线

    # 指数退避参数
    RETRY_BASE_DELAY = 5      # 首次重试延迟（秒）
    RETRY_MAX_DELAY = 300     # 退避上限（秒）

    def __init__(self):
        """初始化推送服务"""
        self.channels: Dict[str, PushChannel] = {}
        self.push_queue: queue.Queue = queue.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._retry_heap: List = []
        self._retry_lock = threading.Lock()
        self.max_retries = 3                      # 最大重试次数（可由配置覆盖）
        self.retry_base_delay = self.RETRY_BASE_DELAY   # 可由配置覆盖
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.RLock()
        self._started = False  # 标记是否已启动

        # 推送失败持久化存储（重启后自动补发）
        self._failed_store = FailedPushStore()
        self._restore_failed_tasks()

        # 死信区（超出最大重试次数）
        self._dead_letter_store = DeadLetterStore(self._failed_store.db_path)

        # 统计信息
        self._stats = {
            "total_pushed": 0,
            "total_failed": 0,
            "total_dropped": 0,
            "total_dead_letter": 0,
            "last_push_time": None
        }
        self._stats_lock = threading.Lock()

    def _calc_retry_delay(self, retry_count: int) -> float:
        """指数退避：delay = base * 2^(retry_count-1)，上限 RETRY_MAX_DELAY"""
        delay = self.retry_base_delay * (2 ** (retry_count - 1))
        return min(delay, self.RETRY_MAX_DELAY)

    def start(self):
        """
        启动推送服务工作线程
        """
        with self.lock:
            if not self.running:
                self.running = True
                self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
                self.worker_thread.start()
                self._started = True
                logger.info("推送服务工作线程已启动")

                # 启动时立即清理一次过期持久化记录，然后每 24 小时定期清理
                self._start_failed_task_cleaner()

    def _restore_failed_tasks(self):
        """从持久化存储恢复上次未成功的推送任务，加入重试堆"""
        pending = self._failed_store.load_pending()
        if not pending:
            return
        now = time.time()
        with self._retry_lock:
            for task in pending:
                # 若延迟已过期则立即重试，否则按原计划时间
                next_at = max(task.next_retry_at, now)
                heapq.heappush(self._retry_heap, (next_at, task))
        logger.info(f"从持久化存储恢复 {len(pending)} 条待补发推送任务")

    def _start_failed_task_cleaner(self):
        """启动过期失败任务定期清理（启动时执行一次，此后每 24 小时执行一次）"""
        # 立即清一次
        self.cleanup_old_failed_tasks(max_age_hours=24)

        def _cleaner_loop():
            while self.running:
                # 等待 24 小时，期间每 60 秒检查一次 running 状态以便快速退出
                for _ in range(24 * 60):
                    if not self.running:
                        return
                    time.sleep(60)
                self.cleanup_old_failed_tasks(max_age_hours=24)

        thread = threading.Thread(target=_cleaner_loop, daemon=True, name="failed-task-cleaner")
        thread.start()
        logger.info("失败任务定期清理线程已启动（间隔 24 小时）")

    def stop(self):
        """
        停止推送服务工作线程
        """
        with self.lock:
            if self.running:
                self.running = False
                if self.worker_thread:
                    self.worker_thread.join(timeout=5)
                self._started = False
                logger.info("推送服务工作线程已停止")
    
    def register_channel(self, name: str, channel: PushChannel):
        """
        注册推送渠道
        
        Args:
            name: 渠道名称
            channel: 渠道实例
        """
        self.channels[name] = channel
        logger.info(f"注册推送渠道: {name}")
    
    def unregister_channel(self, name: str):
        """
        注销推送渠道
        
        Args:
            name: 渠道名称
        """
        if name in self.channels:
            del self.channels[name]
            logger.info(f"注销推送渠道: {name}")
    
    def push_message(self, content: str, enabled_channels: Optional[Dict[str, bool]] = None) -> bool:
        """
        推送消息到启用的渠道

        Args:
            content: 消息内容
            enabled_channels: 启用的渠道配置 {"webhook": True, "wecom": False}

        Returns:
            是否成功加入队列
        """
        logger.info(f"[DEBUG] PushService.push_message: 收到消息，内容长度={len(content)}，渠道={enabled_channels}")
        
        if enabled_channels is None:
            enabled_channels = {name: True for name in self.channels}
        
        # 检查是否有任何启用的渠道
        has_enabled_channel = False
        for channel_name, is_enabled in enabled_channels.items():
            if is_enabled and channel_name in self.channels:
                has_enabled_channel = True
                break
        
        if not has_enabled_channel:
            logger.warning("没有启用任何推送渠道")
            return False

        # 检查队列水位
        queue_size = self.push_queue.qsize()
        if queue_size >= self.QUEUE_WARNING_THRESHOLD:
            logger.warning(f"推送队列接近满载: {queue_size}/{self.MAX_QUEUE_SIZE}")

        # 创建推送任务
        task = PushTask(content, enabled_channels)

        try:
            # 同步执行推送，获取实际结果
            channel_results = self._execute_push(task)
            
            # 判断是否有失败的渠道
            has_failures = channel_results and not all(channel_results.values())
            
            # 同步执行后不再加入队列，避免重复推送
            # 仅当有渠道失败且未超过最大重试次数时，加入队列等待重试
            if has_failures and task.retry_count < self.max_retries:
                failed_channels = {ch: result for ch, result in channel_results.items() if not result}
                retry_task = PushTask(
                    content=task.content,
                    enabled_channels=task.enabled_channels,
                    retry_count=1,
                    failed_channels=failed_channels
                )
                try:
                    self.push_queue.put(retry_task, block=False)
                    self.start()
                    logger.info(f"失败渠道将加入重试队列: {list(failed_channels.keys())}")
                except queue.Full:
                    logger.warning("推送队列已满，失败任务无法加入重试")
            
            logger.info(f"消息已推送，渠道结果: {channel_results}")
            return channel_results
        except Exception as e:
            logger.error(f"推送执行异常: {e}")
            return {}

    def _process_queue(self):
        """
        处理推送队列中的任务。

        策略：
        - 新任务放在 push_queue（普通队列），优先处理。
        - 推送失败需重试的任务放入 _retry_heap（最小堆，按 next_retry_at 排序）。
        - 每次循环先检查堆里是否有到期的重试任务，有则移入 push_queue；
          再从 push_queue 取一条任务执行。
        - 新任务永远不会被重试任务"插队"，延迟降为 check_interval 级别。
        - 重试堆大小限制为 MAX_RETRY_HEAP_SIZE，超过时丢弃最旧的任务。
        """
        while self.running:
            try:
                now = time.time()

                # 1. 把已到期的重试任务移入主队列
                with self._retry_lock:
                    while self._retry_heap and self._retry_heap[0][0] <= now:
                        _, retry_task = heapq.heappop(self._retry_heap)
                        try:
                            self.push_queue.put_nowait(retry_task)
                        except queue.Full:
                            logger.warning("推送队列已满，丢弃到期重试任务")
                            with self._stats_lock:
                                self._stats["total_dropped"] += 1

                # 2. 取一条任务执行（最多等 0.5 秒，以便及时响应重试到期）
                try:
                    task = self.push_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                channel_results = self._execute_push(task)
                
                # 判断是否所有渠道都成功
                all_success = channel_results and all(channel_results.values())
                has_failures = channel_results and not all(channel_results.values())
                
                if has_failures and task.retry_count < self.max_retries:
                    # 部分渠道失败：记录失败的渠道，准备重试
                    failed_channels = {ch: result for ch, result in channel_results.items() if not result}
                    logger.info(f"部分渠道推送失败: {failed_channels}，准备重试")
                    
                    # 创建新的重试任务，只包含失败的渠道
                    retry_task = PushTask(
                        content=task.content,
                        enabled_channels=task.enabled_channels,
                        retry_count=task.retry_count + 1,
                        failed_channels=failed_channels
                    )
                    
                    task.retry_count += 1
                    task.last_attempt = time.time()
                    delay = self._calc_retry_delay(task.retry_count)
                    retry_task.next_retry_at = task.last_attempt + delay
                    
                    logger.info(
                        f"将在 {delay:.0f} 秒后重试失败的渠道（第 {task.retry_count} 次），"
                        f"退避延迟: {delay:.0f}s"
                    )
                    # 持久化失败任务
                    self._failed_store.save(retry_task)
                    with self._retry_lock:
                        if len(self._retry_heap) >= self.MAX_RETRY_HEAP_SIZE:
                            logger.error(f"重试堆已满({self.MAX_RETRY_HEAP_SIZE})，丢弃最旧的任务")
                            heapq.heappop(self._retry_heap)
                            with self._stats_lock:
                                self._stats["total_dropped"] += 1
                        heapq.heappush(self._retry_heap, (retry_task.next_retry_at, retry_task))
                
                elif has_failures:
                    # 超过最大重试次数 → 写入死信区
                    failed_channels = {ch: result for ch, result in channel_results.items() if not result}
                    reason = f"已重试 {task.retry_count} 次，失败渠道: {list(failed_channels.keys())}"
                    self._dead_letter_store.save(task, reason=reason)
                    self._failed_store.delete(task)
                    with self._stats_lock:
                        self._stats["total_failed"] += 1
                        self._stats["total_dead_letter"] += 1
                    logger.error(f"推送任务进入死信区: retry_count={task.retry_count}, {reason}")
                else:
                    # 推送成功，删除持久化记录
                    self._failed_store.delete(task)
                    with self._stats_lock:
                        self._stats["total_pushed"] += 1
                        self._stats["last_push_time"] = time.time()

                self.push_queue.task_done()

            except Exception as e:
                logger.error(f"处理推送队列时出错: {e}", exc_info=True)
                try:
                    self.push_queue.task_done()
                except Exception:
                    pass
    
    def _execute_push(self, task: PushTask) -> bool:
        """
        执行推送任务
        
        Args:
            task: 推送任务
            
        Returns:
            渠道推送结果字典: {"wecom": True, "dingtalk": False}
        """
        channel_results = {}
        
        # 获取本次需要推送的渠道（重试时只推失败的渠道）
        retry_channels = task.get_retry_channels()
        is_retry = task.failed_channels is not None and len(task.failed_channels) > 0
        
        for channel_name, channel in self.channels.items():
            if retry_channels.get(channel_name, False):
                if is_retry:
                    logger.info(f"[重试] 推送渠道: {channel_name}")
                channel_success = channel.push(task.content)
                channel_results[channel_name] = channel_success
        
        # 记录推送结果
        result_str = ', '.join([f"{name}:{'成功' if ok else '失败'}" for name, ok in channel_results.items()])
        logger.info(f"推送结果: {result_str}")
        
        return channel_results
    
    def configure_from_config(self, config: Dict[str, Any]):
        """
        从配置文件配置推送渠道
        
        Args:
            config: 配置字典
        """
        # 配置Webhook渠道
        webhook_url = config.get('webhook_url', '')
        if webhook_url:
            if 'webhook' not in self.channels:
                self.register_channel('webhook', WebhookPushChannel(webhook_url))
            else:
                self.channels['webhook'].webhook_url = webhook_url
        
        # 配置企业微信渠道
        wecom_config = config.get('wecom', {})
        if wecom_config.get('enabled', False) and wecom_config.get('webhook_url'):
            wecom_url = wecom_config['webhook_url']
            if 'wecom' not in self.channels:
                self.register_channel('wecom', WecomPushChannel(wecom_url, True))
            else:
                self.channels['wecom'].webhook_url = wecom_url
                self.channels['wecom'].enabled = True
        
        # 配置钉钉渠道
        dingtalk_config = config.get('dingtalk', {})
        if dingtalk_config.get('enabled', False) and dingtalk_config.get('webhook_url'):
            webhook_url = dingtalk_config['webhook_url']
            secret = dingtalk_config.get('secret', '')
            if 'dingtalk' not in self.channels:
                self.register_channel('dingtalk', DingtalkPushChannel(webhook_url, secret, True))
            else:
                self.channels['dingtalk'].webhook_url = webhook_url
                self.channels['dingtalk'].secret = secret
                self.channels['dingtalk'].enabled = True
        
        # 配置飞书渠道
        feishu_config = config.get('feishu', {})
        if feishu_config.get('enabled', False) and feishu_config.get('webhook_url'):
            webhook_url = feishu_config['webhook_url']
            if 'feishu' not in self.channels:
                self.register_channel('feishu', FeishuPushChannel(webhook_url, True))
            else:
                self.channels['feishu'].webhook_url = webhook_url
                self.channels['feishu'].enabled = True
        
        # 配置Bark渠道
        bark_config = config.get('bark', {})
        if bark_config.get('enabled', False) and bark_config.get('device_key'):
            device_key = bark_config['device_key']
            server = bark_config.get('server', 'https://api.day.app')
            if 'bark' not in self.channels:
                self.register_channel('bark', BarkPushChannel(device_key, server, True))
            else:
                self.channels['bark'].device_key = device_key
                self.channels['bark'].server = server
                self.channels['bark'].enabled = True
        
        # 配置PushPlus渠道
        pushplus_config = config.get('pushplus', {})
        if pushplus_config.get('enabled', False) and pushplus_config.get('token'):
            token = pushplus_config['token']
            topic = pushplus_config.get('topic', '')
            if 'pushplus' not in self.channels:
                self.register_channel('pushplus', PushPlusPushChannel(token, topic, True))
            else:
                self.channels['pushplus'].token = token
                self.channels['pushplus'].topic = topic
                self.channels['pushplus'].enabled = True
        
        # 配置MeoW渠道
        meow_config = config.get('meow', {})
        if meow_config.get('enabled', False) and meow_config.get('nickname'):
            nickname = meow_config['nickname']
            title = meow_config.get('title', '')
            msgtype = meow_config.get('msgtype', '')
            if 'meow' not in self.channels:
                self.register_channel('meow', MeoWPushChannel(nickname, True, title, msgtype))
            else:
                self.channels['meow'].nickname = nickname
                self.channels['meow'].title = title
                self.channels['meow'].msgtype = msgtype
                self.channels['meow'].enabled = True
        
        # 更新重试参数（支持配置覆盖）
        if 'push_retry' in config:
            retry_cfg = config['push_retry']
            self.max_retries = int(retry_cfg.get('max_retries', self.max_retries))
            self.retry_base_delay = float(retry_cfg.get('base_delay', self.retry_base_delay))
            logger.info(f"推送重试参数: max_retries={self.max_retries}, base_delay={self.retry_base_delay}s")

        # 更新推送渠道配置
        push_channels_config = config.get('push_channels', {})
        logger.info(f"推送渠道配置: {push_channels_config}")
        
        # 确保工作线程已启动
        self.start()
    
    def get_queue_size(self) -> int:
        """
        获取推送队列大小

        Returns:
            队列中的任务数量
        """
        return self.push_queue.qsize()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取推送服务统计信息

        Returns:
            统计信息字典
        """
        from utils.time_utils import TimeUtils
        with self._stats_lock:
            with self._retry_lock:
                last_push_ts = self._stats["last_push_time"]
                last_push_str = (
                    TimeUtils.timestamp_to_shanghai(int(last_push_ts))
                    if last_push_ts else None
                )
                stats = {
                    "queue_size": self.push_queue.qsize(),
                    "queue_max_size": self.MAX_QUEUE_SIZE,
                    "queue_usage_percent": round(
                        (self.push_queue.qsize() / self.MAX_QUEUE_SIZE) * 100, 1
                    ),
                    "retry_heap_size": len(self._retry_heap),
                    "retry_heap_max_size": self.MAX_RETRY_HEAP_SIZE,
                    "retry_base_delay": self.retry_base_delay,
                    "max_retries": self.max_retries,
                    "total_pushed": self._stats["total_pushed"],
                    "total_failed": self._stats["total_failed"],
                    "total_dropped": self._stats["total_dropped"],
                    "total_dead_letter": self._stats["total_dead_letter"],
                    "dead_letter_count": self._dead_letter_store.count(),
                    "last_push_time": last_push_str,
                    "running": self.running
                }
        return stats

    def get_dead_letters(self) -> List[Dict]:
        """返回死信区所有记录（供 API 查询）"""
        return self._dead_letter_store.list_all()

    def requeue_dead_letter(self, dlq_id: int) -> bool:
        """
        将死信区的一条记录重新投入推送队列

        Args:
            dlq_id: 死信记录 id

        Returns:
            是否成功重新入队
        """
        record = self._dead_letter_store.get_by_id(dlq_id)
        if not record:
            logger.warning(f"死信记录不存在: id={dlq_id}")
            return False
        try:
            enabled_channels = json.loads(record["enabled_channels"])
        except Exception:
            enabled_channels = {}
        task = PushTask(
            content=record["content"],
            enabled_channels=enabled_channels,
            retry_count=0,   # 重发时重置重试次数
        )
        task.created_at = record["created_at"]
        try:
            self.push_queue.put(task, block=False)
            self._dead_letter_store.delete(dlq_id)
            logger.info(f"死信记录已重新入队: id={dlq_id}")
            return True
        except queue.Full:
            logger.error("推送队列已满，死信重发失败")
            return False

    def cleanup_old_failed_tasks(self, max_age_hours: int = 24):
        """
        清理过期的持久化失败任务

        Args:
            max_age_hours: 任务最大保留时间（小时）
        """
        try:
            max_age_seconds = max_age_hours * 3600
            current_time = time.time()

            # 直接操作数据库清理过期任务
            import sqlite3
            with sqlite3.connect(self._failed_store.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM failed_push WHERE created_at < ?",
                    (current_time - max_age_seconds,)
                )
                deleted_count = cursor.rowcount
                conn.commit()

                if deleted_count > 0:
                    logger.info(f"清理了 {deleted_count} 个过期持久化任务")

        except Exception as e:
            logger.error(f"清理过期持久化任务时出错: {e}")
