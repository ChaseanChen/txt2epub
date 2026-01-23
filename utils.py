# utils.py
import os
import sys
import re
import logging
from typing import Optional

# [修复] 显式处理 chardet 的定义，防止静态分析报错 "possibly unbound"
try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False
    chardet = None  # 关键修复：确保变量名存在

def get_app_root():
    """获取应用程序根目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def sanitize_filename(filename):
    """清理文件名，移除非法字符"""
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
    智能检测文件编码
    """
    # 常用编码列表（作为 fallback）
    common_encodings = ['utf-8', 'gb18030', 'gbk', 'big5', 'utf-16']
    
    # 1. 使用 chardet 进行统计学分析
    if HAS_CHARDET and chardet is not None:
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(50000) # 读取前 50KB 足够判断
                result = chardet.detect(raw_data)
                detected_enc = result['encoding']
                confidence = result['confidence']
                
                if detected_enc and confidence > 0.8:
                    logging.info(f"Chardet 检测编码: {detected_enc} (置信度: {confidence:.2f})")
                    if detected_enc.lower() in ['gb2312', 'gbk']:
                        return 'gb18030'
                    return detected_enc
        except Exception as e:
            logging.warning(f"Chardet 检测出错: {e}，将使用回退策略")

    # 2. 暴力尝试 (Fallback)
    logging.info("使用列表尝试解码...")
    for enc in common_encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read(4096)
            logging.info(f"编码探测成功: {enc}")
            return enc
        except UnicodeDecodeError:
            continue
        except Exception:
            break
            
    return None