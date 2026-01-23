# txt2epub.py

import os
import re
from ebooklib import epub

class Kernel:
    def __init__(self):
        # 可以在这里初始化一些全局配置，目前留空即可
        pass
    
    def txt_to_epub(self, txt_path, epub_path, title, author, font_path=None):
        # --- 1. 基础检查 ---
        print("-" * 30)
        print(f"📂 输入文件: {txt_path}")
        print(f"📂 输出路径: {epub_path}")
        
        if not os.path.exists(txt_path):
            print(f"❌ 错误: 找不到输入文件 '{txt_path}'")
            return

        # 确保输出目录存在
        output_dir = os.path.dirname(epub_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"📁 已创建输出目录: {output_dir}")
            
        print(f"📖 正在初始化书籍信息: 《{title}》...")
        
        # --- 2. 创建书籍对象 ---
        book = epub.EpubBook()
        book.set_identifier('id_generated_by_kernel')
        book.set_title(title)
        book.set_language('zh-cn')
        book.add_author(author)
        
        # --- 3. 字体与样式处理 ---
        css_item = None
        if font_path and os.path.exists(font_path):
            print(f"🎨 检测到字体，正在嵌入: {os.path.basename(font_path)}")
            
            # 读取字体文件
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

            # 创建 CSS
            # 注意：我们将 CSS 放在 EPUB 根目录 ('style.css')，这样引用 'fonts/...' 才有效
            css_content = f'''
                @font-face {{
                    font-family: "MyFont";
                    src: url("{font_filename}");
                }}
                body, p, div {{
                    font-family: "MyFont", "PingFang SC", "Microsoft YaHei", sans-serif;
                    line-height: 1.8; /* 增加行高，阅读更舒适 */
                    text-align: justify;
                }}
                p {{
                    text-indent: 2em;
                    margin: 0.8em 0;
                }}
                h1 {{
                    font-family: "MyFont", sans-serif;
                    font-weight: bold;
                    text-align: center;
                    margin: 2em 0 1em 0;
                }}
            '''
            css_item = epub.EpubItem(
                uid="style_css",
                file_name="style.css", # 放在根目录，方便引用字体
                media_type="text/css",
                content=css_content
            )
            book.add_item(css_item)
            print("✅ 字体嵌入与样式配置完成。")
        else:
            if font_path:
                print(f"⚠️ 警告: 找不到字体文件 '{font_path}'，将跳过字体嵌入。")
                
        # --- 4. 读取文本内容 ---
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
                print("❌ 错误: 无法识别文件编码 (不是 UTF-8 也不是 GBK/GB18030)。")
                return
            
        # --- 5. 章节分析 ---
        print("🔍 正在分析章节结构...")
        # 优化正则：^\s* 兼容缩进，(?=第) 断言优化分割
        # split 会保留分割符在结果中（如果加了括号），这里我们用传统的分割方式
        pattern = re.compile(r'(^\s*第.{1,12}[章节回卷].*?$)', re.MULTILINE)
        parts = pattern.split(content)
        
        if len(parts) < 2:
            print("⚠️ 警告: 未匹配到标准章节格式。整本书将被视为一个章节。")
            # 如果匹配失败，手动构造一个单章节列表
            parts = ["", "正文", content] 
        
        chapters = []
        
        # 辅助函数：创建章节
        def create_chapter_item(title, content_text, file_name):
            c = epub.EpubHtml(title=title, file_name=file_name, lang='zh-cn')
            
            # 清洗段落：去除空白行，包裹 p 标签
            lines = [line.strip() for line in content_text.split('\n') if line.strip()]
            body_html = ''.join([f'<p>{line}</p>' for line in lines])
            
            c.content = f'<h1>{title}</h1>{body_html}'
            
            # 必须关联 CSS 才能生效
            if css_item:
                c.add_item(css_item)
                
            book.add_item(c)
            chapters.append(c)

        # 处理开头（序章/简介）
        if parts[0].strip():
            create_chapter_item("序言/简介", parts[0], "intro.xhtml")

        # 处理正文 (parts[1]是标题, parts[2]是内容, 以此类推)
        chapter_titles = parts[1::2]
        chapter_contents = parts[2::2]
        
        print(f"📊 识别到 {len(chapter_titles)} 个章节，开始打包...")

        for i, (chap_title, chap_content) in enumerate(zip(chapter_titles, chapter_contents)):
            # 简单的进度打印，防止大文件时以为卡死了
            if i % 100 == 0 and i > 0:
                print(f"   ...已处理 {i} 章")
            create_chapter_item(chap_title.strip(), chap_content, f'chap_{i+1}.xhtml')

        # --- 6. 生成目录与输出 ---
        book.toc = (chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # 设置阅读顺序
        book.spine = ['nav'] + chapters

        print(f"💾 正在写入文件: {epub_path}")
        try:
            epub.write_epub(epub_path, book, {})
            print("-" * 30)
            print(f"🎉 成功！Epub 已生成：\n   -> {epub_path}")
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")

if __name__ == "__main__":
    # 获取路径上下文
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    # 配置区
    TXT_FILENAME = '大乘期才有逆袭系统.txt'
    EPUB_FILENAME = '大乘期才有逆袭系统.epub'
    FONT_FILENAME = '字魂风华雅宋.ttf'
    
    BOOK_TITLE = '大乘期才有逆袭系统'
    BOOK_AUTHOR = '最白的乌鸦'
    
    # 拼接路径
    txt_file_path = os.path.join(project_root, 'input', TXT_FILENAME)
    epub_file_path = os.path.join(project_root, 'output', EPUB_FILENAME)
    font_file_path = os.path.join(project_root, 'fonts', FONT_FILENAME)
    
    # --- 修复点：实例化类并调用方法 ---
    app = Kernel()
    app.txt_to_epub(txt_file_path, epub_file_path, BOOK_TITLE, BOOK_AUTHOR, font_file_path)