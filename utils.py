# utils.py

import os
import sys
import re
from typing import Optional 

def get_app_root():
    """获取应用程序根目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def sanitize_filename(filename):
    """清理文件名"""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)
    return cleaned.strip().strip('.')

def ensure_dirs(root_path, subdirs):
    """批量创建目录"""
    for d in subdirs:
        full_path = os.path.join(root_path, d)
        if not os.path.exists(full_path):
            try:
                os.makedirs(full_path)
            except OSError as e:
                raise PermissionError(f"无法创建目录 '{full_path}'\n系统错误: {e}")

def detect_file_encoding(file_path: str) -> Optional[str]:
    """
    尝试检测文件编码。
    相比原来的暴力尝试，这里封装成函数，便于复用。
    """
    encodings = ['utf-8', 'gb18030', 'gbk', 'big5', 'utf-16']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                # 读取少量内容进行测试，而不是全量读取
                f.read(4096)
            return enc
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    return None