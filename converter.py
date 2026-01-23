import os
import re
import uuid
import logging
from typing import List, Tuple, Optional
from ebooklib import epub

# 设置简单的日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EPubGenerator:
    def __init__(self, font_path: Optional[str] = None):
        self.font_path = font_path
        # 优化正则：兼容更广泛的章节命名，如 "Chapter 1", "第一部" 等
        self.chapter_pattern = re.compile(
            r'(^\s*(?:第[0-9零一二三四五六七八九十百千]+[章节回卷部]|Chapter\s?\d+).*?$)', 
            re.MULTILINE | re.IGNORECASE
        )
        # 用于生成 UUID 的固定命名空间（类似域名的作用）
        self.NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "ebook.converter.local")

    def _generate_stable_id(self, title: str, author: str) -> str:
        """
        生成基于书名和作者的确定性 UUID。
        改进点：进行归一化处理（去除空格、转小写），确保无论文件名如何变化，
        只要核心要素不变，ID 就不变，从而保留阅读进度。
        """
        norm_title = title.strip().lower()
        norm_author = author.strip().lower()
        unique_string = f"{norm_title}::{norm_author}"
        return str(uuid.uuid5(self.NAMESPACE, unique_string))

    def _get_default_css(self, font_file_name: Optional[str] = None) -> str:
        font_face = ""
        font_family = "'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif"
        
        if font_file_name:
            font_face = f'@font-face {{ font-family: "CustomFont"; src: url("fonts/{font_file_name}"); }}'
            font_family = '"CustomFont", sans-serif'
            
        return f'''
            {font_face}
            body {{ font-family: {font_family}; line-height: 1.8; text-align: justify; margin: 0 5px; background-color: #fcfcfc; }}
            p {{ text-indent: 2em; margin: 0.8em 0; font-size: 1em; }}
            h1 {{ font-weight: bold; text-align: center; margin: 2em 0 1em 0; font-size: 1.6em; page-break-before: always; }}
            div.cover {{ text-align: center; height: 100%; }}
            img {{ max-width: 100%; height: auto; }}
        '''

    def _try_get_cover(self, txt_path: str) -> Tuple[Optional[str], Optional[str]]:
        base_dir = os.path.dirname(txt_path)
        file_basename = os.path.splitext(os.path.basename(txt_path))[0]
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

    def _parse_chapters(self, content: str) -> List[Tuple[str, str]]:
        matches = list(self.chapter_pattern.finditer(content))
        chapters = []

        if not matches:
            logging.info("未检测到明显章节目录，作为单章处理。")
            return [("正文", content)]

        # 处理序章/前言（第一个匹配项之前的内容）
        preface_end = matches[0].start()
        if preface_end > 0:
            preface_content = content[:preface_end].strip()
            if len(preface_content) > 50: # 简单的过滤，太短的可能是乱码或元数据
                chapters.append(("序言", preface_content))

        count = len(matches)
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start_idx = match.end()
            # 这里的逻辑是：本章开始到下一章开始前
            end_idx = matches[i+1].start() if i + 1 < count else len(content)
            
            body = content[start_idx:end_idx]
            # 简单的正文清洗：去除首尾空行，防止章节之间空隙过大
            chapters.append((title, body.strip()))
            
        return chapters

    def run(self, txt_path: str, epub_path: str, title: str, author: str):
        print(f"\n正在处理: [{os.path.basename(txt_path)}]")
        
        book = epub.EpubBook()
        # [关键修复] 使用确定性 ID
        book_id = self._generate_stable_id(title, author)
        book.set_identifier(book_id)
        book.set_title(title)
        book.set_language('zh-cn')
        book.add_author(author)
        
        # 调试信息
        logging.debug(f"Book ID generated: {book_id}")

        # 封面处理
        cover_path, cover_ext = self._try_get_cover(txt_path)
        if cover_path:
            try:
                with open(cover_path, 'rb') as f:
                    book.set_cover(f"cover{cover_ext}", f.read())
                print(f"  [+] 已添加封面: {os.path.basename(cover_path)}")
            except Exception as e:
                print(f"  [!] 封面读取失败: {e}")
        
        # 字体处理
        css_item = None
        font_filename = None
        if self.font_path and os.path.exists(self.font_path):
            font_filename = os.path.basename(self.font_path)
            try:
                with open(self.font_path, 'rb') as f:
                    book.add_item(epub.EpubItem(
                        uid="custom_font", file_name=f"fonts/{font_filename}",
                        media_type="application/x-font-ttf", content=f.read()
                    ))
                print(f"  [+] 已嵌入字体: {font_filename}")
            except Exception as e:
                print(f"  [!] 字体嵌入失败: {e}")
                font_filename = None

        css_content = self._get_default_css(font_filename)
        css_item = epub.EpubItem(uid="style_css", file_name="style.css", media_type="text/css", content=css_content)
        book.add_item(css_item)

        # 读取内容 (增强编码识别)
        content = ""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                print("  [i] UTF-8 解码失败，尝试 GB18030 (兼容GBK)...")
                with open(txt_path, 'r', encoding='gb18030') as f:
                    content = f.read()
            except Exception:
                print(f"  [Error] 无法识别文件编码，跳过: {txt_path}")
                return

        parsed_chapters = self._parse_chapters(content)
        print(f"  [i] 识别到 {len(parsed_chapters)} 个章节")
        
        epub_chapters = []
        for i, (chap_title, chap_body) in enumerate(parsed_chapters):
            file_name = f'chap_{i+1}.xhtml'
            c = epub.EpubHtml(title=chap_title, file_name=file_name, lang='zh-cn')
            c.add_item(css_item)
            
            # 增强段落处理：
            # 1. splitlines() 切分行
            # 2. strip() 去除每行首尾空白
            # 3. 过滤空行
            # 4. 包装 <p> 标签
            lines = []
            for line in chap_body.splitlines():
                clean_line = line.strip()
                if clean_line:
                    lines.append(f"<p>{clean_line}</p>")
            
            c.content = f'<h1>{chap_title}</h1>' + "".join(lines)
            book.add_item(c)
            epub_chapters.append(c)

        # 构建目录结构
        book.toc = epub_chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # 定义阅读顺序 (Spine)
        if book.cover_image: # type: ignore
            # 如果有封面，通常阅读器会自动处理，不需要手动加入 spine，但为了保险可以配置
            pass 
        book.spine = ['nav'] + epub_chapters

        # 确保输出目录存在
        output_dir = os.path.dirname(epub_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try:
            epub.write_epub(epub_path, book, {})
            print(f"  [Success] 生成完毕: {os.path.basename(epub_path)}")
        except Exception as e:
            print(f"  [Error] 保存 EPUB 失败: {e}")