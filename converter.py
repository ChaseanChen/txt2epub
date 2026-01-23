# converter.py
import os
import uuid
import logging
from ebooklib import epub
from utils import detect_file_encoding
from parser import TxtParser
from resources import ResourceManager
from typing import Optional
from tqdm import tqdm

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EPubBuilder:
    """
    EPUB 构建器
    """
    def __init__(self, font_path: Optional[str] = None, assets_dir: Optional[str] = None):
        self.resource_mgr = ResourceManager(assets_dir, font_path)
        self.NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "ebook.converter.local")

    def build(self, txt_path: str, epub_path: str, title: str, author: str):
        print(f"\n正在处理: [{os.path.basename(txt_path)}]")
        
        # 1. 编码检测
        encoding = detect_file_encoding(txt_path)
        if not encoding:
            logging.error(f"无法识别文件编码，跳过: {txt_path}")
            return

        # 2. 初始化书籍
        book = epub.EpubBook()
        self._setup_metadata(book, title, author)

        # 3. 准备资源 (CSS, Font, Cover)
        # [修复] 预先初始化变量，防止 try 块报错导致变量未绑定
        css_item = None
        font_item = None
        
        try:
            # 3.1 封面
            cover_name, cover_data, _ = self.resource_mgr.get_cover_image(txt_path)
            if cover_data:
                book.set_cover(cover_name, cover_data)
                logging.info("已设置封面")
            
            # 3.2 字体与 CSS
            font_item, font_rule, font_family = self.resource_mgr.get_font_resource()
            if font_item:
                book.add_item(font_item)
            
            # 生成 CSS
            css_item = self.resource_mgr.get_css(font_rule, font_family)
            book.add_item(css_item)
            
        except Exception as e:
            logging.error(f"资源加载部分失败 (非致命): {e}")
            # 这里不 return，继续处理文本，但需要确保 css_item 存在

        # [修复] 兜底逻辑：如果上述 try 块失败导致 css_item 为空，生成默认 CSS
        if css_item is None:
            logging.warning("使用兜底 CSS 配置")
            # 获取没有任何自定义字体的默认 CSS
            css_item = self.resource_mgr.get_css("", "sans-serif")
            book.add_item(css_item)

        # 4. 解析并构建章节
        parser = TxtParser(txt_path, encoding)
        chapter_items = []
        
        print("  [i] 正在构建章节...")
        
        try:
            with tqdm(unit="chap", desc="  解析进度") as pbar:
                for chap_idx, (chap_title, chap_content) in enumerate(parser.parse()):
                    # 构建 HTML
                    file_name = f'chap_{chap_idx}.xhtml'
                    c = epub.EpubHtml(title=chap_title, file_name=file_name, lang='zh-cn')
                    
                    # 此时 css_item 必然有值（要么是加载成功的，要么是兜底的）
                    c.add_item(css_item)
                    c.content = self._render_chapter_html(chap_title, chap_content)
                    
                    book.add_item(c)
                    chapter_items.append(c)
                    
                    pbar.update(1)
                    
        except Exception as e:
            logging.error(f"章节解析过程中发生严重错误: {e}")
            return 

        logging.info(f"共生成 {len(chapter_items)} 个章节")

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
        body = body.replace('\r\n', '\n').replace('\r', '\n')
        html_parts = [f'<h1>{title}</h1>']
        
        raw_lines = body.split('\n')
        empty_lines_count = 0
        
        for line in raw_lines:
            clean_line = line.strip()
            
            if not clean_line:
                empty_lines_count += 1
                continue
            
            if empty_lines_count >= 2:
                html_parts.append('<div class="scene-break">***</div>')
            
            empty_lines_count = 0
            
            clean_line = (clean_line.replace('&', '&amp;')
                                    .replace('<', '&lt;')
                                    .replace('>', '&gt;'))
            
            html_parts.append(f"<p>{clean_line}</p>")
            
        return "".join(html_parts)

    def _write_to_disk(self, book, output_path):
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except OSError as e:
                logging.error(f"创建输出目录失败: {e}")
                return

        try:
            epub.write_epub(output_path, book, {})
            logging.info(f"EPUB 生成完毕: {output_path}")
        except PermissionError:
            logging.error(f"写入失败: 权限不足。请检查文件是否被其他程序占用: {output_path}")
        except Exception as e:
            logging.error(f"写入磁盘时发生未知错误: {e}")