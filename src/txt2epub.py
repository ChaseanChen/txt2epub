# txt2epub_v2.py

import os
import re
import time
import uuid
import sys
from ebooklib import epub

class EPubGenerator:
    def __init__(self, font_path=None):
        self.font_path = font_path
        # 预编译正则，提高性能
        # 匹配逻辑：行首 + 第 + 中文数字/数字 + 章/节/回 + 任意文字
        self.chapter_pattern = re.compile(r'(^\s*第.{1,12}[章节回卷].*?$)', re.MULTILINE)

    def _generate_stable_id(self, title, author):
        """
        生成基于书名和作者的确定性UUID。
        保证同一本书重复生成时ID一致，避免阅读器丢失进度。
        """
        unique_string = f"{title}-{author}"
        # 使用 DNS 命名空间作为种子
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

    def _get_default_css(self, font_file_name=None):
        """
        生成 CSS 样式。
        """
        font_face = ""
        font_family = "sans-serif"
        
        if font_file_name:
            font_face = f'@font-face {{ font-family: "CustomFont"; src: url("fonts/{font_file_name}"); }}'
            font_family = '"CustomFont", sans-serif'
            
        return f'''
            {font_face}
            body {{ font-family: {font_family}; line-height: 1.8; text-align: justify; margin: 0 5px; }}
            p {{ text-indent: 2em; margin: 0.8em 0; }}
            h1 {{ font-weight: bold; text-align: center; margin: 2em 0 1em 0; font-size: 1.5em; }}
            div.cover {{ text-align: center; }}
            img {{ max-width: 100%; height: auto; }}
        '''

    def _try_get_cover(self, txt_path):
        """
        尝试寻找封面图片。
        策略：
        1. 优先寻找与 TXT 同名的图片 (e.g. book.txt -> book.jpg)
        2. 其次寻找目录下的 cover.jpg / cover.png
        """
        base_dir = os.path.dirname(txt_path)
        file_basename = os.path.splitext(os.path.basename(txt_path))[0]
        
        # 支持的图片扩展名
        valid_exts = ['.jpg', '.jpeg', '.png']
        
        # 1. 检查同名图片
        for ext in valid_exts:
            img_path = os.path.join(base_dir, file_basename + ext)
            if os.path.exists(img_path):
                return img_path, ext
        
        # 2. 检查通用封面
        for ext in valid_exts:
            img_path = os.path.join(base_dir, 'cover' + ext)
            if os.path.exists(img_path):
                return img_path, ext
                
        return None, None

    def _parse_chapters(self, content):
        """
        解析文本内容为章节列表。
        返回: List[Tuple(title, body)]
        """
        matches = list(self.chapter_pattern.finditer(content))
        chapters = []

        if not matches:
            # 如果没有匹配到任何章节，全文作为一章
            return [("正文", content)]

        # 处理序言（第一个匹配之前的文本）
        preface_end = matches[0].start()
        if preface_end > 0:
            preface_content = content[:preface_end].strip()
            if preface_content:
                chapters.append(("序言", preface_content))

        # 处理各个章节
        count = len(matches)
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start_idx = match.end()
            # 结束位置是下一个匹配的开始，或者是文本末尾
            end_idx = matches[i+1].start() if i + 1 < count else len(content)
            
            body = content[start_idx:end_idx]
            chapters.append((title, body))
            
        return chapters

    def run(self, txt_path, epub_path, title, author):
        print(f"\n正在处理: [{os.path.basename(txt_path)}]")
        
        # 1. 初始化书籍
        book = epub.EpubBook()
        book.set_identifier(self._generate_stable_id(title, author))
        book.set_title(title)
        book.set_language('zh-cn')
        book.add_author(author)

        # 2. 处理封面 (新增功能)
        cover_path, cover_ext = self._try_get_cover(txt_path)
        if cover_path:
            try:
                with open(cover_path, 'rb') as f:
                    cover_content = f.read()
                # 设置封面，ebooklib 会自动创建封面页 html
                book.set_cover(f"cover{cover_ext}", cover_content)
                print(f"  [+] 已添加封面: {os.path.basename(cover_path)}")
            except Exception as e:
                print(f"  [!] 封面读取失败: {e}")
        else:
            print("  [-] 未检测到封面图片，跳过。")

        # 3. 嵌入字体与样式
        css_item = None
        font_filename = None
        
        if self.font_path and os.path.exists(self.font_path):
            font_filename = os.path.basename(self.font_path)
            try:
                with open(self.font_path, 'rb') as f:
                    book.add_item(epub.EpubItem(
                        uid="custom_font",
                        file_name=f"fonts/{font_filename}",
                        media_type="application/x-font-ttf",
                        content=f.read()
                    ))
                print(f"  [+] 已嵌入字体: {font_filename}")
            except Exception as e:
                print(f"  [!] 字体嵌入失败: {e}")
                font_filename = None # 回退

        css_content = self._get_default_css(font_filename)
        css_item = epub.EpubItem(uid="style_css", file_name="style.css", media_type="text/css", content=css_content)
        book.add_item(css_item)

        # 4. 读取文本 (自动处理编码)
        content = ""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                print("  [i] UTF-8 解码失败，尝试 GB18030...")
                with open(txt_path, 'r', encoding='gb18030') as f:
                    content = f.read()
            except Exception:
                print(f"  [Error] 无法识别文件编码，跳过。")
                return

        # 5. 生成章节
        parsed_chapters = self._parse_chapters(content)
        print(f"  [i] 识别到 {len(parsed_chapters)} 个章节")
        
        epub_chapters = []
        for i, (chap_title, chap_body) in enumerate(parsed_chapters):
            # 构建 HTML 文件名
            file_name = f'chap_{i+1}.xhtml'
            c = epub.EpubHtml(title=chap_title, file_name=file_name, lang='zh-cn')
            c.add_item(css_item)
            
            # 优化段落处理
            lines = [f"<p>{line.strip()}</p>" for line in chap_body.splitlines() if line.strip()]
            c.content = f'<h1>{chap_title}</h1>' + "".join(lines)
            
            book.add_item(c)
            epub_chapters.append(c)

        # 6. 构建目录和骨架
        book.toc = epub_chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # 确保封面在 spine 中（如果有的话，set_cover 会自动处理，但在 spine 中明确导航是个好习惯）
        book.spine = ['nav'] + epub_chapters

        # 7. 保存文件
        output_dir = os.path.dirname(epub_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try:
            epub.write_epub(epub_path, book, {})
            print(f"  [Success] 生成完毕: {os.path.basename(epub_path)}")
        except Exception as e:
            print(f"  [Error] 保存 EPUB 失败: {e}")


# --- 交互式功能函数 ---
def interactive_runner():
    # 1. 健壮的路径设置
    # 获取脚本所在的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 定义目录结构 (相对于脚本位置)
    input_dir = os.path.join(script_dir, 'input')
    output_dir = os.path.join(script_dir, 'output')
    fonts_dir = os.path.join(script_dir, 'fonts')

    for d in [input_dir, output_dir, fonts_dir]:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"创建目录: {d}")

    print("\n" + "=" * 40)
    print("     TXT 转 EPUB 转换器 (Pro Ver.)")
    print("=" * 40)
    print(f"工作目录: {script_dir}")

    # 2. 扫描 TXT 文件
    txt_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.txt')]
    
    if not txt_files:
        print(f"\n[!] input 文件夹 ({input_dir}) 为空。")
        print("请将 .txt 小说放入该文件夹后重试。")
        input("按回车键退出...")
        return

    # 打印列表
    print(f"\n[1] 发现 {len(txt_files)} 个文件:")
    print("-" * 30)
    print(f"  [A] 全部转换 (Batch Convert)")
    for i, f in enumerate(txt_files):
        print(f"  [{i+1}] {f}")
    
    # 3. 用户选择逻辑
    selected_files = [] 
    
    while True:
        choice = input("\n请选择 (序号 或 A): ").strip().lower()
        
        if choice == 'a':
            print(">> 已选择全部文件")
            batch_author = input("请输入统一作者名 (回车默认 'Unknown'): ").strip() or "Unknown"
            for f in txt_files:
                title = os.path.splitext(f)[0]
                selected_files.append((f, title, batch_author))
            break
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
                    
                    selected_files.append((f, final_title, final_author))
                    break
                else:
                    print("序号无效。")
            except ValueError:
                print("输入无效。")

    # 4. 选择字体
    font_files = [f for f in os.listdir(fonts_dir) if f.lower().endswith(('.ttf', '.otf'))]
    selected_font_path = None
    
    if font_files:
        print("\n[2] 选择字体:")
        print("  [0] 不使用嵌入字体")
        for i, f in enumerate(font_files):
            print(f"  [{i+1}] {f}")
        
        while True:
            c = input("字体序号: ").strip()
            if c == '0' or c == '':
                break
            try:
                idx = int(c) - 1
                if 0 <= idx < len(font_files):
                    selected_font_path = os.path.join(fonts_dir, font_files[idx])
                    break
            except:
                pass
    else:
        print("\n[i] fonts 文件夹为空，将使用阅读器默认字体。")

    # 5. 执行转换
    total_tasks = len(selected_files)
    print("\n" + "=" * 40)
    print(f"开始处理 {total_tasks} 个任务...")
    print("=" * 40)
    
    # 实例化生成器
    generator = EPubGenerator(font_path=selected_font_path)
    
    start_time = time.time()
    
    for i, (fname, book_title, book_author) in enumerate(selected_files):
        print(f"\n>>> 任务 ({i+1}/{total_tasks})")
        
        txt_full_path = os.path.join(input_dir, fname)
        epub_full_path = os.path.join(output_dir, f"{book_title}.epub")
        
        try:
            generator.run(txt_full_path, epub_full_path, book_title, book_author)
        except KeyboardInterrupt:
            print("\n任务被用户中断。")
            break
        except Exception as e:
            print(f"发生未捕获的错误: {e}")

    duration = time.time() - start_time
    print("\n" + "=" * 40)
    print(f"全部完成！耗时: {duration:.2f} 秒")
    print(f"输出路径: {output_dir}")
    input("按回车键退出...")

if __name__ == "__main__":
    try:
        interactive_runner()
    except KeyboardInterrupt:
        pass