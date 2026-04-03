#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用主入口
"""
import sys
import os
from pathlib import Path

# 获取应用代码目录
MAIN_FILE = Path(__file__).resolve()
SRC_DIR = MAIN_FILE.parent
CODE_DIR = SRC_DIR.parent

# 添加到Python路径
sys.path.insert(0, str(CODE_DIR))
sys.path.insert(0, str(SRC_DIR))

# 导入并运行main
from app import main

if __name__ == '__main__':
    main()
