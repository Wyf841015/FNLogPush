#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份操作记录模型
用于监控 basic_backup.db3 中的 operations 表
"""
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass


# 操作状态映射
OPERATION_STATUS_MAP = {
    0: "未知",
    1: "开始",
    2: "取消",
    3: "成功",
    4: "失败",
    5: "未知"
}

# 操作方向映射
DIRECTION_MAP = {
    0: "上传(本地→云端)",
    1: "下载(云端→本地)",
    2: "上传(本地→云端)"
}


@dataclass
class BackupOperation:
    """备份操作记录数据类"""
    id: int
    uid: int
    task_id: int
    start_time: int
    finished_time: int
    files_count: int
    total_size: int
    ignoring_files: int
    error_code: int
    error_message: str
    status: int
    extend: int
    comment: str
    logger_items: int
    completed_count: int
    completed_size: int
    actual_count: int
    actual_size: int
    actual_time: int
    decrypt_files: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupOperation':
        """从字典创建备份操作记录"""
        return cls(
            id=data.get('id', 0),
            uid=data.get('uid', 0),
            task_id=data.get('task_id', 0),
            start_time=data.get('start_time', 0),
            finished_time=data.get('finished_time', 0),
            files_count=data.get('files_count', 0),
            total_size=data.get('total_size', 0),
            ignoring_files=data.get('ignoring_files', 0),
            error_code=data.get('error_code', 0),
            error_message=data.get('error_message', ''),
            status=data.get('status', 0),
            extend=data.get('extend', 0),
            comment=data.get('comment', ''),
            logger_items=data.get('logger_items', 0),
            completed_count=data.get('completed_count', 0),
            completed_size=data.get('completed_size', 0),
            actual_count=data.get('actual_count', 0),
            actual_size=data.get('actual_size', 0),
            actual_time=data.get('actual_time', 0),
            decrypt_files=data.get('decrypt_files', 0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'uid': self.uid,
            'task_id': self.task_id,
            'start_time': self.start_time,
            'finished_time': self.finished_time,
            'files_count': self.files_count,
            'total_size': self.total_size,
            'ignoring_files': self.ignoring_files,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'status': self.status,
            'extend': self.extend,
            'comment': self.comment,
            'logger_items': self.logger_items,
            'completed_count': self.completed_count,
            'completed_size': self.completed_size,
            'actual_count': self.actual_count,
            'actual_size': self.actual_size,
            'actual_time': self.actual_time,
            'decrypt_files': self.decrypt_files
        }
    
    def get_status_name(self) -> str:
        """获取状态名称"""
        return OPERATION_STATUS_MAP.get(self.status, "未知")
    
    def get_direction_name(self, task_direction: int) -> str:
        """获取操作方向名称"""
        return DIRECTION_MAP.get(task_direction, "未知")
    
    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        elif size_bytes < 1024 * 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024 * 1024):.2f} TB"
    
    def format_duration(self) -> str:
        """格式化墙钟持续时间（finished_time - start_time，单位秒）"""
        if self.start_time == 0 or self.finished_time == 0:
            return "-"
        duration = self.finished_time - self.start_time
        if duration < 60:
            return f"{duration}秒"
        elif duration < 3600:
            minutes = duration // 60
            seconds = duration % 60
            return f"{minutes}分{seconds}秒"
        else:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            return f"{hours}小时{minutes}分"

    def format_actual_time(self) -> str:
        """格式化实际 I/O 传输耗时（actual_time 单位为毫秒）"""
        ms = self.actual_time
        if not ms or ms <= 0:
            return "-"
        s = ms / 1000
        h, rem = divmod(int(s), 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f"{h}小时{m:02d}分{sec:02d}秒"
        elif m:
            return f"{m}分{sec:02d}秒"
        else:
            return f"{s:.1f}秒"
    
    def get_start_time_str(self) -> str:
        """获取开始时间字符串"""
        if self.start_time == 0:
            return "-"
        return datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')
    
    def get_finished_time_str(self) -> str:
        """获取完成时间字符串"""
        if self.finished_time == 0:
            return "-"
        return datetime.fromtimestamp(self.finished_time).strftime('%Y-%m-%d %H:%M:%S')
