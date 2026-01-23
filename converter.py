# converter.py
import os
import uuid
import logging
# import re  # 新增 re 用于更强的文本清洗
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

        # 4. 解析并构建章节
        parser = TxtParser(txt_path, encoding)
        chapter_items = []
        
        print("  [i] 正在流式解析并构建章节...")
        
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
        """
        核心改进：智能段落处理
        1. 归一化换行符
        2. 保留场景分隔（连续空行）
        3. 使用 strip() 清洗缩进，依赖 CSS text-indent 进行标准化排版
        """
        # 1. 归一化换行符，防止不同平台的差异
        body = body.replace('\r\n', '\n').replace('\r', '\n')
        
        html_parts = [f'<h1>{title}</h1>']
        
        # 2. 逐行处理
        # 使用状态机逻辑：记录连续空行数量
        raw_lines = body.split('\n')
        empty_lines_count = 0
        
        for line in raw_lines:
            # 清洗行：去除两端空白（包括全角空格 \u3000）
            clean_line = line.strip()
            
            if not clean_line:
                empty_lines_count += 1
                continue
            
            # 逻辑：如果之前的空行数 >= 2，说明这是一个场景分割（Scene Break）
            # 我们插入一个视觉分隔符，而不是生成空 <p>
            if empty_lines_count >= 2:
                html_parts.append('<div class="scene-break">***</div>')
            
            # 重置计数器
            empty_lines_count = 0
            
            # HTML 转义
            clean_line = (clean_line.replace('&', '&amp;')
                                    .replace('<', '&lt;')
                                    .replace('>', '&gt;'))
            
            # 包装段落
            html_parts.append(f"<p>{clean_line}</p>")
            
        return "".join(html_parts)

    def _write_to_disk(self, book, output_path):
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        try:
            epub.write_epub(output_path, book, {})
            print(f"  [Success] 生成完毕: {os.path.basename(output_path)}")
        except Exception as e:
            print(f"  [Error] 保存文件失败: {e}")