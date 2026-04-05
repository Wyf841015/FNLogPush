#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证服务模块
处理用户登录、密码加密和验证

安全说明:
  - 密码哈希使用 bcrypt（每个密码独立随机盐）
  - 保留对旧 SHA-256 哈希的兼容迁移：首次用旧哈希验证成功后，自动将密码升级为 bcrypt
  - 登录失败计数 + 账号锁定机制（防暴力破解）
  - bcrypt 为强制依赖，若未安装则启动时报错退出
"""
import json
import os
import hashlib
import logging
import threading
import time
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# bcrypt 是强制依赖，不可用时直接报错退出（不降级到 SHA-256）
try:
    import bcrypt
except ImportError as _bcrypt_err:
    raise RuntimeError(
        "bcrypt 未安装，无法启动认证服务。"
        "请执行 pip install bcrypt 后重试。"
    ) from _bcrypt_err


# --------------------------------------------------------------------------- #
#  旧方案辅助函数（仅用于兼容迁移，不对外暴露）
# --------------------------------------------------------------------------- #
_LEGACY_SALT = "fnos_log_monitor_secret_salt_2024"


def _legacy_hash(password: str) -> str:
    """旧版固定盐 SHA-256 哈希（仅用于读取旧格式哈希做一次性迁移，不用于新密码存储）"""
    return hashlib.sha256((password + _LEGACY_SALT).encode('utf-8')).hexdigest()


# --------------------------------------------------------------------------- #
#  登录限速常量
# --------------------------------------------------------------------------- #
MAX_LOGIN_FAILURES = 5          # 最大连续失败次数
LOCKOUT_DURATION = 300          # 锁定时长（秒），5 分钟


class AuthService:
    """认证服务类"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            # 从环境变量获取APP_HOME
            app_home = os.environ.get('APP_HOME', os.getcwd())
            config_path = os.path.join(app_home, 'config', 'config.json')
        self.config_path = config_path
        self.config = self._load_config()

        # 登录失败计数器（内存中，重启后清零）
        self._login_failures: Dict[str, int] = {}
        self._lockout_until: Dict[str, float] = {}
        self._rate_lock = threading.Lock()

    # ----------------------------------------------------------------------- #
    #  配置读写
    # ----------------------------------------------------------------------- #

    def _load_config(self) -> Dict:
        """加载配置文件（处理加密）"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 解密 auth 部分（如果被加密）
                return self._decrypt_auth(config)
            return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    def _decrypt_auth(self, config: Dict) -> Dict:
        """解密配置中的 auth 部分"""
        if 'auth' in config and isinstance(config['auth'], dict):
            auth = config['auth']
            for key in ('username', 'password_hash'):
                if key in auth and isinstance(auth[key], str):
                    # 检查是否加密（ConfigManager 会加密这些字段）
                    if auth[key].startswith('__enc__') or auth[key].startswith('__xor__'):
                        try:
                            from utils.crypto import decrypt_value
                            auth[key] = decrypt_value(auth[key])
                            logger.info(f"已解密 auth.{key}")
                        except Exception as e:
                            logger.warning(f"解密 auth.{key} 失败: {e}")
        return config

    def _save_config(self) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False

    # ----------------------------------------------------------------------- #
    #  密码哈希（bcrypt 优先）
    # ----------------------------------------------------------------------- #

    @staticmethod
    def _hash_password(password: str) -> str:
        """使用 bcrypt 对密码进行哈希（每次生成独立随机盐）。"""
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8')

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        """
        验证密码。
        自动识别 bcrypt 哈希（以 $2 开头）和旧版 SHA-256 哈希（一次性迁移兼容）。
        """
        if stored_hash.startswith('$2'):
            # bcrypt 格式
            try:
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
            except Exception as e:
                logger.error(f"bcrypt 验证失败: {e}")
                return False
        else:
            # 旧版 SHA-256（64位十六进制字符串），仅用于一次性迁移
            return _legacy_hash(password) == stored_hash

    # ----------------------------------------------------------------------- #
    #  登录限速 / 账号锁定
    # ----------------------------------------------------------------------- #

    def _check_rate_limit(self, username: str) -> Tuple[bool, str]:
        """
        检查是否触发登录限速。

        Returns:
            (allowed, reason) — allowed=False 时禁止登录
        """
        with self._rate_lock:
            lockout_time = self._lockout_until.get(username, 0)
            if lockout_time and time.time() < lockout_time:
                remaining = int(lockout_time - time.time())
                return False, f"账号已锁定，请 {remaining} 秒后再试"
            return True, ""

    def _record_login_failure(self, username: str):
        """记录登录失败，达到上限时锁定账号"""
        with self._rate_lock:
            self._login_failures[username] = self._login_failures.get(username, 0) + 1
            failures = self._login_failures[username]
            if failures >= MAX_LOGIN_FAILURES:
                self._lockout_until[username] = time.time() + LOCKOUT_DURATION
                self._login_failures[username] = 0
                logger.warning(
                    f"账号 '{username}' 连续失败 {MAX_LOGIN_FAILURES} 次，"
                    f"锁定 {LOCKOUT_DURATION} 秒"
                )

    def _record_login_success(self, username: str):
        """登录成功后清除失败计数"""
        with self._rate_lock:
            self._login_failures.pop(username, None)
            self._lockout_until.pop(username, None)

    # ----------------------------------------------------------------------- #
    #  公开接口
    # ----------------------------------------------------------------------- #

    def is_first_run(self) -> bool:
        """检查是否为首次运行（未设置用户名和密码）"""
        return 'auth' not in self.config or not self.config.get('auth', {}).get('username')

    def setup_initial_user(self, username: str, password: str) -> Tuple[bool, str]:
        """设置初始用户名和密码"""
        if not username or not password:
            return False, "用户名和密码不能为空"
        if len(username) < 3:
            return False, "用户名至少需要3个字符"
        if len(password) < 6:
            return False, "密码至少需要6个字符"

        password_hash = self._hash_password(password)
        self.config['auth'] = {
            'username': username,
            'password_hash': password_hash
        }

        logger.info(f"设置初始用户: {username}, 密码哈希长度: {len(password_hash)}")
        
        if self._save_config():
            logger.info(f"初始用户设置成功: {username}")
            # 验证保存是否成功
            test_config = self._load_config()
            if 'auth' in test_config and test_config['auth'].get('username') == username:
                logger.info(f"配置保存验证成功")
            else:
                logger.error(f"配置保存验证失败")
            return True, "用户设置成功"
        return False, "保存配置失败"

    def verify_login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        验证登录凭证（含限速检查）。
        如验证通过且哈希为旧版格式，自动升级为 bcrypt。
        """
        # 0. 强制重新加载配置（确保读取最新保存的数据）
        self.config = self._load_config()
        
        # 1. 限速检查
        allowed, reason = self._check_rate_limit(username)
        if not allowed:
            return False, reason

        # 2. 基础校验
        if 'auth' not in self.config:
            logger.warning(f"验证登录失败: auth 配置不存在")
            return False, "用户未设置"

        auth_config = self.config['auth']
        stored_username = auth_config.get('username')
        stored_hash = auth_config.get('password_hash')

        logger.info(f"验证登录: 输入用户={username}, 存储用户={stored_username}, 哈希长度={len(stored_hash) if stored_hash else 0}")
        logger.debug(f"密码哈希: {stored_hash[:20]}..." if stored_hash else "无")

        if not stored_username or not stored_hash:
            return False, "用户未设置"

        # 3. 用户名校验
        if username != stored_username:
            self._record_login_failure(username)
            return False, "用户名或密码错误"

        # 4. 密码校验
        if not self._verify_password(password, stored_hash):
            self._record_login_failure(username)
            return False, "用户名或密码错误"

        # 5. 登录成功
        self._record_login_success(username)

        # 6. 自动迁移旧哈希 → bcrypt（仅当前存储的是旧 SHA-256 格式时）
        if not stored_hash.startswith('$2'):
            logger.info(f"自动将用户 '{username}' 的密码哈希升级为 bcrypt")
            new_hash = self._hash_password(password)
            self.config['auth']['password_hash'] = new_hash
            self._save_config()

        return True, "登录成功"

    def change_password(self, old_password: str, new_password: str) -> Tuple[bool, str]:
        """修改密码"""
        if 'auth' not in self.config:
            return False, "用户未设置"
        if len(new_password) < 6:
            return False, "新密码至少需要6个字符"

        auth_config = self.config['auth']
        stored_hash = auth_config.get('password_hash', '')

        if not self._verify_password(old_password, stored_hash):
            return False, "旧密码错误"

        new_hash = self._hash_password(new_password)
        self.config['auth']['password_hash'] = new_hash

        if self._save_config():
            logger.info("密码修改成功")
            return True, "密码修改成功"
        return False, "保存配置失败"

    def get_username(self) -> Optional[str]:
        """获取用户名（不返回密码）"""
        return self.config.get('auth', {}).get('username')
