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
    """
    核心转换器类。
    改进点：
    1. 支持加载外部 CSS 文件。
    2. 更加健壮的封面与元数据处理。
    """
    def __init__(self, font_path: Optional[str] = None, assets_dir: Optional[str] = None):
        self.font_path = font_path
        self.assets_dir = assets_dir
        
        # 正则预编译
        self.chapter_pattern = re.compile(
            r'(^\s*(?:第[0-9零一二三四五六七八九十百千两]+[章节回卷部]|Chapter\s?\d+).*?$)', 
            re.MULTILINE | re.IGNORECASE
        )
        self.MAX_TITLE_LENGTH = 40 
        self.NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "ebook.converter.local")
        
        # 默认字体栈（用于后备）
        self.default_font_family = "'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"

    def convert(self, txt_path: str, epub_path: str, title: str, author: str):
        """主入口方法"""
        file_name = os.path.basename(txt_path)
        print(f"\n正在处理: [{file_name}]")

        # 1. 读取内容
        content = self._load_content(txt_path)
        if not content:
            return

        # 2. 解析章节
        parsed_chapters = self._parse_chapters(content)
        print(f"  [i] 识别到 {len(parsed_chapters)} 个章节")

        # 3. 初始化书籍对象
        book = epub.EpubBook()
        self._setup_metadata(book, title, author)

        # 4. 嵌入资源 (封面、字体、CSS)
        css_item = self._embed_resources(book, txt_path)

        # 5. 构建章节
        self._build_chapters(book, parsed_chapters, css_item)

        # 6. 写入文件
        self._write_epub(book, epub_path)

    def _load_content(self, txt_path: str) -> Optional[str]:
        encodings = ['utf-8', 'gb18030', 'gbk', 'big5', 'utf-16']
        for enc in encodings:
            try:
                with open(txt_path, 'r', encoding=enc) as f:
                    content = f.read()
                if enc != 'utf-8':
                    print(f"  [i] 使用 {enc} 编码成功读取。")
                return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"  [Error] 读取文件出错: {e}")
                return None
        print(f"  [Error] 无法识别文件编码，跳过: {txt_path}")
        return None

    def _setup_metadata(self, book: epub.EpubBook, title: str, author: str):
        book_id = self._generate_stable_id(title, author)
        book.set_identifier(book_id)
        book.set_title(title)
        book.set_language('zh-cn')
        book.add_author(author)

    def _embed_resources(self, book: epub.EpubBook, txt_path: str) -> epub.EpubItem:
        """
        加载 CSS、字体和封面。
        """
        # --- 1. 封面处理 (Cover Image) ---
        # 逻辑：优先找同名图片 -> 其次找 cover.jpg -> 最后看 assets 目录有没有默认 cover
        cover_path, cover_ext = self._try_get_cover(txt_path)
        
        if cover_path:
            try:
                with open(cover_path, 'rb') as f:
                    book.set_cover(f"cover{cover_ext}", f.read())
                print(f"  [+] 已添加封面: {os.path.basename(cover_path)}")
            except Exception as e:
                print(f"  [!] 封面读取失败: {e}")
        else:
            print("  [i] 未找到封面图片，将生成纯文本封面。")

        # --- 2. 字体处理 ---
        font_face_rule = ""
        css_font_family = self.default_font_family
        
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
                # 生成动态的 @font-face 规则
                font_face_rule = f'@font-face {{ font-family: "CustomFont"; src: url("fonts/{font_filename}"); }}\n'
                css_font_family = '"CustomFont", sans-serif'
                print(f"  [+] 已嵌入字体: {font_filename}")
            except Exception as e:
                print(f"  [!] 字体嵌入失败: {e}")

        # --- 3. CSS 处理 (核心改进) ---
        # 我们把 动态CSS (字体) 和 静态CSS (文件) 分离
        
        # 动态部分
        dynamic_css = f"""
        {font_face_rule}
        body {{ font-family: {css_font_family}; }}
        """

        # 静态部分 (从 assets/style.css 读取)
        static_css = ""
        style_path = os.path.join(self.assets_dir, 'style.css') if self.assets_dir else None
        
        if style_path and os.path.exists(style_path):
            try:
                with open(style_path, 'r', encoding='utf-8') as f:
                    static_css = f.read()
                print("  [+] 已加载外部样式表 (assets/style.css)")
            except Exception as e:
                print(f"  [!] 读取样式表失败，使用内置默认样式: {e}")
                static_css = self._get_fallback_css()
        else:
            static_css = self._get_fallback_css()

        # 合并 CSS
        final_css_content = dynamic_css + "\n" + static_css

        css_item = epub.EpubItem(
            uid="style_css", 
            file_name="style.css", 
            media_type="text/css", 
            content=final_css_content
        )
        book.add_item(css_item)
        return css_item

    def _build_chapters(self, book: epub.EpubBook, chapters: List[Tuple[str, str]], css_item: epub.EpubItem):
        epub_chapters = []
        for i, (chap_title, chap_body) in enumerate(chapters):
            file_name = f'chap_{i+1}.xhtml'
            c = epub.EpubHtml(title=chap_title, file_name=file_name, lang='zh-cn')
            c.add_item(css_item)
            
            lines = []
            for line in chap_body.splitlines():
                clean_line = line.strip()
                if clean_line:
                    # 转义 HTML 特殊字符
                    clean_line = (clean_line.replace('&', '&amp;')
                                            .replace('<', '&lt;')
                                            .replace('>', '&gt;'))
                    lines.append(f"<p>{clean_line}</p>")
            
            body_content = "".join(lines) if lines else "<p></p>"
            c.content = f'<h1>{chap_title}</h1>{body_content}'
            
            book.add_item(c)
            epub_chapters.append(c)

        book.toc = epub_chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + epub_chapters

    def _write_epub(self, book: epub.EpubBook, output_path: str):
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        try:
            epub.write_epub(output_path, book, {})
            print(f"  [Success] 生成完毕: {os.path.basename(output_path)}")
        except Exception as e:
            print(f"  [Error] 保存 EPUB 失败: {e}")

    # --- Helpers ---

    def _get_fallback_css(self) -> str:
        """内置的默认样式，仅在文件丢失时使用"""
        return '''
            body { line-height: 1.8; text-align: justify; margin: 0 5px; background-color: #fcfcfc; }
            p { text-indent: 2em; margin: 0.8em 0; font-size: 1em; }
            h1 { font-weight: bold; text-align: center; margin: 2em 0 1em 0; font-size: 1.6em; page-break-before: always; color: #333; }
            img { max-width: 100%; height: auto; }
        '''

    def _generate_stable_id(self, title: str, author: str) -> str:
        norm_title = title.strip().lower()
        norm_author = author.strip().lower()
        unique_string = f"{norm_title}::{norm_author}"
        return str(uuid.uuid5(self.NAMESPACE, unique_string))

    def _try_get_cover(self, txt_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        尝试寻找封面:
        1. [txt文件名].jpg/png
        2. cover.jpg/png (在同级目录下)
        3. 默认封面 (在 assets 目录下) - 可选扩展
        """
        base_dir = os.path.dirname(txt_path)
        file_basename = os.path.splitext(os.path.basename(txt_path))[0]
        valid_exts = ['.jpg', '.jpeg', '.png']
        
        # 1. 检查同名图片
        for ext in valid_exts:
            img_path = os.path.join(base_dir, file_basename + ext)
            if os.path.exists(img_path):
                return img_path, ext
        
        # 2. 检查 cover.jpg
        for ext in valid_exts:
            img_path = os.path.join(base_dir, 'cover' + ext)
            if os.path.exists(img_path):
                return img_path, ext
                
        return None, None

    def _parse_chapters(self, content: str) -> List[Tuple[str, str]]:
        raw_matches = list(self.chapter_pattern.finditer(content))
        valid_matches = []
        for m in raw_matches:
            if len(m.group(1).strip()) <= self.MAX_TITLE_LENGTH:
                valid_matches.append(m)
        
        chapters = []
        if not valid_matches:
            logging.info("未检测到有效章节目录，作为单章处理。")
            return [("正文", content)]

        first_match_start = valid_matches[0].start()
        if first_match_start > 0:
            preface = content[:first_match_start].strip()
            if preface: 
                chapters.append(("序言", preface))

        count = len(valid_matches)
        for i, match in enumerate(valid_matches):
            title = match.group(1).strip()
            start_idx = match.end()
            end_idx = valid_matches[i+1].start() if i + 1 < count else len(content)
            body = content[start_idx:end_idx].strip()
            chapters.append((title, body))
            
        return chapters