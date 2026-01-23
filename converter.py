# converter.py
import os
import uuid
import logging
from ebooklib import epub
from utils import detect_file_encoding
from parser import TxtParser
from resources import ResourceManager
from typing import Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EPubBuilder:
    """
    EPUB 构建器 (Builder Pattern)
    职责：协调 Parser 和 ResourceManager，组装最终的 EpubBook 对象并写入磁盘。
    """
    def __init__(self, font_path: Optional[str] = None, assets_dir: Optional[str] = None):
        self.resource_mgr = ResourceManager(assets_dir, font_path)
        self.NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "ebook.converter.local")

    def build(self, txt_path: str, epub_path: str, title: str, author: str):
        print(f"\n正在处理: [{os.path.basename(txt_path)}]")
        
        # 1. 编码检测
        encoding = detect_file_encoding(txt_path)
        if not encoding:
            print(f"  [Error] 无法识别文件编码，跳过: {txt_path}")
            return

        # 2. 初始化书籍
        book = epub.EpubBook()
        self._setup_metadata(book, title, author)

        # 3. 准备资源 (CSS, Font, Cover)
        # 3.1 封面
        cover_name, cover_data, _ = self.resource_mgr.get_cover_image(txt_path)
        if cover_data:
            book.set_cover(cover_name, cover_data)
            print("  [+] 已设置封面")
        else:
            print("  [i] 未检测到封面，将使用文本封面")
        
        # 3.2 字体与 CSS
        font_item, font_rule, font_family = self.resource_mgr.get_font_resource()
        if font_item:
            book.add_item(font_item)
        
        css_item = self.resource_mgr.get_css(font_rule, font_family)
        book.add_item(css_item)

        # 4. 解析并构建章节 (核心改进：流式处理)
        parser = TxtParser(txt_path, encoding)
        chapter_items = []
        
        print("  [i] 正在流式解析并构建章节...")
        
        # 使用生成器迭代，内存占用极低
        for chap_idx, (chap_title, chap_content) in enumerate(parser.parse()):
            # 构建 HTML
            file_name = f'chap_{chap_idx}.xhtml'
            c = epub.EpubHtml(title=chap_title, file_name=file_name, lang='zh-cn')
            c.add_item(css_item)
            c.content = self._render_chapter_html(chap_title, chap_content)
            
            book.add_item(c)
            chapter_items.append(c)

        print(f"  [i] 共处理 {len(chapter_items)} 个章节")

        # 5. 设置目录和 spine
        book.toc = chapter_items
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + chapter_items

        # 6. 写入文件
        self._write_to_disk(book, epub_path)

    def _setup_metadata(self, book, title, author):
        unique_string = f"{title}::{author}"
        book_id = str(uuid.uuid5(self.NAMESPACE, unique_string))
        book.set_identifier(book_id)
        book.set_title(title)
        book.set_language('zh-cn')
        book.add_author(author)

    def _render_chapter_html(self, title, body) -> str:
        lines = []
        for line in body.splitlines():
            clean_line = line.strip()
            if clean_line:
                # 简单的 HTML 转义
                clean_line = (clean_line.replace('&', '&amp;')
                                        .replace('<', '&lt;')
                                        .replace('>', '&gt;'))
                lines.append(f"<p>{clean_line}</p>")
        body_content = "".join(lines)
        return f'<h1>{title}</h1>{body_content}'

    def _write_to_disk(self, book, output_path):
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        try:
            epub.write_epub(output_path, book, {})
            print(f"  [Success] 生成完毕: {os.path.basename(output_path)}")
        except Exception as e:
            print(f"  [Error] 保存文件失败: {e}")