"""用于插入更新日志条目的 Markdown 文档更新器。"""

import re
from pathlib import Path
from typing import Optional, Tuple
from .models import ChangelogEntry, MarkdownUpdateConfig


class MarkdownUpdater:
    """使用更新日志条目更新 Markdown 文档。"""

    def __init__(self, config: Optional[MarkdownUpdateConfig] = None):
        """
        初始化 Markdown 更新器。

        Args:
            config: 可选配置
        """
        self.config = config or MarkdownUpdateConfig()

    def update_readme(
        self,
        file_path: str,
        entry: ChangelogEntry,
    ) -> Tuple[bool, str]:
        """
        使用新的更新日志条目更新 README 文件。

        Args:
            file_path: README 文件路径
            entry: 要插入的更新日志条目

        Returns:
            (成功标志, 消息) 元组
        """
        path = Path(file_path)

        # 检查文件是否存在
        if not path.exists():
            return False, f"File not found: {file_path}"

        # 读取当前内容
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"Failed to read file: {e}"

        # 查找标题位置
        position = self.find_heading_position(content, self.config.heading_marker)

        if position == -1:
            return False, f"Heading not found: {self.config.heading_marker}"

        # 插入条目
        new_content = self.insert_entry(content, position, entry)

        # 如果配置了最大条目数，则应用限制
        if self.config.max_entries:
            new_content = self._limit_entries(new_content, position)

        # 写回文件
        try:
            path.write_text(new_content, encoding="utf-8")
            return True, f"Successfully updated {file_path}"
        except Exception as e:
            return False, f"Failed to write file: {e}"

    def find_heading_position(self, content: str, heading: str) -> int:
        """
        查找 Markdown 标题的位置。

        Args:
            content: Markdown 内容
            heading: 要查找的标题（例如 "## 更新日志"）

        Returns:
            标题后的字符位置，如果未找到则返回 -1
        """
        # 转义标题中的特殊正则表达式字符
        escaped_heading = re.escape(heading)

        # 匹配标题的模式（带可选的尾随空白）
        pattern = rf'^{escaped_heading}\s*$'

        lines = content.split("\n")

        for i, line in enumerate(lines):
            if re.match(pattern, line.strip()):
                # 找到标题，返回此行之后的位置
                position = sum(len(l) + 1 for l in lines[:i+1])  # +1 表示换行符
                return position

        return -1

    def insert_entry(
        self,
        content: str,
        position: int,
        entry: ChangelogEntry,
    ) -> str:
        """
        在指定位置插入更新日志条目。

        Args:
            content: 原始内容
            position: 插入位置
            entry: 更新日志条目

        Returns:
            更新后的内容
        """
        # 将条目格式化为 Markdown
        entry_text = entry.to_markdown()

        # 确定插入文本
        if self.config.insert_at_top:
            # 在顶部插入（紧接标题之后）
            # 如果内容不以空行开头，则在条目前添加空行
            if position < len(content) and content[position] != "\n":
                insertion = f"\n{entry_text}\n"
            else:
                insertion = f"{entry_text}\n"
        else:
            # 在底部插入（在下一个标题或末尾之前）
            insertion = f"{entry_text}\n"

        # 插入条目
        new_content = content[:position] + insertion + content[position:]

        return new_content

    def _limit_entries(self, content: str, heading_position: int) -> str:
        """
        限制更新日志条目的数量。

        Args:
            content: 包含条目的内容
            heading_position: 更新日志标题的位置

        Returns:
            限制条目后的内容
        """
        if not self.config.max_entries:
            return content

        # 查找标题后的所有条目
        lines = content[heading_position:].split("\n")

        # 匹配更新日志条目的模式（日期格式：YYYY年MM月DD日）
        entry_pattern = r'^\d{4}年\d{2}月\d{2}日\s+'

        entry_lines = []
        other_lines = []
        entry_count = 0

        for line in lines:
            if re.match(entry_pattern, line):
                entry_count += 1
                if entry_count <= self.config.max_entries:
                    entry_lines.append(line)
            else:
                # 检查是否已经过了所有条目
                if entry_count > 0 and not re.match(entry_pattern, line):
                    # 这是条目之后的内容
                    other_lines.append(line)
                elif entry_count == 0:
                    # 这是第一个条目之前的内容
                    entry_lines.append(line)

        # 重构内容
        new_section = "\n".join(entry_lines)
        if other_lines:
            new_section += "\n" + "\n".join(other_lines)

        return content[:heading_position] + new_section

    def create_changelog_section(self, heading: Optional[str] = None) -> str:
        """
        创建新的更新日志部分。

        Args:
            heading: 可选的自定义标题

        Returns:
            更新日志部分的 Markdown 文本
        """
        heading = heading or self.config.heading_marker
        return f"{heading}\n\n"

    def append_to_file(
        self,
        file_path: str,
        entry: ChangelogEntry,
    ) -> Tuple[bool, str]:
        """
        将更新日志条目追加到文件末尾。

        Args:
            file_path: 文件路径
            entry: 更新日志条目

        Returns:
            (成功标志, 消息) 元组
        """
        path = Path(file_path)

        try:
            # 读取现有内容
            if path.exists():
                content = path.read_text(encoding="utf-8")
            else:
                content = ""

            # 追加条目
            if content and not content.endswith("\n"):
                content += "\n"

            content += entry.to_markdown() + "\n"

            # 写回
            path.write_text(content, encoding="utf-8")

            return True, f"Successfully appended to {file_path}"

        except Exception as e:
            return False, f"Failed to append to file: {e}"

    def validate_markdown(self, content: str) -> Tuple[bool, str]:
        """
        验证 Markdown 内容。

        Args:
            content: Markdown 内容

        Returns:
            (是否有效, 消息) 元组
        """
        # 检查基本的 Markdown 结构
        if not content.strip():
            return False, "Content is empty"

        # 检查至少有一个标题
        if not re.search(r'^#+\s+', content, re.MULTILINE):
            return False, "No headings found"

        return True, "Valid markdown"
