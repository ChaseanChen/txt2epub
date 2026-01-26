# main.py
import os
import re
import traceback
from typing import List, Tuple, Optional
from utils import get_app_root, sanitize_filename, ensure_dirs
from converter import EPubBuilder

DEFAULT_CSS_TEMPLATE = """/* EPUB 样式表 v2.1 */
body { line-height: 1.8; text-align: justify; margin: 0; padding: 0 10px; background-color: #fcfcfc; font-family: sans-serif; }
h1 { font-weight: bold; text-align: center; margin: 2em 0 1.5em 0; font-size: 1.6em; line-height: 1.3; page-break-before: always; color: #333; }
p { text-indent: 2em; margin: 0 0 0.8em 0; font-size: 1em; word-wrap: break-word; }
.scene-break { margin: 2em auto; text-align: center; color: #999; font-weight: bold; page-break-inside: avoid; }
img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
"""

def init_assets(assets_dir: str):
    css_path = os.path.join(assets_dir, 'style.css')
    if not os.path.exists(css_path):
        try:
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(DEFAULT_CSS_TEMPLATE)
        except OSError as e:
            print(f"[Warning] 无法初始化默认 CSS: {e}")

def parse_filename_metadata(filename: str) -> Tuple[str, str]:
    """
    从文件名猜测书名和作者
    支持格式: 
    - <<书名>> 作者.txt
    - 书名 - 作者.txt
    - 书名.txt
    """
    base = os.path.splitext(filename)[0]
    
    # 模式 1: <<书名>> 作者
    match = re.match(r'《(.*?)》\s*(.*)', base)
    if match:
        return match.group(1).strip(), match.group(2).strip() or "Unknown"

    # 模式 2: 书名 - 作者 (或 作者 - 书名，难以区分，默认前者)
    if ' - ' in base:
        parts = base.split(' - ')
        return parts[0].strip(), parts[1].strip()
    
    # 模式 3: 仅书名
    return base, "Unknown"

def parse_selection(choice: str, total_files: int) -> List[int]:
    choice = choice.strip().lower()
    if not choice:
        return []
    if choice == 'a':
        return list(range(total_files))
    
    selected_indices = set()
    parts = choice.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part: # 支持范围 1-3
            try:
                start, end = map(int, part.split('-'))
                # 转换为 0-based 索引，并限制范围
                for i in range(start - 1, end):
                    if 0 <= i < total_files:
                        selected_indices.add(i)
            except ValueError:
                pass
        else:
            try:
                idx = int(part) - 1
                if 0 <= idx < total_files:
                    selected_indices.add(idx)
            except ValueError:
                pass
    return sorted(list(selected_indices))

def select_files(input_dir: str) -> Optional[List[Tuple[str, str, str]]]:
    """支持多选的 CLI 文件选择器"""
    if not os.path.exists(input_dir):
        print(f"[!] 目录不存在: {input_dir}")
        return None
        
    txt_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.txt')]
    if not txt_files:
        print(f"[!] '{input_dir}' 为空。")
        return None

    print(f"\n[1] 发现 {len(txt_files)} 个文件:")
    print("  [A] 全部转换")
    for i, f in enumerate(txt_files):
        print(f"  [{i+1}] {f}")
    
    print("\n提示: 输入 'A' 全选，序号 '1'，多选 '1,3'，范围 '1-5'")
    choice = input("请选择: ")
    
    indices = parse_selection(choice, len(txt_files))
    
    if not indices:
        print("未选择有效文件。")
        return None

    tasks = []
    is_batch = len(indices) > 1
    
    if is_batch:
        print(f"已选择 {len(indices)} 个文件。")
        print("模式选择:")
        print("  [1] 自动识别文件名 (书名 - 作者.txt)")
        print("  [2] 统一指定作者")
        mode = input("请选择 (默认1): ").strip()
        
        batch_auth = None
        if mode == '2':
            batch_auth = input("请输入统一作者名 (Unknown): ").strip() or "Unknown"

        for idx in indices:
            fname = txt_files[idx]
            if batch_auth:
                # 统一作者模式，书名取文件名
                tasks.append((fname, os.path.splitext(fname)[0], batch_auth))
            else:
                # 自动识别模式
                title, author = parse_filename_metadata(fname)
                tasks.append((fname, title, author))
    else:
        # 单文件精细设置
        idx = indices[0]
        fname = txt_files[idx]
        auto_title, auto_auth = parse_filename_metadata(fname)
        
        title = input(f"书名 ({auto_title}): ").strip() or auto_title
        auth = input(f"作者 ({auto_auth}): ").strip() or auto_auth
        tasks.append((fname, title, auth))
        
    return tasks

def select_font(fonts_dir: str) -> Optional[str]:
    if not os.path.exists(fonts_dir):
        return None
    font_files = [f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf'))]
    if not font_files:
        return None

    print("\n[2] 选择字体:")
    print("  [0] 不嵌入 (使用阅读器默认)")
    for i, f in enumerate(font_files):
        print(f"  [{i+1}] {f}")
    
    choice = input("序号: ").strip()
    try:
        if choice == '0' or not choice:
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(font_files):
            return os.path.join(fonts_dir, font_files[idx])
    except ValueError:
        pass
    return None

def main():
    app_root = get_app_root()
    dirs = {
        'input': os.path.join(app_root, 'input'),
        'output': os.path.join(app_root, 'output'),
        'fonts': os.path.join(app_root, 'fonts'),
        'assets': os.path.join(app_root, 'assets')
    }

    try:
        ensure_dirs(app_root, dirs.keys())
        init_assets(dirs['assets'])
    except PermissionError as e:
        print(f"[Fatal] 权限错误: {e}")
        return

    print("TXT 转 EPUB 工具 (Architecture v3.1)")
    
    tasks = select_files(dirs['input'])
    if not tasks:
        return

    font_path = select_font(dirs['fonts'])
    builder = EPubBuilder(font_path=font_path, assets_dir=dirs['assets'])

    print(f"\n开始处理 {len(tasks)} 个任务...")
    
    success_cnt = 0
    for i, (fname, title, auth) in enumerate(tasks):
        print(f"--- 任务 {i+1}/{len(tasks)}: 《{title}》 ---")
        txt_path = os.path.join(dirs['input'], fname)
        epub_path = os.path.join(dirs['output'], f"{sanitize_filename(title)}.epub")
        
        try:
            builder.build(txt_path, epub_path, title, auth)
            success_cnt += 1
        except KeyboardInterrupt:
            print("\n[!] 用户中断")
            break
        except Exception:
            print(f"  [Fail] 处理失败: {fname}")
            traceback.print_exc()

    print(f"\n全部完成: 成功 {success_cnt} / 总计 {len(tasks)}")
    if not os.getenv("NO_PAUSE"): # 方便脚本调用
        input("按回车退出...")

if __name__ == "__main__":
    main()