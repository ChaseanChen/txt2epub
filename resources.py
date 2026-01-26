# resources.py
import os
import logging
from typing import Tuple, Optional
from ebooklib import epub

class ResourceManager:
    """
    资源管理器 (增强版)
    增加对图片文件的格式校验，避免因文件扩展名错误导致的程序崩溃或 EPUB 损坏。
    """
    def __init__(self, assets_dir: Optional[str], font_path: Optional[str] = None):
        self.assets_dir = assets_dir
        self.font_path = font_path
        self.default_font_family = "'PingFang SC', 'Microsoft YaHei', 'Heiti SC', STHeiti, sans-serif"

    def _validate_image(self, file_path: str) -> bool:
        """
        简单的 Magic Bytes 校验，不依赖 PIL，保持轻量级。
        确保文件是真实的 JPG 或 PNG。
        """
        try:
            if os.path.getsize(file_path) == 0:
                return False
            
            with open(file_path, 'rb') as f:
                header = f.read(8)
                
            # JPEG: FF D8 FF
            if header.startswith(b'\xff\xd8\xff'):
                return True
            # PNG: 89 50 4E 47 0D 0A 1A 0A
            if header.startswith(b'\x89PNG\r\n\x1a\n'):
                return True
            
            logging.warning(f"图片格式校验失败 (非标准 JPG/PNG 头): {file_path}")
            return False
        except Exception:
            return False

    def get_cover_image(self, txt_path: str) -> Tuple[Optional[str], Optional[bytes], Optional[str]]:
        base_dir = os.path.dirname(txt_path)
        file_basename = os.path.splitext(os.path.basename(txt_path))[0]
        # 扩展支持 webp (虽然 epub 标准支持有限，但防止报错)
        valid_exts = ['.jpg', '.jpeg', '.png']
        
        candidates = [
            os.path.join(base_dir, file_basename + ext) for ext in valid_exts
        ] + [
            os.path.join(base_dir, 'cover' + ext) for ext in valid_exts
        ]

        for img_path in candidates:
            if os.path.exists(img_path):
                if not self._validate_image(img_path):
                    logging.warning(f"跳过无效的封面文件: {img_path}")
                    continue
                
                try:
                    ext = os.path.splitext(img_path)[1].lower()
                    # 规范化扩展名，防止 .JPEG 这种
                    if ext == '.jpeg':
                        ext = '.jpg'
                    
                    with open(img_path, 'rb') as f:
                        content = f.read()
                        logging.info(f"已加载封面: {os.path.basename(img_path)}")
                        return f"cover{ext}", content, ext
                except Exception as e:
                    logging.warning(f"读取封面失败: {img_path}, 错误: {e}")
        
        return None, None, None

    def get_font_resource(self) -> Tuple[Optional[epub.EpubItem], str, str]:
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
            # 使用 UUID 避免 font-family 冲突，或者保持简单
            font_face_rule = f'@font-face {{ font-family: "CustomFont"; src: url("fonts/{font_filename}"); }}\n'
            css_font_family = '"CustomFont", sans-serif'
            logging.info(f"已加载字体: {font_filename}")
            return font_item, font_face_rule, css_font_family
        except Exception as e:
            logging.error(f"字体加载失败: {e}")
            return None, "", self.default_font_family

    def get_css(self, font_face_rule: str, font_family: str) -> epub.EpubItem:
        dynamic_css = f"""
        {font_face_rule}
        body {{ font-family: {font_family}; }}
        """
        static_css = self._get_fallback_css()
        
        if self.assets_dir:
            style_path = os.path.join(self.assets_dir, 'style.css')
            if os.path.exists(style_path):
                try:
                    with open(style_path, 'r', encoding='utf-8') as f:
                        static_css = f.read()
                except Exception as e:
                    logging.warning(f"外部样式表读取失败: {e}")

        final_css = dynamic_css + "\n" + static_css
        return epub.EpubItem(
            uid="style_css", 
            file_name="style.css", 
            media_type="text/css", 
            content=final_css
        )

    def _get_fallback_css(self) -> str:
        return '''
            body { line-height: 1.8; text-align: justify; margin: 0; padding: 0 10px; background-color: #fcfcfc; }
            p { text-indent: 2em; margin: 0 0 0.8em 0; font-size: 1em; }
            h1 { font-weight: bold; text-align: center; margin: 2em 0 1.5em 0; font-size: 1.6em; page-break-before: always; color: #333; }
            img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
            .scene-break { margin: 2em auto; text-align: center; color: #999; font-weight: bold; }
        '''