# utils.py
import os
import sys
import re

def get_app_root():
    """
    获取应用程序的“根目录”。
    兼容 PyInstaller 打包环境与开发脚本环境。
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def sanitize_filename(filename):
    """
    清理文件名中的非法字符，防止保存文件时出错。
    保留空格、中文字符等合法字符。
    """
    # 替换 Windows/Linux 文件系统中的非法字符
    cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)
    # 去除首尾空格和点（Windows 不喜欢文件名以点结尾）
    return cleaned.strip().strip('.')

def ensure_dirs(root_path, subdirs):
    """
    批量创建目录并进行权限检查。
    """
    for d in subdirs:
        full_path = os.path.join(root_path, d)
        if not os.path.exists(full_path):
            try:
                os.makedirs(full_path)
                print(f"[Init] 创建目录: {full_path}")
            except OSError as e:
                raise PermissionError(f"无法创建目录 '{full_path}'。请检查是否有写入权限或磁盘已满。\n系统错误: {e}")