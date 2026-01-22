"""MCP Doc Updater 的数据模型。"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ComparisonMode(str, Enum):
    """Git 比较模式。"""
    LATEST_VS_PREVIOUS = "latest_vs_previous"
    WORKING_TREE_VS_HEAD = "working_tree_vs_head"
    LATEST_VS_TAG = "latest_vs_tag"


class ChangeImportance(str, Enum):
    """代码变化的重要性级别。"""
    CRITICAL = "critical"      # 新函数、类、重大逻辑变化
    IMPORTANT = "important"    # 重要修改、bug 修复
    NORMAL = "normal"          # 常规变化
    TRIVIAL = "trivial"        # 空白、注释、格式化


class ChangeType(str, Enum):
    """代码变化的类型。"""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class CodeChange(BaseModel):
    """表示单个代码变化。"""
    file_path: str
    change_type: ChangeType
    importance: ChangeImportance
    diff_text: str
    summary: Optional[str] = None
    line_count: int = 0

    # 提取的语义信息
    functions_added: List[str] = Field(default_factory=list)
    functions_modified: List[str] = Field(default_factory=list)
    functions_deleted: List[str] = Field(default_factory=list)
    classes_added: List[str] = Field(default_factory=list)
    classes_modified: List[str] = Field(default_factory=list)


class GitAnalysisResult(BaseModel):
    """Git 分析的结果。"""
    comparison_mode: ComparisonMode
    changes: List[CodeChange]
    total_files_changed: int
    total_lines_added: int = 0
    total_lines_deleted: int = 0
    summary: str
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    author: Optional[str] = None
    timestamp: Optional[datetime] = None


class ChangelogEntry(BaseModel):
    """单个更新日志条目。"""
    date: datetime
    content: str
    commit_hash: Optional[str] = None
    author: Optional[str] = None

    def format_chinese_date(self) -> str:
        """格式化日期为中文格式：2026年01月22日"""
        return self.date.strftime("%Y年%m月%d日")

    def to_markdown(self) -> str:
        """转换为 markdown 格式。"""
        date_str = self.format_chinese_date()
        return f"{date_str}  {self.content}"


class MarkdownUpdateConfig(BaseModel):
    """Markdown 更新的配置。"""
    heading_marker: str = "## 更新日志"
    max_entries: Optional[int] = None
    insert_at_top: bool = True
    preserve_formatting: bool = True


class FilterConfig(BaseModel):
    """差异过滤的配置。"""
    ignore_whitespace: bool = True
    ignore_comments: bool = False
    ignore_imports: bool = False
    min_importance: ChangeImportance = ChangeImportance.NORMAL
    max_context_lines: int = 3
    token_budget: Optional[int] = None

    # 要忽略的文件模式
    ignore_patterns: List[str] = Field(default_factory=lambda: [
        "*.lock",
        "*.log",
        "*.pyc",
        "__pycache__/*",
        ".git/*",
        ".idea/*",
        ".vscode/*",
        "node_modules/*",
        "*.min.js",
        "*.min.css",
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
    ])
