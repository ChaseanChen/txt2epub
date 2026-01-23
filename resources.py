# resources.py
import os
# import uuid
import logging
from typing import Tuple, Optional
from ebooklib import epub

class ResourceManager:
    """
    资源管理器
    职责：处理封面、字体、CSS 等静态资源的加载与生成。
    """
    def __init__(self, assets_dir: Optional[str], font_path: Optional[str] = None):
        self.assets_dir = assets_dir
        self.font_path = font_path
        self.default_font_family = "'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif"

    def get_cover_image(self, txt_path: str) -> Tuple[Optional[str], Optional[bytes], Optional[str]]:
        """
        查找封面。
        返回: (文件名, 二进制内容, 扩展名)
        """
        base_dir = os.path.dirname(txt_path)
        file_basename = os.path.splitext(os.path.basename(txt_path))[0]
        valid_exts = ['.jpg', '.jpeg', '.png']
        
        candidates = [
            os.path.join(base_dir, file_basename + ext) for ext in valid_exts
        ] + [
            os.path.join(base_dir, 'cover' + ext) for ext in valid_exts
        ]

        for img_path in candidates:
            if os.path.exists(img_path):
                try:
                    ext = os.path.splitext(img_path)[1]
                    with open(img_path, 'rb') as f:
                        return f"cover{ext}", f.read(), ext
                except Exception as e:
                    logging.warning(f"封面存在但读取失败: {img_path}, 错误: {e}")
        
        return None, None, None

    def get_font_resource(self) -> Tuple[Optional[epub.EpubItem], str, str]:
        """
        处理字体。
        返回: (EpubItem对象, CSS中的@font-face规则, CSS中的font-family设置)
        """
        if not self.font_path or not os.path.exists(self.font_path):
            return None, "", self.default_font_family

        font_filename = os.path.basename(self.font_path)
        try:
            with open(self.font_path, 'rb') as f:
                font_item = epub.EpubItem(
                    uid="custom_font",
                    file_name=f"fonts/{font_filename}",
                    media_type="application/x-font-ttf",
                    content=f.read()
                )
            font_face_rule = f'@font-face {{ font-family: "CustomFont"; src: url("fonts/{font_filename}"); }}\n'
            css_font_family = '"CustomFont", sans-serif'
            logging.info(f"已加载字体: {font_filename}")
            return font_item, font_face_rule, css_font_family
        except Exception as e:
            logging.error(f"字体加载失败: {e}")
            return None, "", self.default_font_family

    def get_css(self, font_face_rule: str, font_family: str) -> epub.EpubItem:
        """生成最终的 CSS Item"""
        # 1. 动态部分
        dynamic_css = f"""
        {font_face_rule}
        body {{ font-family: {font_family}; }}
        """

        # 2. 静态部分 (从 assets 读取)
        static_css = self._get_fallback_css()
        if self.assets_dir:
            style_path = os.path.join(self.assets_dir, 'style.css')
            if os.path.exists(style_path):
                try:
                    with open(style_path, 'r', encoding='utf-8') as f:
                        static_css = f.read()
                except Exception as e:
                    logging.warning(f"外部样式表读取失败，使用默认值: {e}")

        final_css = dynamic_css + "\n" + static_css
        return epub.EpubItem(
            uid="style_css", 
            file_name="style.css", 
            media_type="text/css", 
            content=final_css
        )

    def _get_fallback_css(self) -> str:
        return '''
            body { line-height: 1.8; text-align: justify; margin: 0 5px; background-color: #fcfcfc; }
            p { text-indent: 2em; margin: 0.8em 0; font-size: 1em; }
            h1 { font-weight: bold; text-align: center; margin: 2em 0 1em 0; font-size: 1.6em; page-break-before: always; color: #333; }
            img { max-width: 100%; height: auto; }
        '''