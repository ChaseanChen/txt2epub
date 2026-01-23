# converter.py
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
        # 优化正则：
        # 1. 兼容 "第x章", "Chapter x"
        # 2. 使用非捕获组 (?:...) 优化性能
        # 3. 匹配行首空白 ^\s*
        self.chapter_pattern = re.compile(
            r'(^\s*(?:第[0-9零一二三四五六七八九十百千两]+[章节回卷部]|Chapter\s?\d+).*?$)', 
            re.MULTILINE | re.IGNORECASE
        )
        # 标题最大允许长度（超过此长度的行，即使匹配正则，也被视为正文，防止误判）
        self.MAX_TITLE_LENGTH = 40 
        
        # 用于生成 UUID 的固定命名空间
        self.NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "ebook.converter.local")

    def _generate_stable_id(self, title: str, author: str) -> str:
        """生成基于书名和作者的确定性 UUID。"""
        norm_title = title.strip().lower()
        norm_author = author.strip().lower()
        unique_string = f"{norm_title}::{norm_author}"
        return str(uuid.uuid5(self.NAMESPACE, unique_string))

    def _get_default_css(self, font_file_name: Optional[str] = None) -> str:
        font_face = ""
        # 优化字体栈，优先显示常见中文字体
        font_family = "'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Source Han Sans CN', sans-serif"
        
        if font_file_name:
            font_face = f'@font-face {{ font-family: "CustomFont"; src: url("fonts/{font_file_name}"); }}'
            font_family = '"CustomFont", sans-serif'
            
        return f'''
            {font_face}
            body {{ font-family: {font_family}; line-height: 1.8; text-align: justify; margin: 0 5px; background-color: #fcfcfc; }}
            p {{ text-indent: 2em; margin: 0.8em 0; font-size: 1em; }}
            h1 {{ font-weight: bold; text-align: center; margin: 2em 0 1em 0; font-size: 1.6em; page-break-before: always; color: #333; }}
            div.cover {{ text-align: center; height: 100%; }}
            img {{ max-width: 100%; height: auto; }}
        '''

    def _try_get_cover(self, txt_path: str) -> Tuple[Optional[str], Optional[str]]:
        """尝试查找同目录下的封面图片"""
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
        """
        核心分章逻辑 (Refined)
        使用 finditer 代替 split，并增加误判校验。
        """
        # 1. 找出所有潜在的标题匹配项
        raw_matches = list(self.chapter_pattern.finditer(content))
        
        # 2. 过滤无效标题（例如过长的行）
        valid_matches = []
        for m in raw_matches:
            title_text = m.group(1).strip()
            # 如果标题过长，很可能是正文中的长句，跳过
            if len(title_text) <= self.MAX_TITLE_LENGTH:
                valid_matches.append(m)
        
        chapters = []

        # 情况 A: 没有检测到任何有效章节，整本作为一章
        if not valid_matches:
            logging.info("未检测到有效章节目录，作为单章处理。")
            return [("正文", content)]

        # 情况 B: 处理序章/前言 (第一个有效章节之前的内容)
        first_match_start = valid_matches[0].start()
        if first_match_start > 0:
            preface_content = content[:first_match_start].strip()
            # 只有当序章内容有一定长度时才添加，避免添加空字符串
            if len(preface_content) > 0: 
                chapters.append(("序言", preface_content))

        # 情况 C: 提取各章节内容
        count = len(valid_matches)
        for i, match in enumerate(valid_matches):
            title = match.group(1).strip()
            
            # 当前章节内容的起始位置 = 当前标题的结束位置
            start_idx = match.end()
            
            # 当前章节内容的结束位置 = 下一个标题的起始位置 (如果是最后一章，则到文件末尾)
            if i + 1 < count:
                end_idx = valid_matches[i+1].start()
            else:
                end_idx = len(content)
            
            body = content[start_idx:end_idx].strip()
            
            # 即使 body 为空（例如连续标题），也保留该章节（作为目录节点）
            chapters.append((title, body))
            
        return chapters

    def run(self, txt_path: str, epub_path: str, title: str, author: str):
        file_name = os.path.basename(txt_path)
        print(f"\n正在处理: [{file_name}]")
        
        book = epub.EpubBook()
        # ID 处理
        book_id = self._generate_stable_id(title, author)
        book.set_identifier(book_id)
        book.set_title(title)
        book.set_language('zh-cn')
        book.add_author(author)
        
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

        # 读取内容 (增强编码兼容性)
        content = ""
        encodings = ['utf-8', 'gb18030', 'gbk', 'big5', 'utf-16']
        for enc in encodings:
            try:
                with open(txt_path, 'r', encoding=enc) as f:
                    content = f.read()
                if enc != 'utf-8':
                    print(f"  [i] 使用 {enc} 编码成功读取。")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"  [Error] 读取文件出错: {e}")
                return
        
        if not content:
            print(f"  [Error] 无法识别文件编码，跳过: {txt_path}")
            return

        # 调用改进后的分章逻辑
        parsed_chapters = self._parse_chapters(content)
        print(f"  [i] 识别到 {len(parsed_chapters)} 个章节")
        
        epub_chapters = []
        for i, (chap_title, chap_body) in enumerate(parsed_chapters):
            file_name = f'chap_{i+1}.xhtml'
            c = epub.EpubHtml(title=chap_title, file_name=file_name, lang='zh-cn')
            c.add_item(css_item)
            
            # HTML 内容构建
            lines = []
            for line in chap_body.splitlines():
                clean_line = line.strip()
                if clean_line:
                    # 简单转义 HTML 特殊字符，防止内容破坏结构
                    clean_line = clean_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    lines.append(f"<p>{clean_line}</p>")
            
            # 即使内容为空，也要有基本的结构
            body_content = "".join(lines) if lines else "<p></p>"
            c.content = f'<h1>{chap_title}</h1>{body_content}'
            
            book.add_item(c)
            epub_chapters.append(c)

        # 构建目录结构
        book.toc = epub_chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # 定义阅读顺序 (Spine)
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