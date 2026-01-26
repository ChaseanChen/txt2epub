# parser.py
import re
import logging
from typing import Iterator, Tuple

class TxtParser:
    """
    TXT 解析器 (优化版)
    1. 保持流式读取，节省内存。
    2. 增加标题去重逻辑（去除正文开头重复的章节名）。
    3. 增加单章最大行数限制，防止正则失效导致内存溢出。
    """
    def __init__(self, file_path: str, encoding: str):
        self.file_path = file_path
        self.encoding = encoding
        
        # 优化正则：增加对常见卷标、序章的兼容
        self.chapter_pattern = re.compile(
            r'^\s*(?:第[0-9零一二三四五六七八九十百千两]+[章节回卷部集]|Chapter\s?\d+|序章|楔子|尾声).*?$', 
            re.IGNORECASE
        )
        self.MAX_TITLE_LENGTH = 60
        # 安全限制：如果一章超过 10000 行，强制截断，防止内存溢出
        self.MAX_LINES_PER_CHAPTER = 10000 

    def _clean_duplicate_title(self, title: str, content_lines: list) -> str:
        """
        移除正文开头与标题重复的行
        """
        if not content_lines:
            return ""

        # 预处理标题：去除空格和标点，用于模糊比对
        clean_title = re.sub(r'\s+|[：:,\.，。]', '', title)
        
        # 检查前 3 行（有时会有空行）
        check_range = min(len(content_lines), 3)
        # start_idx = 0
        
        for i in range(check_range):
            line = content_lines[i].strip()
            if not line:
                continue
            
            # 预处理行内容
            clean_line = re.sub(r'\s+|[：:,\.，。]', '', line)
            
            # 判定重复：如果正文行 完全包含 标题，或者 标题 完全包含 正文行(且正文行长度足够长)
            # 例如 Title="第一章 启程", Line="第一章 启程" -> 移除
            if clean_title == clean_line or (len(clean_line) > 2 and clean_title in clean_line):
                # 标记该行及之前的空行为待删除
                # 这里简单策略：只删除匹配到的这一行，之前的空行由 HTML 渲染器处理
                content_lines[i] = "" # 也就是这一行置空
                logging.debug(f"已移除重复标题行: {line}")
                break # 只移除第一次出现的标题

        return "".join(content_lines)

    def parse(self) -> Iterator[Tuple[str, str]]:
        current_title = "序言"
        buffer = []
        
        logging.info(f"开始解析文件: {self.file_path}")
        
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                for line_idx, line in enumerate(f):
                    stripped_line = line.strip()
                    
                    # 1. 判定是否为新章节
                    is_new_chapter = False
                    if stripped_line and len(stripped_line) < self.MAX_TITLE_LENGTH:
                        if self.chapter_pattern.match(stripped_line):
                            is_new_chapter = True

                    # 2. 如果是新章节，或者缓冲区过大（安全强制切分）
                    if is_new_chapter or len(buffer) >= self.MAX_LINES_PER_CHAPTER:
                        # 吐出上一章
                        if buffer:
                            cleaned_content = self._clean_duplicate_title(current_title, buffer)
                            yield current_title, cleaned_content
                        
                        # 如果是因为缓冲区满了强制切分的，不更新标题，只清空 buffer
                        if not is_new_chapter:
                            logging.warning(f"章节过长 (>{self.MAX_LINES_PER_CHAPTER}行)，强制切分章节。")
                            # 延续上一章标题，或者加个后缀
                            current_title = f"{current_title} (续)"
                            buffer = [line] # 当前行归入下一段
                        else:
                            # 正常新章节
                            current_title = stripped_line
                            buffer = []
                    else:
                        buffer.append(line)
                
                # 3. 文件结束，吐出最后一章
                if buffer:
                    cleaned_content = self._clean_duplicate_title(current_title, buffer)
                    yield current_title, cleaned_content
                    
        except Exception as e:
            logging.error(f"解析文件流时发生错误: {e}")
            # 即使报错，如果 buffer 有内容，最好也吐出来，避免数据完全丢失
            if buffer:
                yield current_title, "".join(buffer)
            raise e