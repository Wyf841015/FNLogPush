#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件配置辅助模块
提供从 events.json 读取事件配置的功能
"""
import json
import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def _get_events_file_path() -> Path:
    """获取事件配置文件路径（优先使用 APP_HOME/config/events.json）"""
    app_home = os.environ.get('APP_HOME')
    
    if app_home:
        path = Path(app_home) / 'config' / 'events.json'
        abs_path = path.resolve()
        logger.info(f"[事件] 获取事件配置文件路径: {abs_path}, exists={path.exists()}")
        if path.exists() or True:  # 允许返回不存在的路径
            return path
    
    # fallback 到源码目录
    src_path = _find_events_json()
    if src_path:
        logger.info(f"[事件] fallback 到源码目录: {src_path.resolve()}")
    else:
        logger.warning(f"[事件] 未找到事件配置文件")
    return src_path


def _find_events_json() -> Path:
    """查找 events.json 文件的多个可能位置"""
    app_home = os.environ.get('APP_HOME')
    
    possible_paths = []
    
    # 1. APP_HOME/config/events.json（优先）
    if app_home:
        possible_paths.append(Path(app_home) / 'config' / 'events.json')
    
    # 2. 源码目录下的 events.json
    src_dir = Path(__file__).parent.parent / 'src'
    possible_paths.append(src_dir / 'events.json')
    possible_paths.append(src_dir / 'config' / 'events.json')
    
    for path in possible_paths:
        abs_path = path.resolve()
        if path.exists():
            logger.info(f"[事件] 读取事件配置文件: {abs_path}")
            return path
        else:
            logger.debug(f"[事件] 检查路径不存在: {abs_path}")
    
    logger.warning(f"[事件] 事件配置文件不存在，已检查以下路径:")
    for path in possible_paths:
        logger.warning(f"[事件]   - {path.resolve()}")
    return None


def _load_events_config() -> dict:
    """加载事件配置"""
    events_file = _get_events_file_path()
    abs_events_path = events_file.resolve() if events_file else None
    logger.info(f"[事件] 读取事件配置文件: {abs_events_path}")
    
    if events_file and events_file.exists():
        try:
            with open(events_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"[事件] 成功加载 {len(config.get('categories', []))} 个分类")
            return config
        except Exception as e:
            logger.error(f"[事件] 加载事件配置失败: {e}")
    
    logger.warning(f"[事件] 使用默认事件配置（配置文件不存在或加载失败）")
    return {"version": "1.0.0", "categories": []}


def get_all_configured_event_ids() -> List[str]:
    """
    获取 events.json 中所有已配置的事件ID（无论是否选中监控）
    这是判断"新事件"的标准：只有不在此列表中的事件才被认为是新事件
    """
    config = _load_events_config()
    all_ids = []
    for category in config.get('categories', []):
        for event in category.get('events', []):
            if event.get('id'):
                all_ids.append(event['id'])
    logger.info(f"[新事件] 事件配置文件中共有 {len(all_ids)} 个事件定义")
    return all_ids
