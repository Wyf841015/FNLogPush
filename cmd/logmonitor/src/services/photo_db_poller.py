#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Photo monitor poller - standalone version without monitor_core dependency."""
import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

PHOTO_SHARE_CREATED = "PHOTO_SHARE_CREATED"
PHOTO_SHARE_EXPIRED = "PHOTO_SHARE_EXPIRED"
PHOTO_DEVICE_REGISTERED = "PHOTO_DEVICE_REGISTERED"
FACE_RECOGNITION_UPDATED = "FACE_RECOGNITION_UPDATED"

PHOTO_POLL_EVENTS = {
    PHOTO_SHARE_CREATED,
    PHOTO_SHARE_EXPIRED,
    PHOTO_DEVICE_REGISTERED,
    FACE_RECOGNITION_UPDATED,
}

_DEDUP_TTL = 30 * 24 * 3600

def _maybe_int(v):
    if v is None or isinstance(v, bool):
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None

def _sec_to_local_str(sec):
    if sec is None:
        return ""
    try:
        v = int(sec)
    except (TypeError, ValueError):
        return ""
    if v <= 0:
        return "永久有效"
    try:
        return datetime.fromtimestamp(v, tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        return str(v)

def _connect_readonly(db_path, timeout=10.0):
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=timeout)
    return conn

class PhotoDBPoller:
    def __init__(self, db_path, cursor_dir, poll_interval=10, monitor_events=None):
        self.db_path = (db_path or "").strip()
        self.cursor_dir = Path(cursor_dir)
        self.poll_interval = max(1, int(poll_interval or 10))
        self.monitor_events = set(monitor_events or [])
        self.event_handlers = {}
        self.running = False
        self._thread = None
        self._state_file = self.cursor_dir / "photo_db_poller_state.json"
        self._dedup_file = self.cursor_dir / "photo_db_poller_dedup.json"
        self.logger = logging.getLogger(__name__)
        self.cursor_dir.mkdir(parents=True, exist_ok=True)
        self._dedup_seen = {}
        self._missing_db_warned = False

    def add_handler(self, event_type, handler):
        self.event_handlers[event_type] = handler

    def clear_handlers(self):
        self.event_handlers.clear()

    def update_config(self, monitor_events=None, poll_interval=None, db_path=None):
        if monitor_events is not None:
            self.monitor_events = set(monitor_events)
        if poll_interval is not None:
            self.poll_interval = max(1, int(poll_interval))
        if db_path is not None:
            self.db_path = (db_path or "").strip()
            self._missing_db_warned = False

    def _load_state(self):
        default = {
            "version": 1,
            "initialized": False,
            "last_share_link_id": 0,
            "last_device_id": 0,
            "last_face_task_log_id": 0,
        }
        try:
            if self._state_file.exists():
                raw = self._state_file.read_text().strip()
                if raw:
                    obj = json.loads(raw)
                    if isinstance(obj, dict):
                        default.update(obj)
        except Exception as e:
            self.logger.warning("读取相册轮询状态失败: %s", e)
        return default

    def _save_state(self, state):
        try:
            self._state_file.write_text(json.dumps(state, ensure_ascii=False))
        except Exception as e:
            self.logger.warning("写入相册轮询状态失败: %s", e)

    def _load_dedup(self):
        try:
            if self._dedup_file.exists():
                obj = json.loads(self._dedup_file.read_text() or "{}")
                if isinstance(obj, dict):
                    now = int(time.time())
                    self._dedup_seen = {
                        str(k): int(v)
                        for k, v in obj.items()
                        if isinstance(v, (int, float)) and int(v) >= now - _DEDUP_TTL
                    }
                    return
        except Exception as e:
            self.logger.warning("读取相册去重缓存失败: %s", e)
        self._dedup_seen = {}

    def _save_dedup(self):
        try:
            self._dedup_file.write_text(json.dumps(self._dedup_seen, ensure_ascii=False))
        except Exception as e:
            self.logger.warning("写入相册去重缓存失败: %s", e)

    def _prune_dedup(self):
        now = int(time.time())
        self._dedup_seen = {k: v for k, v in self._dedup_seen.items() if int(v) >= now - _DEDUP_TTL}

    def _connect(self):
        conn = _connect_readonly(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _fingerprint(self, kind, key):
        return f"{kind}|{key}"

    def _emit(self, event_type, event_data, raw_obj, ts_sec=None):
        if self.monitor_events and event_type not in self.monitor_events:
            return
        fp = self._fingerprint(event_type, json.dumps(raw_obj, sort_keys=True, ensure_ascii=False)[:400])
        now = int(time.time())
        if fp in self._dedup_seen:
            return
        handler = self.event_handlers.get(event_type)
        if not handler:
            return
        raw_log = json.dumps(event_data, ensure_ascii=False)
        ts = _sec_to_local_str(ts_sec) if ts_sec else datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "type": event_type,
            "timestamp": ts,
            "hostname": "photo.db",
            "message": raw_log,
            "raw_data": raw_log,
        }
        try:
            handler(event_data, entry)
            self._dedup_seen[fp] = now
        except Exception as e:
            self.logger.error("处理相册事件失败 %s: %s", event_type, e, exc_info=True)

    def _owner_label(self, owner_id, nas_uid):
        parts = []
        if nas_uid is not None and str(nas_uid).strip():
            parts.append(f"NAS 用户 UID {nas_uid}")
        if owner_id is not None and str(owner_id).strip():
            parts.append(f"相册用户 id {owner_id}")
        return "，".join(parts) if parts else "未知"

    def _baseline(self, conn, state):
        row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM share_link").fetchone()
        state["last_share_link_id"] = int(row[0] or 0)
        row_d = conn.execute("SELECT COALESCE(MAX(id), 0) FROM device").fetchone()
        state["last_device_id"] = int(row_d[0] or 0)
        row_f = conn.execute("SELECT COALESCE(MAX(id), 0) FROM face_task_log").fetchone()
        state["last_face_task_log_id"] = int(row_f[0] or 0)
        state["initialized"] = True

    def _check_share_link(self, conn, state):
        try:
            rows = conn.execute(
                "SELECT id, title, link, valid_to, owner_id, nas_uid FROM share_link WHERE id > ? ORDER BY id LIMIT 200",
                (state.get("last_share_link_id", 0),),
            ).fetchall()
            for row in rows:
                event_data = {
                    "id": row["id"],
                    "title": row["title"] or "",
                    "link": row["link"] or "",
                    "valid_to": _sec_to_local_str(_maybe_int(row["valid_to"])),
                    "valid_to_ts": _maybe_int(row["valid_to"]),
                    "owner": self._owner_label(row.get("owner_id"), row.get("nas_uid")),
                }
                state["last_share_link_id"] = max(state.get("last_share_link_id", 0), row["id"])
                self._emit(PHOTO_SHARE_CREATED, event_data, dict(row), _maybe_int(row["valid_to"]))
        except Exception as e:
            self.logger.warning("查询 share_link 失败: %s", e)

    def _check_device(self, conn, state):
        try:
            rows = conn.execute(
                "SELECT id, device_name, device_type, owner_id, nas_uid, last_active_time FROM device WHERE id > ? ORDER BY id LIMIT 200",
                (state.get("last_device_id", 0),),
            ).fetchall()
            for row in rows:
                event_data = {
                    "id": row["id"],
                    "device_name": row["device_name"] or "",
                    "device_type": row["device_type"] or "",
                    "owner": self._owner_label(row.get("owner_id"), row.get("nas_uid")),
                    "last_active_time": row["last_active_time"] or "",
                }
                state["last_device_id"] = max(state.get("last_device_id", 0), row["id"])
                self._emit(PHOTO_DEVICE_REGISTERED, event_data, dict(row), None)
        except Exception as e:
            self.logger.warning("查询 device 失败: %s", e)

    def _check_face_task_log(self, conn, state):
        try:
            rows = conn.execute(
                "SELECT id, task_id, status, started_at, finished_at FROM face_task_log WHERE id > ? ORDER BY id LIMIT 200",
                (state.get("last_face_task_log_id", 0),),
            ).fetchall()
            for row in rows:
                event_data = {
                    "id": row["id"],
                    "task_id": row["task_id"] or "",
                    "status": row["status"] or "",
                    "started_at": row["started_at"] or "",
                    "finished_at": row["finished_at"] or "",
                }
                state["last_face_task_log_id"] = max(state.get("last_face_task_log_id", 0), row["id"])
                self._emit(FACE_RECOGNITION_UPDATED, event_data, dict(row), None)
        except Exception as e:
            self.logger.warning("查询 face_task_log 失败: %s", e)

    def _check_expired_shares(self):
        now = int(time.time())
        state = self._load_state()
        last_check = state.get("last_expired_check", 0)
        if now - last_check < 3600:
            return
        try:
            conn = _connect_readonly(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, title, link, valid_to, owner_id, nas_uid FROM share_link WHERE valid_to > 0 AND valid_to < ? LIMIT 100",
                (now,),
            ).fetchall()
            for row in rows:
                event_data = {
                    "id": row["id"],
                    "title": row["title"] or "",
                    "link": row["link"] or "",
                    "valid_to": _sec_to_local_str(_maybe_int(row["valid_to"])),
                    "owner": self._owner_label(row.get("owner_id"), row.get("nas_uid")),
                }
                self._emit(PHOTO_SHARE_EXPIRED, event_data, dict(row), None)
            conn.close()
            state["last_expired_check"] = now
            self._save_state(state)
        except Exception as e:
            self.logger.warning("检查过期分享失败: %s", e)

    def _poll_once(self):
        if not self.db_path:
            if not self._missing_db_warned:
                self.logger.warning("photo.db 路径未设置")
                self._missing_db_warned = True
            return
        if not os.path.exists(self.db_path):
            if not self._missing_db_warned:
                self.logger.warning("photo.db 不存在: %s", self.db_path)
                self._missing_db_warned = True
            return
        self._missing_db_warned = False
        state = self._load_state()
        conn = None
        try:
            conn = self._connect()
            if not state.get("initialized"):
                self._baseline(conn, state)
                self._save_state(state)
            self._check_share_link(conn, state)
            self._check_device(conn, state)
            self._check_face_task_log(conn, state)
            conn.close()
            conn = None
        except Exception as e:
            self.logger.error("轮询 photo.db 失败: %s", e, exc_info=True)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        if PHOTO_SHARE_EXPIRED in self.monitor_events:
            self._check_expired_shares()
        self._save_state(state)
        self._prune_dedup()
        self._save_dedup()

    def _poll_loop(self):
        while self.running:
            try:
                self._poll_once()
            except Exception as e:
                self.logger.error("PhotoDBPoller 轮询异常: %s", e, exc_info=True)
            time.sleep(self.poll_interval)

    def start(self):
        if self.running:
            return
        self.running = True
        self._load_dedup()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="PhotoDBPoller")
        self._thread.start()
        self.logger.info("PhotoDBPoller 已启动，轮询间隔: %ds，监控事件: %s", self.poll_interval, sorted(self.monitor_events))

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._save_state(self._load_state())
        self._save_dedup()
        self.logger.info("PhotoDBPoller 已停止")