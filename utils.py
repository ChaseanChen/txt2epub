# utils.py
import os
import sys
import re

def get_app_root():
    """
    获取应用程序的“根目录”。
    1. 如果是被 PyInstaller 打包成 exe，则返回 exe 所在目录。
    2. 如果是脚本运行，则返回脚本所在目录。
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def sanitize_filename(filename):
    """
    清理文件名中的非法字符，防止保存文件时出错。
    """
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def ensure_dirs(root_path, subdirs):
    """
    批量创建目录并进行权限检查。
    """
    for d in subdirs:
        full_path = os.path.join(root_path, d)
        if not os.path.exists(full_path):
            try:
                os.makedirs(full_path)
                print(f"初始化目录: {full_path}")
            except OSError as e:
                print(f"无法创建目录 {full_path}: {e}")
                raise PermissionError(f"无法创建目录，请检查权限: {full_path}")