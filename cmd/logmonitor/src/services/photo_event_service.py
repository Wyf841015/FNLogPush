"""
相册事件存储服务
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


class PhotoEventService:
    """相册事件存储服务"""

    def __init__(self, data_dir: str = './data'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.data_dir / 'photo_events.json'
        self._events: List[Dict] = []
        self._load_events()

    def _load_events(self):
        """加载事件"""
        if self.events_file.exists():
            try:
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    self._events = json.load(f)
            except Exception as e:
                logger.warning(f"加载相册事件失败: {e}")
                self._events = []

    def _save_events(self):
        """保存事件"""
        try:
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(self._events, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存相册事件失败: {e}")

    def add_event(self, event: Dict):
        """添加事件"""
        event['datetime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._events.insert(0, event)
        # 保留最近1000条
        self._events = self._events[:1000]
        self._save_events()

    def add_events(self, events: List[Dict]):
        """批量添加事件"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for event in events:
            event['datetime'] = now
        self._events = events + self._events
        self._events = self._events[:1000]
        self._save_events()

    def get_events(self, limit: int = 50, event_type: Optional[str] = None) -> List[Dict]:
        """获取事件列表"""
        events = self._events
        if event_type:
            events = [e for e in events if e.get('type') == event_type]
        return events[:limit]

    def clear_events(self):
        """清空事件"""
        self._events = []
        self._save_events()
