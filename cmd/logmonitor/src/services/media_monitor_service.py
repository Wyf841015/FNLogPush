#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""影视库监控服务"""

import os, sqlite3, logging, threading, time, json
from datetime import datetime
from pathlib import Path
from typing import Set, List, Dict, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

MEDIA_RESOURCE_ADDED = "MEDIA_RESOURCE_ADDED"
MEDIA_SCRAPE_SUCCESS = "MEDIA_SCRAPE_SUCCESS"
MEDIA_LOGIN_SUCCESS = "MEDIA_LOGIN_SUCCESS"
MEDIA_LOGOUT = "MEDIA_LOGOUT"

def _ms_to_str(ms):
    if ms is None:
        return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    try:
        v = int(ms)
        if v > 10000000000: v = int(v / 1000)
        return datetime.fromtimestamp(v, tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    except: return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")

def _probe_db(db_path):
    if not db_path or not os.path.exists(db_path): return False
    try:
        c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=3.0)
        c.execute("SELECT 1"); c.close(); return True
    except: return False

class MediaMonitorService:
    def __init__(self, db_path="/usr/local/apps/@appdata/trim.media/database/trimmedia.db",
                 activity_db_path="/usr/local/apps/@appdata/trim.media/database/trimactivity.db",
                 cursor_dir="./data/cursor", poll_interval=10,
                 monitor_events=None, on_event=None):
        self.db_path = db_path
        self.activity_db_path = activity_db_path
        self.cursor_dir = Path(cursor_dir)
        self.poll_interval = max(1, poll_interval)
        self.monitor_events = set(monitor_events or [])
        self.on_event = on_event
        self.running = False
        self._thread = None
        self._state_file = self.cursor_dir / "media_state.json"
        self._dedup_file = self.cursor_dir / "media_dedup.json"
        self._state = {}
        self._dedup = {}
        self.cursor_dir.mkdir(parents=True, exist_ok=True)
        self._load_state()
        self._load_dedup()
        self.db_available = _probe_db(self.db_path)
        self.activity_db_available = _probe_db(self.activity_db_path)
        logger.info(f"MediaMonitor: db={self.db_available}, act={self.activity_db_available}")

    def _load_state(self):
        try:
            if self._state_file.exists():
                self._state = json.loads(self._state_file.read_text(encoding="utf-8"))
        except: self._state = {}

    def _save_state(self):
        try:
            self._state_file.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
        except: pass

    def _load_dedup(self):
        try:
            if self._dedup_file.exists():
                self._dedup = json.loads(self._dedup_file.read_text(encoding="utf-8"))
                now = time.time()
                self._dedup = {k: v for k, v in self._dedup.items() if now - v < 86400}
        except: self._dedup = {}

    def _save_dedup(self):
        try:
            self._dedup_file.write_text(json.dumps(self._dedup, ensure_ascii=False), encoding="utf-8")
        except: pass

    def _should_notify(self, key):
        now = time.time()
        if key in self._dedup and now - self._dedup[key] < 3600: return False
        self._dedup[key] = now
        self._save_dedup()
        return True

    def update_config(self, **kw):
        if "db_path" in kw:
            self.db_path = kw["db_path"]; self.db_available = _probe_db(self.db_path)
        if "activity_db_path" in kw:
            self.activity_db_path = kw["activity_db_path"]; self.activity_db_available = _probe_db(self.activity_db_path)
        if "poll_interval" in kw: self.poll_interval = max(1, kw["poll_interval"])
        if "monitor_events" in kw: self.monitor_events = set(kw["monitor_events"])

    def _poll_loop(self):
        logger.info("MediaMonitor started")
        while self.running:
            try:
                events = []
                if self.db_available and os.path.exists(self.db_path):
                    events.extend(self._poll_media())
                if self.activity_db_available and os.path.exists(self.activity_db_path):
                    events.extend(self._poll_activity())
                if events and self.on_event:
                    try: self.on_event(events)
                    except Exception as e: logger.error(f"Callback error: {e}")
                self._save_state()
            except Exception as e: logger.error(f"Poll error: {e}")
            for _ in range(self.poll_interval):
                if not self.running: break
                time.sleep(1)
        logger.info("MediaMonitor stopped")

    def _poll_media(self):
        events = []
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if MEDIA_RESOURCE_ADDED in self.monitor_events:
                last = self._state.get("item_cursor", 0)
                cur.execute("SELECT id,item_type,title,title_original,year,added_at FROM item WHERE id>? AND item_type IN ('Movie','TV','Season','Episode') ORDER BY id ASC LIMIT 50", (last,))
                for row in cur.fetchall():
                    if self._should_notify(f"res_{row['id']}"):
                        events.append({"type": MEDIA_RESOURCE_ADDED, "title": row['title'] or row['title_original'] or f"ID:{row['id']}", "item_type": row['item_type'], "year": row['year'], "time": _ms_to_str(row['added_at'])})
                cur.execute("SELECT MAX(id) FROM item")
                r = cur.fetchone()
                if r and r[0]: self._state["item_cursor"] = r[0]
            if MEDIA_SCRAPE_SUCCESS in self.monitor_events:
                last_ft = self._state.get("fetch_check", 0)
                cur.execute("SELECT id,item_type,title,title_original,year,fetch_time FROM item WHERE fetch_status=1 AND item_type IN ('Movie','TV','Episode') AND fetch_time>? ORDER BY fetch_time ASC LIMIT 30", (last_ft,))
                for row in cur.fetchall():
                    if self._should_notify(f"scr_{row['id']}"):
                        events.append({"type": MEDIA_SCRAPE_SUCCESS, "title": row['title'] or row['title_original'] or f"ID:{row['id']}", "item_type": row['item_type'], "year": row['year'], "time": _ms_to_str(row['fetch_time'])})
                    if row['fetch_time'] and row['fetch_time'] > last_ft: last_ft = row['fetch_time']
                if last_ft > 0: self._state["fetch_check"] = last_ft
            conn.close()
        except Exception as e: logger.error(f"Poll media error: {e}")
        return events

    def _poll_activity(self):
        events = []
        try:
            conn = sqlite3.connect(f"file:{self.activity_db_path}?mode=ro", uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            last = self._state.get("activity_cursor", 0)
            cur.execute("SELECT id,username,action,create_time,ip_address FROM activity_log WHERE id>? ORDER BY id ASC LIMIT 50", (last,))
            for row in cur.fetchall():
                ev_type = None
                if MEDIA_LOGIN_SUCCESS in self.monitor_events and row['action'] in ('login', 'login_success', 'LoginSucc'): ev_type = MEDIA_LOGIN_SUCCESS
                elif MEDIA_LOGOUT in self.monitor_events and row['action'] in ('logout', 'Logout'): ev_type = MEDIA_LOGOUT
                if ev_type and self._should_notify(f"act_{row['id']}"):
                    events.append({"type": ev_type, "username": row['username'] or "Unknown", "action": row['action'], "time": _ms_to_str(row['create_time']), "ip": row['ip_address'] or ""})
            cur.execute("SELECT MAX(id) FROM activity_log")
            r = cur.fetchone()
            if r and r[0]: self._state["activity_cursor"] = r[0]
            conn.close()
        except Exception as e: logger.error(f"Poll activity error: {e}")
        return events

    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="MediaMonitor")
        self._thread.start()
        logger.info("MediaMonitor started")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        self._save_state()
        self._save_dedup()
        logger.info("MediaMonitor stopped")

    def get_stats(self):
        return {
            "running": self.running,
            "db_available": self.db_available,
            "activity_db_available": self.activity_db_available,
            "db_path": self.db_path,
            "activity_db_path": self.activity_db_path,
            "poll_interval": self.poll_interval,
            "monitor_events": list(self.monitor_events)
        }
