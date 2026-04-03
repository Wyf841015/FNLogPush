#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推送历史模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class PushHistory:
    """推送历史数据类"""
    timestamp: str
    content: str
    preview: str
    success: bool
    count: int
    last_id: int
    levels: Optional[Dict[str, int]] = None
    index: Optional[int] = None
    source: str = 'log'  # 来源：log=日志监控, backup=备份监控
    channel_results: Optional[Dict[str, bool]] = None  # 渠道推送结果：{"wecom": True, "dingtalk": False}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PushHistory':
        """从字典创建推送历史"""
        return cls(
            timestamp=data.get('timestamp', ''),
            content=data.get('content', ''),
            preview=data.get('preview', ''),
            success=data.get('success', False),
            count=data.get('count', 0),
            last_id=data.get('last_id', 0),
            levels=data.get('levels'),
            index=data.get('index'),
            source=data.get('source', 'log'),
            channel_results=data.get('channel_results')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'timestamp': self.timestamp,
            'content': self.content,
            'preview': self.preview,
            'success': self.success,
            'count': self.count,
            'last_id': self.last_id,
            'source': self.source,
            'channel_results': self.channel_results
        }
        if self.levels is not None:
            result['levels'] = self.levels
        if self.index is not None:
            result['index'] = self.index
        return result
