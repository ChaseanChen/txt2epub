# parser.py
import re
import logging
from typing import Iterator, Tuple

class TxtParser:
    """
    TXT 解析器
    职责：负责读取文本文件，识别编码，并以流(Stream)的形式逐章产出内容。
    解决痛点：使用生成器避免一次性加载大文件导致的内存溢出 (OOM)。
    """
    def __init__(self, file_path: str, encoding: str):
        self.file_path = file_path
        self.encoding = encoding
        # 预编译正则，匹配行首的章节名
        self.chapter_pattern = re.compile(
            r'^\s*(?:第[0-9零一二三四五六七八九十百千两]+[章节回卷部]|Chapter\s?\d+).*?$', 
            re.IGNORECASE
        )
        self.MAX_TITLE_LENGTH = 50

    def parse(self) -> Iterator[Tuple[str, str]]:
        """
        生成器方法：yield (title, content)
        """
        current_title = "序言/正文"
        buffer = []
        
        logging.info(f"开始解析文件 (流式): {self.file_path}")
        
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                for line in f:
                    stripped_line = line.strip()
                    # 只有非空行且匹配章节正则，且长度合理的才被认为是标题
                    if stripped_line and len(stripped_line) < self.MAX_TITLE_LENGTH and self.chapter_pattern.match(stripped_line):
                        # 遇到新章节，先吐出上一章节的内容（如果有的话）
                        if buffer:
                            yield current_title, "".join(buffer)
                        
                        # 重置状态
                        current_title = stripped_line
                        buffer = []
                    else:
                        buffer.append(line)
                
                # 循环结束，吐出最后一章
                if buffer:
                    yield current_title, "".join(buffer)
                    
        except Exception as e:
            logging.error(f"解析过程中断: {e}")
            raise e