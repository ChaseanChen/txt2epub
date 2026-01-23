# main.py
import os
import traceback
from typing import List, Tuple, Optional
from utils import get_app_root, sanitize_filename, ensure_dirs
# 注意：这里导入的是我们改名后的 EPubBuilder
from converter import EPubBuilder 

# 改进后的 CSS：处理了场景分隔，优化了段落间距
DEFAULT_CSS_TEMPLATE = """/* EPUB 样式表 v2 */
body { 
    line-height: 1.8; 
    text-align: justify; 
    margin: 0; 
    padding: 0 10px;
    background-color: #fcfcfc; 
    font-family: sans-serif;
}

/* 标题样式 */
h1 { 
    font-weight: bold; 
    text-align: center; 
    margin: 2em 0 1.5em 0; 
    font-size: 1.6em; 
    line-height: 1.3;
    page-break-before: always; 
    color: #333; 
}

/* 段落核心样式：首行缩进 2em，替代源文件空格 */
p { 
    text-indent: 2em; 
    margin: 0 0 0.8em 0; /* 仅保留下边距，防止上下间距过大 */
    font-size: 1em; 
    word-wrap: break-word;
}

/* 场景分隔符：处理原书中的大段空行 */
.scene-break {
    margin: 2em auto;
    text-align: center;
    color: #999;
    font-weight: bold;
    page-break-inside: avoid;
}

/* 图片处理 */
img { 
    max-width: 100%; 
    height: auto; 
    display: block; 
    margin: 1em auto; 
}
"""

def init_assets(assets_dir: str):
    css_path = os.path.join(assets_dir, 'style.css')
    # 为了应用新的 CSS，如果文件存在但内容是旧的，可能需要逻辑去更新
    # 简单起见，这里假设用户如果想重置样式，会删除 assets 下的 style.css
    # 或者如果文件不存在则写入
    if not os.path.exists(css_path):
        try:
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(DEFAULT_CSS_TEMPLATE)
        except Exception:
            pass

def select_files(input_dir: str) -> Optional[List[Tuple[str, str, str]]]:
    """简单的 CLI 文件选择器"""
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
    
    choice = input("\n请选择 (序号 或 A): ").strip().lower()
    if choice == 'a':
        auth = input("统一作者 (默认 Unknown): ").strip() or "Unknown"
        return [(f, os.path.splitext(f)[0], auth) for f in txt_files]
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(txt_files):
            f = txt_files[idx]
            title = input(f"书名 ({os.path.splitext(f)[0]}): ").strip() or os.path.splitext(f)[0]
            auth = input("作者 (Unknown): ").strip() or "Unknown"
            return [(f, title, auth)]
    except ValueError:
        pass
    print("输入无效。")
    return None

def select_font(fonts_dir: str) -> Optional[str]:
    """简单的 CLI 字体选择器"""
    if not os.path.exists(fonts_dir):
        return None
    font_files = [f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf'))]
    if not font_files:
        return None

    print("\n[2] 选择字体:")
    print("  [0] 不嵌入")
    for i, f in enumerate(font_files):
        print(f"  [{i+1}] {f}")
    
    choice = input("序号: ").strip()
    try:
        if choice == '0' or not choice:
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(font_files):
            return os.path.join(fonts_dir, font_files[idx])
    except Exception:
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

    print("TXT 转 EPUB 工具 (Refactored v2.1 - Smart Paragraph)")
    
    tasks = select_files(dirs['input'])
    if not tasks:
        return

    font_path = select_font(dirs['fonts'])

    # 初始化 Builder
    builder = EPubBuilder(font_path=font_path, assets_dir=dirs['assets'])

    print(f"\n开始处理 {len(tasks)} 个任务...")
    
    success_cnt = 0
    for fname, title, auth in tasks:
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

    print(f"\n完成: {success_cnt}/{len(tasks)}")
    input("按回车退出...")

if __name__ == "__main__":
    main()