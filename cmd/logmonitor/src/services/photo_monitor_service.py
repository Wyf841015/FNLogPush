"""
相册监控服务
"""

import logging
import threading
from pathlib import Path
from typing import List, Optional, Callable

from .photo_db_poller import PhotoDBPoller, PHOTO_POLL_EVENTS

logger = logging.getLogger(__name__)


class PhotoMonitorService:
    """相册监控服务"""

    def __init__(
        self,
        db_path: str = '/usr/local/apps/@appdata/trim.photos/db/photo.db',
        cursor_dir: str = None,
        poll_interval: int = 10,
        monitor_events: Optional[List[str]] = None,
        on_event: Optional[Callable] = None
    ):
        self.db_path = db_path
        self.cursor_dir = cursor_dir or './data/cursor'
        self.poll_interval = poll_interval
        self.monitor_events = monitor_events or list(PHOTO_POLL_EVENTS)
        self.on_event = on_event
        
        self.poller = PhotoDBPoller(
            db_path=self.db_path,
            cursor_dir=self.cursor_dir,
            poll_interval=self.poll_interval,
            monitor_events=self.monitor_events
        )
        
        # 注册事件处理器
        self.poller.add_handler('PHOTO_SHARE_CREATED', self._handle_share_created)
        self.poller.add_handler('PHOTO_SHARE_EXPIRED', self._handle_share_expired)
        self.poller.add_handler('PHOTO_DEVICE_REGISTERED', self._handle_device_registered)
        self.poller.add_handler('FACE_RECOGNITION_UPDATED', self._handle_face_updated)
        
        self._enabled = False

    def _handle_share_created(self, entry):
        """处理分享创建"""
        return {
            'type': 'PHOTO_SHARE_CREATED',
            'id': entry.get('id'),
            'title': entry.get('title', ''),
            'valid_to': entry.get('valid_to'),
            'link': entry.get('link', '')
        }

    def _handle_share_expired(self, entry):
        """处理分享过期"""
        return {
            'type': 'PHOTO_SHARE_EXPIRED',
            'id': entry.get('id'),
            'title': entry.get('title', ''),
            'valid_to': entry.get('valid_to')
        }

    def _handle_device_registered(self, entry):
        """处理设备注册"""
        return {
            'type': 'PHOTO_DEVICE_REGISTERED',
            'id': entry.get('id'),
            'device_name': entry.get('device_name', ''),
            'device_type': entry.get('device_type', '')
        }

    def _handle_face_updated(self, entry):
        """处理人脸识别更新"""
        return {
            'type': 'FACE_RECOGNITION_UPDATED',
            'id': entry.get('id'),
            'task_id': entry.get('task_id')
        }

    def start(self):
        """启动监控"""
        if self._enabled:
            return
        
        # 更新配置
        self.poller.update_config(
            monitor_events=self.monitor_events,
            poll_interval=self.poll_interval,
            db_path=self.db_path
        )
        
        self.poller.start()
        self._enabled = True
        logger.info(f"✓ 相册监控服务已启动 (db={self.db_path})")

    def stop(self):
        """停止监控"""
        if not self._enabled:
            return
        
        self.poller.stop()
        self._enabled = False
        logger.info("○ 相册监控服务已停止")

    def is_running(self) -> bool:
        """检查是否运行中"""
        return self._enabled

    def update_config(self, **kwargs):
        """更新配置"""
        if 'db_path' in kwargs:
            self.db_path = kwargs['db_path']
        if 'poll_interval' in kwargs:
            self.poll_interval = kwargs['poll_interval']
        if 'monitor_events' in kwargs:
            self.monitor_events = kwargs['monitor_events']
        
        self.poller.update_config(
            monitor_events=self.monitor_events,
            poll_interval=self.poll_interval,
            db_path=self.db_path
        )

    def get_status(self) -> dict:
        """获取状态"""
        return {
            'enabled': self._enabled,
            'db_path': self.db_path,
            'db_available': Path(self.db_path).exists() if self.db_path else False,
            'poll_interval': self.poll_interval,
            'monitor_events': list(self.monitor_events) if self.monitor_events else []
        }
