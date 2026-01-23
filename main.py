# main.py
import os
import time
import traceback
from typing import List, Tuple, Optional
from utils import get_app_root, sanitize_filename, ensure_dirs
from converter import EPubGenerator

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
            print(">> 如果直接回车，程序将使用文件名作为书名，'Unknown' 作为作者。")
            batch_author_input = input("请输入统一作者名 (可选): ").strip()
            
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
    print("  [0] 不使用嵌入字体 (推荐，文件更小，兼容性更好)")
    for i, f in enumerate(font_files):
        try:
            file_size_mb = os.path.getsize(os.path.join(fonts_dir, f)) / (1024 * 1024)
            print(f"  [{i+1}] {f} ({file_size_mb:.1f} MB)")
        except OSError:
            print(f"  [{i+1}] {f} (Size unknown)")
    
    while True:
        c = input("字体序号: ").strip()
        if c == '0' or c == '':
            return None
        try:
            idx = int(c) - 1
            if 0 <= idx < len(font_files):
                return os.path.join(fonts_dir, font_files[idx])
            print("序号越界。")
        except ValueError:
            print("输入无效。")
    return None

def main():
    app_root = get_app_root()
    input_dir = os.path.join(app_root, 'input')
    output_dir = os.path.join(app_root, 'output')
    fonts_dir = os.path.join(app_root, 'fonts')

    try:
        ensure_dirs(app_root, ['input', 'output', 'fonts'])
    except PermissionError as e:
        print(f"[Fatal] {e}")
        input("按回车退出...")
        return

    print("\n" + "=" * 50)
    print("     TXT 转 EPUB 转换器 (Architect Edition)")
    print("=" * 50)
    print(f"工作目录: {app_root}")

    tasks = select_files(input_dir)
    if not tasks:
        input("按回车键退出...")
        return

    font_path = select_font(fonts_dir)

    print("\n" + "=" * 50)
    print(f"开始处理 {len(tasks)} 个任务...")
    print("=" * 50)
    
    # 初始化生成器
    generator = EPubGenerator(font_path=font_path)
    
    start_time = time.time()
    success_count = 0
    
    for i, (fname, book_title, book_author) in enumerate(tasks):
        print(f"\n>>> 任务 ({i+1}/{len(tasks)})")
        
        txt_full_path = os.path.join(input_dir, fname)
        safe_name = sanitize_filename(book_title)
        epub_full_path = os.path.join(output_dir, f"{safe_name}.epub")
        
        try:
            # 调用重命名后的核心方法 convert
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