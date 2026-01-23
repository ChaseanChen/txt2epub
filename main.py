# main.py
import os
import time
from utils import get_app_root, sanitize_filename, ensure_dirs
from converter import EPubGenerator

def select_files(input_dir):
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
    
    selected_files = [] 
    while True:
        choice = input("\n请选择 (序号 或 A): ").strip().lower()
        if choice == 'a':
            print(">> 已选择全部文件")
            batch_author = input("请输入统一作者名 (回车默认 'Unknown'): ").strip() or "Unknown"
            for f in txt_files:
                title = os.path.splitext(f)[0]
                selected_files.append((f, title, batch_author))
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
                print("序号无效。")
            except ValueError:
                print("输入无效。")

def select_font(fonts_dir):
    """处理字体选择逻辑"""
    font_files = [f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf'))]
    
    if not font_files:
        print("\n[i] fonts 文件夹为空，将使用阅读器默认字体。")
        return None

    print("\n[2] 选择字体:")
    print("  [0] 不使用嵌入字体")
    for i, f in enumerate(font_files):
        print(f"  [{i+1}] {f}")
    
    while True:
        c = input("字体序号: ").strip()
        if c == '0' or c == '': return None
        try:
            idx = int(c) - 1
            if 0 <= idx < len(font_files):
                return os.path.join(fonts_dir, font_files[idx])
        except: pass
    return None

def main():
    # 1. 初始化路径
    app_root = get_app_root()
    input_dir = os.path.join(app_root, 'input')
    output_dir = os.path.join(app_root, 'output')
    fonts_dir = os.path.join(app_root, 'fonts')

    try:
        ensure_dirs(app_root, ['input', 'output', 'fonts'])
    except PermissionError as e:
        print(e)
        input("按回车退出...")
        return

    print("\n" + "=" * 50)
    print("     TXT 转 EPUB 转换器 (Modular Edition)")
    print("=" * 50)
    print(f"核心路径: {app_root}")

    # 2. 选择文件
    tasks = select_files(input_dir)
    if not tasks:
        input("按回车键退出...")
        return

    # 3. 选择字体
    font_path = select_font(fonts_dir)

    # 4. 执行转换
    print("\n" + "=" * 50)
    print(f"开始处理 {len(tasks)} 个任务...")
    print("=" * 50)
    
    generator = EPubGenerator(font_path=font_path)
    start_time = time.time()
    
    for i, (fname, book_title, book_author) in enumerate(tasks):
        print(f"\n>>> 任务 ({i+1}/{len(tasks)})")
        
        txt_full_path = os.path.join(input_dir, fname)
        safe_name = sanitize_filename(book_title)
        epub_full_path = os.path.join(output_dir, f"{safe_name}.epub")
        
        try:
            generator.run(txt_full_path, epub_full_path, book_title, book_author)
        except KeyboardInterrupt:
            print("\n任务被用户中断。")
            break
        except Exception as e:
            print(f"发生未捕获的错误: {e}")

    duration = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"全部完成！耗时: {duration:.2f} 秒")
    print(f"输出路径: {output_dir}")
    input("按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass