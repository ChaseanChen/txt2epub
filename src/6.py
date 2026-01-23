# txt2epub.py

import os
import re
import time
from ebooklib import epub

class Kernel:
    def __init__(self):
        pass
    
    def txt_to_epub(self, txt_path, epub_path, title, author, font_path=None):
        # --- 核心转换逻辑 (保持稳定) ---
        file_basename = os.path.basename(txt_path)
        print(f"\n正在处理: [{file_basename}]")
        
        if not os.path.exists(txt_path):
            print(f"错误: 找不到文件 '{txt_path}'")
            return

        output_dir = os.path.dirname(epub_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        book = epub.EpubBook()
        book.set_identifier(f'id_{hash(title)}') # 简单的唯一ID生成
        book.set_title(title)
        book.set_language('zh-cn')
        book.add_author(author)
        
        # --- 字体处理 ---
        css_item = None
        if font_path and os.path.exists(font_path):
            font_name = os.path.basename(font_path)
            font_dest = "fonts/" + font_name
            try:
                with open(font_path, 'rb') as f:
                    font_content = f.read()
                
                book.add_item(epub.EpubItem(
                    uid="custom_font", file_name=font_dest, 
                    media_type="application/x-font-ttf", content=font_content
                ))

                css_content = f'''
                    @font-face {{ font-family: "MyFont"; src: url("{font_dest}"); }}
                    body, p, div {{ font-family: "MyFont", sans-serif; line-height: 1.8; text-align: justify; }}
                    p {{ text-indent: 2em; margin: 0.8em 0; }}
                    h1 {{ font-family: "MyFont", sans-serif; font-weight: bold; text-align: center; margin: 2em 0 1em 0; }}
                '''
                css_item = epub.EpubItem(uid="style_css", file_name="style.css", media_type="text/css", content=css_content)
                book.add_item(css_item)
            except Exception as e:
                print(f"字体嵌入失败: {e}，将使用默认样式。")
        
        # --- 读取内容 ---
        content = ""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                # 这一步稍微耗时，不打印太多干扰信息
                with open(txt_path, 'r', encoding='gb18030') as f:
                    content = f.read()
            except Exception :
                print(f"'{file_basename}' 编码识别失败，跳过。")
                return
            
        # --- 章节处理 ---
        pattern = re.compile(r'(^\s*第.{1,12}[章节回卷].*?$)', re.MULTILINE)
        parts = pattern.split(content)
        
        if len(parts) < 2:
            parts = ["", "正文", content] 
        
        chapters = []
        
        def create_chapter(t, c_text, fname):
            c = epub.EpubHtml(title=t, file_name=fname, lang='zh-cn')
            lines = [line.strip() for line in c_text.split('\n') if line.strip()]
            c.content = f'<h1>{t}</h1>' + ''.join([f'<p>{line}</p>' for line in lines])
            if css_item:
                c.add_item(css_item)
            book.add_item(c)
            chapters.append(c)

        if parts[0].strip():
            create_chapter("序言", parts[0], "intro.xhtml")
        
        titles, contents = parts[1::2], parts[2::2]
        
        # 简单进度条
        total_chapters = len(titles)
        print(f"识别到 {total_chapters} 章，打包中...")
        
        for i, (t, c) in enumerate(zip(titles, contents)):
            create_chapter(t.strip(), c, f'chap_{i+1}.xhtml')

        book.toc = (chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + chapters

        try:
            epub.write_epub(epub_path, book, {})
            print(f"成功: {os.path.basename(epub_path)}")
        except Exception as e:
            print(f"保存失败: {e}")


# --- 交互式功能函数 ---
def interactive_runner():
    # 1. 路径设置
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    input_dir = os.path.join(project_root, 'input')
    output_dir = os.path.join(project_root, 'output')
    fonts_dir = os.path.join(project_root, 'fonts')

    for d in [input_dir, output_dir, fonts_dir]:
        if not os.path.exists(d):
            os.makedirs(d)

    print("\n" + "-" * 32)
    print("    ---TXT 转 EPUB 转换器---  ")
    print("-" * 32)

    # 2. 扫描 TXT 文件
    print(f"\n[1/4] 扫描 {input_dir} ...")
    txt_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.txt')]
    
    if not txt_files:
        print("[Error] input 文件夹里没有找到 .txt 文件！")
        return

    # 打印列表
    print(f"[A] 全部转换 (Batch Convert All) - 共 {len(txt_files)} 个文件")
    print("  " + "-" * 30)
    for i, f in enumerate(txt_files):
        print(f"  [{i+1}] {f}")
    
    # 3. 用户选择逻辑
    selected_files = [] # 存储 (文件名, 书名, 作者) 的列表
    
    while True:
        choice = input("\n请输入序号 或 'A': ").strip().lower()
        
        if choice == 'a':
            # --- 批量模式 ---
            print("已选择全部文件！")
            batch_author = input("请输入统一作者名 (回车默认 'Unknown'): ").strip()
            if not batch_author:
                batch_author = "Unknown"
            
            for f in txt_files:
                # 自动提取文件名作为书名 (去除 .txt)
                auto_title = os.path.splitext(f)[0]
                selected_files.append((f, auto_title, batch_author))
            break
            
        else:
            # --- 单选模式 ---
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(txt_files):
                    f = txt_files[idx]
                    default_title = os.path.splitext(f)[0]
                    
                    print(f"已选择: {f}")
                    in_title = input(f"书名 (回车默认 '{default_title}'): ").strip()
                    final_title = in_title if in_title else default_title
                    
                    in_author = input("作者 (回车默认 'Unknown'): ").strip()
                    final_author = in_author if in_author else "Unknown"
                    
                    selected_files.append((f, final_title, final_author))
                    break
                print("序号无效。")
            except ValueError:
                print("输入无效，请输入数字或 'A'。")

    # 4. 选择字体 (通用)
    print("\n[3/4] 选择字体 (应用于所有任务)...")
    font_files = [f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf'))]
    selected_font_path = None
    
    if font_files:
        print("  [0] 不使用嵌入字体")
        for i, f in enumerate(font_files):
            print(f"  [{i+1}] {f}")
        
        while True:
            c = input("\n字体序号: ").strip()
            if c == '0':
                break
            try:
                idx = int(c) - 1
                if 0 <= idx < len(font_files):
                    selected_font_path = os.path.join(fonts_dir, font_files[idx])
                    break
            except Exception:
                pass
    else:
        print("无可用字体文件。")

    # 5. 执行队列
    total_tasks = len(selected_files)
    print("\n" + "=" * 40)
    print(f"准备就绪，共 {total_tasks} 个任务")
    print("=" * 40)
    
    # 初始化核心
    app = Kernel()
    
    start_time = time.time()
    
    for i, (fname, book_title, book_author) in enumerate(selected_files):
        print(f"\n执行任务 ({i+1}/{total_tasks})...")
        
        txt_full = os.path.join(input_dir, fname)
        epub_full = os.path.join(output_dir, f"{book_title}.epub")
        
        app.txt_to_epub(txt_full, epub_full, book_title, book_author, selected_font_path)

    end_time = time.time()
    duration = end_time - start_time
    print("\n" + "=" * 40)
    print(f"全部完成！耗时: {duration:.2f} 秒")
    input("按回车键退出...")

if __name__ == "__main__":
    try:
        interactive_runner()
    except KeyboardInterrupt:
        print("\n\n程序已强制停止。")