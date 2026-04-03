#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志记录模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LogRecord:
    """日志记录数据类"""
    id: int
    logtime: int
    loglevel: int
    category: Optional[int]
    eventId: Optional[str]
    serviceId: Optional[str]
    uname: Optional[str]
    parameter: Optional[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogRecord':
        """从字典创建日志记录"""
        return cls(
            id=data.get('id', 0),
            logtime=data.get('logtime', 0),
            loglevel=data.get('loglevel', 0),
            category=data.get('category'),
            eventId=data.get('eventId'),
            serviceId=data.get('serviceId'),
            uname=data.get('uname'),
            parameter=data.get('parameter')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'logtime': self.logtime,
            'loglevel': self.loglevel,
            'category': self.category,
            'eventId': self.eventId,
            'serviceId': self.serviceId,
            'uname': self.uname,
            'parameter': self.parameter
        }
