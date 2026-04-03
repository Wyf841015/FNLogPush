#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件映射配置
定义日志级别、分类和事件ID的映射关系
"""
from typing import Dict


class EventMappings:
    """事件映射类"""

    # 日志级别映射
    LEVEL_MAP = {
        0: "普通",
        1: "警告",
        2: "错误",
        3: "严重错误",
        4: "FATAL"
    }

    # 日志级别图标映射
    LEVEL_ICON_MAP = {
        "普通": "📝",
        "警告": "⚠️",
        "错误": "❌",
        "严重错误": "💥",
        "FATAL": "💥"
    }

    # 日志分类映射
    CATEGORY_MAP = {
        0: 'SYSTEM-系统',
        1: 'SECURITY-安全',
        2: 'APPLICATION-应用',
        3: 'DISK-磁盘',
        4: 'USER-用户'
    }

    def __init__(self):
        """初始化事件映射"""
        # 构建反向映射（级别名称 -> 级别代码）
        self.LEVEL_NAME_TO_CODE = {v: k for k, v in self.LEVEL_MAP.items()}
    
    # 事件ID中文名称映射
    EVENT_NAME_MAP = {
        # 登录认证
        'LoginSucc': '登录成功',
        'LoginSucc2FA1': '登录成功(双因素)',
        'LoginFail': '登录失败',
        'Logout': '退出',
        # SSH连接
        'SSH_INVALID_USER': 'SSH无效用户',
        'SSH_AUTH_FAILED': 'SSH认证失败',
        'SSH_DISCONNECTED': 'SSH断开连接',
        'SshdLoginSucc': 'SSH登录成功',
        # 文件操作
        'CreateFile': '创建文件',
        'DeleteFile': '删除文件',
        'CopyFile': '复制文件',
        'MoveFile': '移动文件',
        'RenameFile': '重命名文件',
        'ModifyFile': '修改文件',
        'FileUpload': '文件上传',
        'FileDownload': '文件下载',
        'FileAccess': '访问文件',
        'FilePermission': '文件权限变更',
        'FileSync': '文件同步',
        'FileCompress': '文件压缩',
        'FileExtract': '文件解压',
        'FileEncrypt': '文件加密',
        'FileDecrypt': '文件解密',
        'FileBackup': '文件备份',
        'FileRestore': '文件恢复',
        # 应用管理
        'APP_CRASH': '应用崩溃',
        'APP_UPDATE_FAILED': '应用更新失败',
        'APP_START_FAILED': '应用启动失败',
        'LOCAL_APP_RUN_EXCEPTION': '本地应用异常',
        'APP_AUTO_START_FAILED_DOCKER_NOT_AVAILABLE': '自动启动失败(Docker)',
        'APP_STARTED': '应用已启动',
        'APP_STOPPED': '应用已停止',
        'APP_UPDATED': '应用已更新',
        'APP_INSTALLED': '应用已安装',
        'APP_AUTO_STARTED': '应用自动启动',
        'APP_UNINSTALLED': '应用已卸载',
        'APP_INSTALL_FAILED_DEPENDENCT_AND_CONFLICT': '应用安装失败(依赖冲突)',
        # 系统监控
        'CPU_USAGE_ALARM': 'CPU使用率告警',
        'CPU_USAGE_RESTORED': 'CPU使用率恢复',
        'CPU_TEMPERATURE_ALARM': 'CPU温度告警',
        'MemoryUsageAlarm': '内存使用告警',
        'MEMORY_USAGE_ALARM': '内存使用率告警',
        'MEMORY_USAGE_RESTORED': '内存使用率恢复',
        'DiskUsageAlarm': '磁盘使用告警',
        'NetworkUsageAlarm': '网络流量告警',
        'ProcessHighCPU': '进程高CPU占用',
        'ProcessHighMemory': '进程高内存占用',
        # UPS电源
        'UPS_ONBATT': 'UPS电池供电',
        'UPS_ONBATT_LOWBATT': 'UPS低电量',
        'UPS_ONLINE': 'UPS在线',
        'UPS_ENABLE': 'UPS启用',
        'UPS_DISABLE': 'UPS禁用',
        # 磁盘管理
        'FoundDisk': '发现磁盘',
        'DiskWakeup': '磁盘唤醒',
        'DiskSpindown': '磁盘休眠',
        'DISK_IO_ERR': '磁盘IO错误',
        'DiskFull': '磁盘空间不足',
        'DiskCorrupt': '磁盘损坏',
        'DiskFormat': '磁盘格式化',
        'DiskPartition': '磁盘分区',
        # 存储管理
        'CreateStorage': '创建存储',
        'MountStorage': '挂载存储',
        'UnmountStorage': '卸载存储',
        'DeleteStorage': '删除存储',
        'STORAGE_MOUNT_SUCCESS': '存储挂载成功',
        'STORAGE_MOUNT_FAILED': '存储挂载失败',
        'STORAGE_UMOUNT_SUCCESS': '存储卸载成功',
        'STORAGE_UMOUNT_FAILED': '存储卸载失败',
        # 防火墙
        'FW_ENABLE': '防火墙启用',
        'FW_DISABLE': '防火墙禁用',
        'FW_START_SUCCESS': '防火墙启动成功',
        'FW_START_FAILED': '防火墙启动失败',
        'FW_STOP_SUCCESS': '防火墙停止成功',
        'FW_STOP_FAILED': '防火墙停止失败',
        # NFS事件
        'NFS_MOUNT_SUCCESS': 'NFS挂载成功',
        'NFS_MOUNT_FAILED': 'NFS挂载失败',
        'NFS_UMOUNT': 'NFS卸载',
        'NFS_ACCESS_DENIED': 'NFS访问拒绝',
        'NFS_TIMEOUT': 'NFS超时',
        'NFS_ENABLED': 'NFS启用',
        'NFS_DISABLED': 'NFS禁用',
        # SMB/CIFS事件
        'SAMBA_CONNECT_SUCCESS': 'SMB连接成功',
        'SAMBA_CONNECT_FAILED': 'SMB连接失败',
        'SAMBA_DISCONNECT': 'SMB断开连接',
        'SAMBA_AUTH_FAILED': 'SMB认证失败',
        'SAMBA_SHARE_CREATED': 'SMB共享创建',
        'SAMBA_SHARE_DELETED': 'SMB共享删除',
        'SAMBA_SHARE_MODIFIED': 'SMB共享修改',
        'SAMBA_ACCESS_DENIED': 'SMB访问拒绝',
        'SAMBA_ENABLED': 'SMB启用',
        'SAMBA_DISABLED': 'SMB禁用',
        'SAMBA_SESSION_OPEN': 'SMB会话打开',
        'SAMBA_SESSION_CLOSE': 'SMB会话关闭',
        # FTP事件
        'FTP_LOGIN_SUCCESS': 'FTP登录成功',
        'FTP_LOGIN_FAILED': 'FTP登录失败',
        'FTP_DISCONNECT': 'FTP断开连接',
        'FTP_UPLOAD_START': 'FTP上传开始',
        'FTP_UPLOAD_SUCCESS': 'FTP上传成功',
        'FTP_UPLOAD_FAILED': 'FTP上传失败',
        'FTP_DOWNLOAD_START': 'FTP下载开始',
        'FTP_DOWNLOAD_SUCCESS': 'FTP下载成功',
        'FTP_DOWNLOAD_FAILED': 'FTP下载失败',
        'FTP_DELETE_FILE': 'FTP删除文件',
        'FTP_CREATE_DIR': 'FTP创建目录',
        'FTP_DELETE_DIR': 'FTP删除目录',
        'FTP_ENABLED': 'FTP启用',
        'FTP_DISABLED': 'FTP禁用',
        # AFP事件
        'AFP_CONNECT_SUCCESS': 'AFP连接成功',
        'AFP_CONNECT_FAILED': 'AFP连接失败',
        'AFP_LOGIN_SUCCESS': 'AFP登录成功',
        'AFP_LOGIN_FAILED': 'AFP登录失败',
        'AFP_DISCONNECT': 'AFP断开连接',
        'AFP_VOLUME_MOUNT': 'AFP卷挂载',
        'AFP_VOLUME_UMOUNT': 'AFP卷卸载',
        'AFP_ENABLED': 'AFP启用',
        'AFP_DISABLED': 'AFP禁用',
        # WebDAV事件
        'WEBDAV_CONNECT_SUCCESS': 'WebDAV连接成功',
        'WEBDAV_CONNECT_FAILED': 'WebDAV连接失败',
        'WEBDAV_AUTH_FAILED': 'WebDAV认证失败',
        'WEBDAV_GET_SUCCESS': 'WebDAV获取成功',
        'WEBDAV_GET_FAILED': 'WebDAV获取失败',
        'WEBDAV_PUT_SUCCESS': 'WebDAV上传成功',
        'WEBDAV_PUT_FAILED': 'WebDAV上传失败',
        'WEBDAV_DELETE_SUCCESS': 'WebDAV删除成功',
        'WEBDAV_DELETE_FAILED': 'WebDAV删除失败',
        'WEBDAV_ENABLED': 'WebDAV启用',
        'WEBDAV_DISABLED': 'WebDAV禁用',
        # DLNA事件
        'DLNA_ENABLED': 'DLNA启用',
        'DLNA_DISABLED': 'DLNA禁用',
        # 共享协议事件
        'SHARE_EVENTID_PUT': '共享文件上传',
        'SHARE_EVENTID_DEL': '共享文件删除',
        'SHARE_EVENTID_MKDIR': '共享目录创建',
        'SHARE_EVENTID_RENAME': '共享文件重命名',
        # 防火墙事件
        'FW_RULE_CHANGED': '防火墙规则变更'
    }
    
    @classmethod
    def get_level_name(cls, level_code: int) -> str:
        """获取日志级别名称"""
        return cls.LEVEL_MAP.get(level_code, "未知")
    
    @classmethod
    def get_level_icon(cls, level_name: str) -> str:
        """获取日志级别图标"""
        return cls.LEVEL_ICON_MAP.get(level_name, "📌")
    
    @classmethod
    def get_category_name(cls, category_code: int) -> str:
        """获取日志分类名称"""
        return cls.CATEGORY_MAP.get(category_code, "未知")
    
    @classmethod
    def get_event_name(cls, event_id: str) -> str:
        """获取事件中文名称"""
        return cls.EVENT_NAME_MAP.get(event_id, event_id)
