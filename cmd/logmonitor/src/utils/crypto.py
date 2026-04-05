#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密工具模块
提供敏感信息的加密和解密功能
"""
import os
import base64
import hashlib
from typing import Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = __import__('logging').getLogger(__name__)


class CryptoManager:
    """加密管理器"""
    
    def __init__(self, key: Optional[bytes] = None):
        """
        初始化加密管理器
        
        Args:
            key: 加密密钥，默认从环境变量或机器特征生成
        """
        self._key = key or self._get_or_create_key()
        self._fernet = None
        if HAS_CRYPTO:
            try:
                self._fernet = Fernet(self._key)
            except Exception as e:
                logger.warning(f"加密初始化失败: {e}")
    
    def _get_or_create_key(self) -> bytes:
        """获取或创建加密密钥"""
        # 1. 优先从环境变量读取
        env_key = os.environ.get('FNLOGPUSH_ENCRYPT_KEY')
        if env_key:
            return self._derive_key(env_key)
        
        # 2. 从配置文件读取
        config_key = self._load_config_key()
        if config_key:
            return base64.urlsafe_b64decode(config_key)
        
        # 3. 生成新密钥
        if HAS_CRYPTO:
            new_key = Fernet.generate_key()
            self._save_config_key(new_key)
            logger.warning("生成了新的加密密钥，请设置 FNLOGPUSH_ENCRYPT_KEY 环境变量固定")
            return new_key
        
        # 4. 降级方案：使用机器特征生成（仅用于混淆，不可恢复）
        logger.warning("cryptography 库未安装，使用简单哈希加密（安全性较低）")
        machine_id = hashlib.sha256(
            f"{os.environ.get('HOSTNAME', 'default')}-{os.environ.get('USER', 'user')}".encode()
        ).digest()[:32]
        return base64.urlsafe_b64encode(machine_id)
    
    def _derive_key(self, password: str) -> bytes:
        """从密码派生密钥"""
        if not HAS_CRYPTO:
            return base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'fnlogpush-salt-v1',
            iterations=480000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _load_config_key(self) -> Optional[str]:
        """从配置文件加载密钥"""
        try:
            # 尝试在 APP_HOME 下查找密钥文件
            app_home = os.environ.get('APP_HOME', '')
            if app_home:
                key_file = os.path.join(app_home, 'config', '.encrypt_key')
                if os.path.exists(key_file):
                    with open(key_file, 'r') as f:
                        return f.read().strip()
        except Exception:
            pass
        return None
    
    def _save_config_key(self, key: bytes):
        """保存密钥到配置文件"""
        try:
            app_home = os.environ.get('APP_HOME', '')
            if app_home:
                key_file = os.path.join(app_home, 'config', '.encrypt_key')
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                with open(key_file, 'w') as f:
                    f.write(base64.urlsafe_b64encode(key).decode())
        except Exception as e:
            logger.error(f"保存加密密钥失败: {e}")
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串
        
        Args:
            plaintext: 明文
            
        Returns:
            密文（Base64编码）
        """
        if not plaintext:
            return plaintext
        
        try:
            if self._fernet:
                encrypted = self._fernet.encrypt(plaintext.encode('utf-8'))
                return '__enc__' + base64.urlsafe_b64encode(encrypted).decode('ascii')
            else:
                # 降级方案：简单XOR加密
                key = self._key[:len(plaintext)]
                encrypted = ''.join(
                    chr(ord(c) ^ ord(k)) for c, k in zip(plaintext, key)
                )
                return '__xor__' + base64.b64encode(encrypted.encode()).decode('ascii')
        except Exception as e:
            logger.error(f"加密失败: {e}")
            return plaintext
    
    def decrypt(self, ciphertext: str) -> str:
        """
        解密字符串
        
        Args:
            ciphertext: 密文
            
        Returns:
            明文
        """
        if not ciphertext:
            return ciphertext
        
        try:
            if ciphertext.startswith('__enc__') and self._fernet:
                encrypted = base64.urlsafe_b64decode(ciphertext[7:].encode('ascii'))
                return self._fernet.decrypt(encrypted).decode('utf-8')
            elif ciphertext.startswith('__xor__'):
                encrypted = base64.b64decode(ciphertext[7:].encode('ascii')).decode('ascii')
                key = self._key[:len(encrypted)]
                return ''.join(
                    chr(ord(c) ^ ord(k)) for c, k in zip(encrypted, key)
                )
            else:
                # 可能是未加密的明文
                return ciphertext
        except Exception as e:
            logger.error(f"解密失败: {e}")
            return ciphertext


# 全局加密管理器实例
_crypto_manager: Optional[CryptoManager] = None


def get_crypto_manager() -> CryptoManager:
    """获取全局加密管理器实例"""
    global _crypto_manager
    if _crypto_manager is None:
        _crypto_manager = CryptoManager()
    return _crypto_manager


def encrypt_value(value: str) -> str:
    """便捷加密函数"""
    return get_crypto_manager().encrypt(value)


def decrypt_value(value: str) -> str:
    """便捷解密函数"""
    return get_crypto_manager().decrypt(value)


# 敏感字段列表（这些字段的值需要加密存储）
SENSITIVE_FIELDS = [
    'webhook_url',
    'wecom.webhook_url',
    'wecom.secret',
    'dingtalk.webhook_url',
    'dingtalk.secret',
    'feishu.webhook_url',
    'bark.device_key',
    'pushplus.token',
    'meow.token',
]


def is_sensitive_field(field_path: str) -> bool:
    """检查字段是否为敏感字段"""
    return field_path in SENSITIVE_FIELDS
