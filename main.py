# main.py
import os
import time
import traceback
from typing import List, Tuple, Optional
from utils import get_app_root, sanitize_filename, ensure_dirs
from converter import EPubGenerator

# 默认 CSS 模板内容，当 style.css 不存在时写入
DEFAULT_CSS_TEMPLATE = """/* EPUB 样式表 (可自由修改) */

/* 全局设置 */
body {
    line-height: 1.8;
    text-align: justify;
    margin: 0 5px;
    background-color: #fcfcfc;
    /* font-family 会由程序根据设置动态插入，这里不需要写 */
}

/* 段落样式 */
p {
    text-indent: 2em;
    margin: 0.8em 0;
    font-size: 1em;
}

/* 标题样式 */
h1 {
    font-weight: bold;
    text-align: center;
    margin: 2em 0 1em 0;
    font-size: 1.6em;
    page-break-before: always;
    color: #333;
}

/* 图片样式 */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}

/* 封面容器 */
div.cover {
    text-align: center;
    height: 100%;
}
"""

def init_assets(assets_dir: str):
    """初始化资源目录，如果缺少 style.css 则创建默认的"""
    css_path = os.path.join(assets_dir, 'style.css')
    if not os.path.exists(css_path):
        try:
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(DEFAULT_CSS_TEMPLATE)
            print(f"[Init] 已生成默认样式表: {css_path}")
        except Exception as e:
            print(f"[Warning] 无法创建默认样式表: {e}")

def select_files(input_dir: str) -> Optional[List[Tuple[str, str, str]]]:
    """处理文件选择逻辑"""
    txt_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.txt')]
    
    if not txt_files:
        print(f"\n[!] 'input' 文件夹为空。\n位置: {input_dir}")
        print("请将 .txt 小说放入该文件夹后重试。")
        return None

    print(f"\n[1] 发现 {len(txt_files)} 个文件:")
    print("-" * 30)
    print("  [A] 全部转换 (Batch Convert)")
    for i, f in enumerate(txt_files):
        print(f"  [{i+1}] {f}")
    
    while True:
        choice = input("\n请选择 (序号 或 A): ").strip().lower()
        
        if choice == 'a':
            print(">> 已选择全部文件")
            batch_author_input = input("请输入统一作者名 (默认为 'Unknown'): ").strip()
            
            selected_files = []
            for f in txt_files:
                title = os.path.splitext(f)[0]
                author = batch_author_input if batch_author_input else "Unknown"
                selected_files.append((f, title, author))
            return selected_files
        
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(txt_files):
                    f = txt_files[idx]
                    default_title = os.path.splitext(f)[0]
                    print(f">> 已选择: {f}")
                    
                    in_title = input(f"书名 (默认 '{default_title}'): ").strip()
                    final_title = in_title if in_title else default_title
                    
                    in_author = input("作者 (默认 'Unknown'): ").strip()
                    final_author = in_author if in_author else "Unknown"
                    
                    return [(f, final_title, final_author)]
                print("序号无效，请重新输入。")
            except ValueError:
                print("输入无效，请输入数字或 A。")

def select_font(fonts_dir: str) -> Optional[str]:
    """处理字体选择逻辑"""
    font_files = [f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf'))]
    
    if not font_files:
        print("\n[i] fonts 文件夹为空，将使用阅读器默认字体。")
        return None

    print("\n[2] 选择字体:")
    print("  [0] 不使用嵌入字体 (推荐)")
    for i, f in enumerate(font_files):
        try:
            size = os.path.getsize(os.path.join(fonts_dir, f)) / (1024 * 1024)
            print(f"  [{i+1}] {f} ({size:.1f} MB)")
        except Exception:
            print(f"  [{i+1}] {f}")
    
    while True:
        c = input("字体序号: ").strip()
        if c == '0' or c == '':
            return None
        try:
            idx = int(c) - 1
            if 0 <= idx < len(font_files):
                return os.path.join(fonts_dir, font_files[idx])
        except ValueError:
            pass
        print("输入无效。")

def main():
    app_root = get_app_root()
    input_dir = os.path.join(app_root, 'input')
    output_dir = os.path.join(app_root, 'output')
    fonts_dir = os.path.join(app_root, 'fonts')
    assets_dir = os.path.join(app_root, 'assets')  # 新增

    try:
        ensure_dirs(app_root, ['input', 'output', 'fonts', 'assets'])
        init_assets(assets_dir)  # 初始化 CSS
    except PermissionError as e:
        print(f"[Fatal] {e}")
        input("按回车退出...")
        return

    print("\n" + "=" * 50)
    print("     TXT 转 EPUB 转换器 (Architect Edition v2.0)")
    print("=" * 50)
    print(f"工作目录: {app_root}")
    print("样式文件: assets/style.css (可编辑)")

    tasks = select_files(input_dir)
    if not tasks:
        input("按回车键退出...")
        return

    font_path = select_font(fonts_dir)

    print("\n" + "=" * 50)
    print(f"开始处理 {len(tasks)} 个任务...")
    print("=" * 50)
    
    # 注入 assets_dir
    generator = EPubGenerator(font_path=font_path, assets_dir=assets_dir)
    
    start_time = time.time()
    success_count = 0
    
    for i, (fname, book_title, book_author) in enumerate(tasks):
        print(f"\n>>> 任务 ({i+1}/{len(tasks)})")
        
        txt_full_path = os.path.join(input_dir, fname)
        safe_name = sanitize_filename(book_title)
        epub_full_path = os.path.join(output_dir, f"{safe_name}.epub")
        
        try:
            generator.convert(txt_full_path, epub_full_path, book_title, book_author)
            success_count += 1
        except KeyboardInterrupt:
            print("\n[!] 任务被用户中断。")
            break
        except Exception as e:
            print(f"  [Fail] 处理文件 '{fname}' 时发生错误: {e}")
            traceback.print_exc()

    duration = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"处理完成！成功: {success_count}/{len(tasks)} | 耗时: {duration:.2f} 秒")
    print(f"输出路径: {output_dir}")
    input("按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass