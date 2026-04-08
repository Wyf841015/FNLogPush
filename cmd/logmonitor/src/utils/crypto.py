#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密工具模块
提供敏感信息的加密和解密功能
"""
import os
import base64
import hashlib
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = __import__('logging').getLogger(__name__)


def _get_key_storage_dir() -> Optional[Path]:
    """获取密钥存储目录，尝试多个可能的位置"""
    # 1. 优先使用 TRIM_PKGVAR（FPK标准变量）
    trim_pkgvar = os.environ.get('TRIM_PKGVAR', '')
    if trim_pkgvar:
        key_dir = Path(trim_pkgvar) / 'config'
        try:
            os.makedirs(key_dir, exist_ok=True)
            return key_dir
        except Exception as e:
            logger.debug(f"TRIM_PKGVAR 路径不可用: {e}")
    
    # 2. 使用 APP_HOME
    app_home = os.environ.get('APP_HOME', '')
    if app_home:
        key_dir = Path(app_home) / 'config'
        try:
            os.makedirs(key_dir, exist_ok=True)
            return key_dir
        except Exception as e:
            logger.debug(f"APP_HOME 路径不可用: {e}")
    
    # 3. 使用应用数据目录（兼容不同平台）
    for base in [os.environ.get('HOME', ''), '/tmp', '.']:
        if base:
            key_dir = Path(base) / '.fnlogpush'
            try:
                os.makedirs(key_dir, exist_ok=True)
                test_file = key_dir / '.test'
                test_file.touch()
                test_file.unlink()
                return key_dir
            except Exception:
                pass
    
    return None


def _get_config_key_direct() -> Optional[str]:
    """直接从配置文件读取密钥，绕过 APP_HOME 检查"""
    try:
        # 尝试多个可能的密钥文件位置
        locations = []
        
        trim_pkgvar = os.environ.get('TRIM_PKGVAR', '')
        if trim_pkgvar:
            locations.append(Path(trim_pkgvar) / 'config' / '.encrypt_key')
        
        app_home = os.environ.get('APP_HOME', '')
        if app_home:
            locations.append(Path(app_home) / 'config' / '.encrypt_key')
        
        # 也检查 config.json 同目录
        for base in [trim_pkgvar, app_home, os.environ.get('HOME', ''), '.']:
            if base:
                locations.append(Path(base) / 'config' / '.encrypt_key')
        
        for key_file in locations:
            if key_file.exists():
                with open(key_file, 'r') as f:
                    key = f.read().strip()
                    if key:
                        logger.debug(f"从 {key_file} 加载加密密钥")
                        return key
    except Exception as e:
        logger.debug(f"直接读取密钥失败: {e}")
    return None


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
        
        # 2. 从配置文件直接读取（绕过目录检查）
        config_key = _get_config_key_direct()
        if config_key:
            try:
                return base64.urlsafe_b64decode(config_key)
            except Exception as e:
                logger.warning(f"解析密钥失败: {e}")
        
        # 3. 从 _load_config_key 读取（备用）
        config_key = self._load_config_key()
        if config_key:
            return base64.urlsafe_b64decode(config_key)
        
        # 4. 生成新密钥
        if HAS_CRYPTO:
            new_key = Fernet.generate_key()
            self._save_config_key(new_key)
            logger.info("已生成并保存新的加密密钥")
            return new_key
        
        # 5. 降级方案：使用机器特征生成（仅用于混淆，不可恢复）
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
            key_dir = _get_key_storage_dir()
            if key_dir:
                key_file = key_dir / '.encrypt_key'
                if key_file.exists():
                    with open(key_file, 'r') as f:
                        return f.read().strip()
        except Exception as e:
            logger.debug(f"加载加密密钥失败: {e}")
        return None
    
    def _save_config_key(self, key: bytes):
        """保存密钥到配置文件"""
        try:
            key_dir = _get_key_storage_dir()
            if key_dir:
                key_file = key_dir / '.encrypt_key'
                key_dir.mkdir(parents=True, exist_ok=True)
                with open(key_file, 'w') as f:
                    f.write(base64.urlsafe_b64encode(key).decode())
                logger.info(f"加密密钥已保存到: {key_file}")
            else:
                logger.error("无法找到可写的密钥存储目录")
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


def is_sensitive_field(field_path: str) -> bool:
    """检查字段是否为敏感字段"""
    from utils.constants import SENSITIVE_FIELDS
    # 检查完整路径和字段名
    return field_path in SENSITIVE_FIELDS or field_path.split('.')[-1] in SENSITIVE_FIELDS
