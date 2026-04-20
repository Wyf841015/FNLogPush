#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""影视事件存储服务"""

import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MediaEventService:
    """影视事件存储服务"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.events_file = self.data_dir / "media_events.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._events: List[Dict[str, Any]] = []
        self._load_events()
    
    def _load_events(self):
        """加载事件"""
        try:
            if self.events_file.exists():
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    self._events = json.load(f)
                # 清理超过7天的事件
                self._cleanup_old_events()
        except Exception as e:
            logger.error(f"加载影视事件失败: {e}")
            self._events = []
    
    def _save_events(self):
        """保存事件"""
        try:
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(self._events, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存影视事件失败: {e}")
    
    def _cleanup_old_events(self, days: int = 7):
        """清理过期事件"""
        now = time.time()
        cutoff = now - (days * 86400)
        self._events = [e for e in self._events if e.get('timestamp', 0) > cutoff]
    
    def add_event(self, event: Dict[str, Any]):
        """添加事件"""
        event['timestamp'] = time.time()
        event['datetime'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._events.append(event)
        
        # 只保留最近1000条
        if len(self._events) > 1000:
            self._events = self._events[-1000:]
        
        self._save_events()
    
    def add_events(self, events: List[Dict[str, Any]]):
        """批量添加事件"""
        for event in events:
            self.add_event(event)
    
    def get_recent_events(self, limit: int = 50, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取最近的事件"""
        events = self._events[-limit:] if limit > 0 else self._events
        
        if event_type:
            events = [e for e in events if e.get('type') == event_type]
        
        return list(reversed(events))
    
    def get_events_by_type(self, event_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """按类型获取事件"""
        events = [e for e in self._events if e.get('type') == event_type]
        return list(reversed(events))[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self._events)
        by_type = {}
        
        for event in self._events:
            t = event.get('type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "total": total,
            "by_type": by_type,
            "oldest": self._events[0].get('datetime') if self._events else None,
            "newest": self._events[-1].get('datetime') if self._events else None
        }
    
    def clear_events(self):
        """清空所有事件"""
        self._events = []
        self._save_events()
