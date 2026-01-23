# txt2epub.py

import os
import re
from ebooklib import epub

class Kernel:
    def __init__(self):
        pass
    
    def txt_to_epub(self, txt_path, epub_path, title, author, font_path=None):
        print(f"the input files {txt_path}")
        print(f"the output files {epub_path}")
        if font_path:
            print(f"the font path {font_path}")
            
        if not os.path.exists(txt_path):
            print(f"Error: Input file '{txt_path}' not found.")
            return
        # Ensure output directory exists
        output_dir = os.path.dirname(epub_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        print(f"Starting to read and convert '{title}'...")
        
        book = epub.EpubBook()
        book.set_identifier('id_shu_shi_zui_qiang')
        book.set_title(title)
        book.set_language('zh-cn')
        book.add_author(author)
        print(f"Successfully converted '{title}' to EPUB at '{epub_path}'.")
        
        css_item = None
        if font_path and os.path.exists(font_path):
            print("Embedding font...")
            font_filename = "fonts/" + os.path.basename(font_path)
            with open(font_path, 'rb') as f:
                font_content = f.read()
            font_item = epub.EpubItem(
                uid="custom_font",
                file_name=font_filename,
                media_type="application/x-font-ttf",
                content=font_content
            )
            book.add_item(font_item)
            css_content = f'''
                @font-face {{
                    font-family: "MyFont";
                    src: url("{font_filename}");
                }}
                body, p, div {{
                    font-family: "MyFont", "PingFang SC", "Microsoft YaHei", sans-serif;
                    line-height: 1.6;
                    text-align: justify;
                }}
            '''
            css_item = epub.EpubItem(
                uid="style_nav",
                file_name="styles/style.css",
                media_type="text/css",
                content=css_content
            )
            book.add_item(css_item)
            print("Font embedded successfully.")
        else:
            if font_path:
                print(f"Warning: Font file '{font_path}' not found. Proceeding without embedding font.")
                
        content = ""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                print("UTF-8 decoding failed, trying GBK...")
                with open(txt_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except UnicodeDecodeError:
                print("Error: Failed to decode the text file with both UTF-8 and GBK encodings.")
                return
            
        print("analyzing content...")
        pattern = re.compile(r'^(第.{1,9}[章节回].*?)$', re.MULTILINE)
        parts = pattern.split(content)
        
        if len(parts) < 2:
            print("Warning: No chapters found using the specified pattern. The entire text will be treated as a single chapter.")
            return
        
        chapters = []
        
        def create_chapter(title, content_text, file_name):
            c = epub.EpubHtml(title=title, file_name=file_name, lang='zh-cn')
            
            # 处理段落
            lines = [line.strip() for line in content_text.split('\n') if line.strip()]
            body_html = ''.join([f'<p>{line}</p>' for line in lines])
            
            c.content = f'<h1>{title}</h1>{body_html}'
            
            # 关联 CSS
            if css_item:
                c.add_item(css_item)
                
            book.add_item(c)
            chapters.append(c)

        # 处理序章
        if parts[0].strip():
            create_chapter("序言", parts[0], "intro.xhtml")

        # 处理正文
        chapter_titles = parts[1::2]
        chapter_contents = parts[2::2]
        
        print(f"✅ 识别到 {len(chapter_titles)} 个章节，正在打包...")

        for i, (chap_title, chap_content) in enumerate(zip(chapter_titles, chapter_contents)):
            create_chapter(chap_title.strip(), chap_content, f'chap_{i+1}.xhtml')

        # 4. 生成目录
        book.toc = (chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + chapters

        # 5. 保存
        epub.write_epub(epub_path, book, {})
        print(f"🎉 成功！Epub 已生成：\n   -> {epub_path}")
        
        
        
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    TXT_FILENAME = '大乘期才有逆袭系统.txt'
    EPUB_FILENAME = '大乘期才有逆袭系统.epub'
    FONT_FILENAME = '字魂风华雅宋.ttf'
    
    BOOK_TITLE = '大乘期才有逆袭系统'
    BOOK_AUTHOR = '最白的乌鸦'
    
    txt_file_path = os.path.join(project_root, 'input', TXT_FILENAME)
    epub_file_path = os.path.join(project_root, 'output', EPUB_FILENAME)
    font_file_path = os.path.join(project_root, 'fonts', FONT_FILENAME)
    
    Kernel.txt_to_epub(txt_file_path, epub_file_path, BOOK_TITLE, BOOK_AUTHOR, font_file_path)