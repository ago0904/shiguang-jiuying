#!/usr/bin/env python
"""
Django 管理命令入口
"""
import os
import sys


def main():
    """执行 Django 管理命令"""
    # 设置默认的 settings 模块
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shiguang.settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django。请确保 Django 已安装并且在 "
            "PYTHONPATH 环境变量中可用。是否忘记了激活虚拟环境？"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
