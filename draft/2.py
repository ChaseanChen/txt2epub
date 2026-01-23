import re
import os
# import sys
from ebooklib import epub

def txt_to_epub_with_font(txt_path, epub_path, title, author, font_path=None):
    # --- 路径检查 ---
    print(f"📂 输入文件: {txt_path}")
    print(f"📂 输出路径: {epub_path}")
    if font_path:
        print(f"🎨 字体路径: {font_path}")

    if not os.path.exists(txt_path):
        print(f"❌ 错误：找不到输入文件 '{txt_path}'")
        return 

    # 确保输出目录存在，不存在则创建
    output_dir = os.path.dirname(epub_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 已创建输出目录: {output_dir}")

    print(f"📖 开始读取并转换 '{title}'...")

    # 1. 创建 EPUB 书籍对象
    book = epub.EpubBook()
    book.set_identifier('id_shu_shi_zui_qiang') # 建议用唯一的ID
    book.set_title(title)
    book.set_language('zh-cn')
    book.add_author(author)

    # --- 字体处理核心逻辑 ---
    css_item = None
    if font_path and os.path.exists(font_path):
        print("🎨 正在嵌入字体 (这会增加文件体积)...")
        
        # A. 读取字体
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

        # B. 创建 CSS (使用你的字体名)
        # 注意：font-family 名字可以自定义，这里叫 "MyFont"
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
            p {{
                text-indent: 2em;
                margin-bottom: 0.8em;
            }}
            h1 {{
                font-family: "MyFont", sans-serif;
                text-align: center;
                font-weight: bold;
                margin-top: 1em;
                margin-bottom: 1em;
            }}
        '''
        
        css_item = epub.EpubItem(
            uid="style_css",
            file_name="style.css",
            media_type="text/css",
            content=css_content
        )
        book.add_item(css_item)
    else:
        if font_path:
            print(f"⚠️ 警告：找不到字体文件 '{font_path}'，将生成无自定义字体的版本。")

    # 2. 读取 TXT 内容
    content = ""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            print("⚠️ UTF-8 解码失败，尝试 GB18030...")
            with open(txt_path, 'r', encoding='gb18030') as f:
                content = f.read()
        except UnicodeDecodeError:
            print("❌ 错误：无法识别文件编码。")
            return

    # 3. 正则表达式匹配章节
    print("🔍 正在分析章节结构...")
    pattern = re.compile(r'(^\s*第[0-9一二三四五六七八九十百千万]+章.*$)', re.MULTILINE)
    parts = pattern.split(content)

    if len(parts) < 2:
        print("❌ 警告：未匹配到任何章节！请检查TXT内容格式。")
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

# --- 主程序配置区 ---
if __name__ == '__main__':
    # 1. 自动获取当前脚本所在目录 (src/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. 获取项目根目录 (draft/) - 即 src 的上一级
    project_root = os.path.dirname(current_dir)

    # 3. 定义文件名 (只需要改这里)
    TXT_FILENAME = '大乘期才有逆袭系统.txt'
    EPUB_FILENAME = '大乘期才有逆袭系统.epub'
    FONT_FILENAME = '字魂风华雅宋.ttf'  # 必须和 fonts 文件夹里的名字完全一致
    
    BOOK_TITLE = '大乘期才有逆袭系统'
    BOOK_AUTHOR = '最白的乌鸦'

    # 4. 自动拼接绝对路径 (适配你的目录结构)
    txt_file_path = os.path.join(project_root, 'input', TXT_FILENAME)
    epub_file_path = os.path.join(project_root, 'output', EPUB_FILENAME)
    font_file_path = os.path.join(project_root, 'fonts', FONT_FILENAME)

    # 5. 运行
    txt_to_epub_with_font(txt_file_path, epub_file_path, BOOK_TITLE, BOOK_AUTHOR, font_file_path)