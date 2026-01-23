# converter.py
import os
import re
import uuid
from ebooklib import epub

class EPubGenerator:
    def __init__(self, font_path=None):
        self.font_path = font_path
        # 预编译正则：匹配 第X章/节/回 等格式
        self.chapter_pattern = re.compile(r'(^\s*第.{1,12}[章节回卷].*?$)', re.MULTILINE)

    def _generate_stable_id(self, title, author):
        """生成基于书名和作者的确定性UUID"""
        unique_string = f"{title}-{author}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

    def _get_default_css(self, font_file_name=None):
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

    def _parse_chapters(self, content):
        matches = list(self.chapter_pattern.finditer(content))
        chapters = []

        if not matches:
            return [("正文", content)]

        preface_end = matches[0].start()
        if preface_end > 0:
            preface_content = content[:preface_end].strip()
            if preface_content:
                chapters.append(("序言", preface_content))

        count = len(matches)
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start_idx = match.end()
            end_idx = matches[i+1].start() if i + 1 < count else len(content)
            chapters.append((title, content[start_idx:end_idx]))
            
        return chapters

    def run(self, txt_path, epub_path, title, author):
        print(f"\n正在处理: [{os.path.basename(txt_path)}]")
        
        book = epub.EpubBook()
        book.set_identifier(self._generate_stable_id(title, author))
        book.set_title(title)
        book.set_language('zh-cn')
        book.add_author(author)

        # 封面
        cover_path, cover_ext = self._try_get_cover(txt_path)
        if cover_path:
            try:
                with open(cover_path, 'rb') as f:
                    book.set_cover(f"cover{cover_ext}", f.read())
                print(f"  [+] 已添加封面: {os.path.basename(cover_path)}")
            except Exception as e:
                print(f"  [!] 封面读取失败: {e}")
        
        # 字体
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

        # 读取内容
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

        parsed_chapters = self._parse_chapters(content)
        print(f"  [i] 识别到 {len(parsed_chapters)} 个章节")
        
        epub_chapters = []
        for i, (chap_title, chap_body) in enumerate(parsed_chapters):
            file_name = f'chap_{i+1}.xhtml'
            c = epub.EpubHtml(title=chap_title, file_name=file_name, lang='zh-cn')
            c.add_item(css_item)
            lines = [f"<p>{line.strip()}</p>" for line in chap_body.splitlines() if line.strip()]
            c.content = f'<h1>{chap_title}</h1>' + "".join(lines)
            book.add_item(c)
            epub_chapters.append(c)

        book.toc = epub_chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + epub_chapters

        output_dir = os.path.dirname(epub_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try:
            epub.write_epub(epub_path, book, {})
            print(f"  [Success] 生成完毕: {os.path.basename(epub_path)}")
        except Exception as e:
            print(f"  [Error] 保存 EPUB 失败: {e}")