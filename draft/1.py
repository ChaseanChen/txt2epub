import re
import os
import sys
from ebooklib import epub

def txt_to_epub(txt_path, epub_path, title, author):
    # 0. 检查文件是否存在
    if not os.path.exists(txt_path):
        print(f"❌ 错误：找不到文件 '{txt_path}'。请确保txt文件和代码在同一个目录下。")
        return

    print(f"📖 开始读取 '{txt_path}'...")

    # 1. 创建 EPUB 书籍对象
    book = epub.EpubBook()
    book.set_identifier('id123456')
    book.set_title(title)
    book.set_language('zh-cn')
    book.add_author(author)

    # 2. 读取 TXT 内容 (自动尝试不同编码)
    content = ""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            print("⚠️ UTF-8 解码失败，尝试使用 GB18030 解码...")
            with open(txt_path, 'r', encoding='gb18030') as f:
                content = f.read()
        except UnicodeDecodeError:
            print("❌ 错误：无法识别文件编码，请手动将TXT另存为UTF-8格式。")
            return

    # 3. 正则表达式匹配章节
    print("🔍 正在分析章节结构...")
    # 这里的正则匹配：行首 + (空白) + 第 + 数字/中文 + 章
    pattern = re.compile(r'(^\s*第[0-9一二三四五六七八九十百千万]+章.*$)', re.MULTILINE)
    
    parts = pattern.split(content)
    
    if len(parts) < 2:
        print("❌ 警告：未匹配到任何章节！")
        print("   可能有以下原因：")
        print("   1. 小说章节标题不是以“第x章”开头。")
        print("   2. TXT文件格式混乱。")
        return

    chapters = []
    
    # 处理序章
    if parts[0].strip():
        c = epub.EpubHtml(title='序言', file_name='intro.xhtml', lang='zh-cn')
        text_body = parts[0].replace('\n', '</p><p>')
        c.content = f'<h1>序言</h1><p>{text_body}</p>'
        book.add_item(c)
        chapters.append(c)

    # 处理正文
    chapter_titles = parts[1::2]
    chapter_contents = parts[2::2]

    total_chapters = len(chapter_titles)
    print(f"✅ 识别到 {total_chapters} 个章节，正在打包...")

    for i, (chap_title, chap_content) in enumerate(zip(chapter_titles, chapter_contents)):
        chap_title = chap_title.strip()
        c = epub.EpubHtml(title=chap_title, file_name=f'chap_{i+1}.xhtml', lang='zh-cn')
        
        lines = [line.strip() for line in chap_content.split('\n') if line.strip()]
        body_html = ''.join([f'<p>{line}</p>' for line in lines])
        
        c.content = f'<h1>{chap_title}</h1>{body_html}'
        book.add_item(c)
        chapters.append(c)

    # 4. 生成目录
    book.toc = (chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapters

    # 5. 保存
    epub.write_epub(epub_path, book, {})
    print(f"🎉 成功！文件已生成：{epub_path}")

# --- 主程序入口 ---
if __name__ == '__main__':
    # 配置信息
    TXT_FILE = '史上最强师兄.txt'
    EPUB_FILE = '史上最强师兄.epub'
    BOOK_TITLE = '史上最强师兄'
    BOOK_AUTHOR = '八月飞鹰'

    # 运行转换
    txt_to_epub(TXT_FILE, EPUB_FILE, BOOK_TITLE, BOOK_AUTHOR)