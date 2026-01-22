"""Data models for MCP Doc Updater."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ComparisonMode(str, Enum):
    """Git comparison modes."""
    LATEST_VS_PREVIOUS = "latest_vs_previous"
    WORKING_TREE_VS_HEAD = "working_tree_vs_head"
    LATEST_VS_TAG = "latest_vs_tag"


class ChangeImportance(str, Enum):
    """Importance level of code changes."""
    CRITICAL = "critical"      # New functions, classes, major logic changes
    IMPORTANT = "important"    # Significant modifications, bug fixes
    NORMAL = "normal"          # Regular changes
    TRIVIAL = "trivial"        # Whitespace, comments, formatting


class ChangeType(str, Enum):
    """Type of code change."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class CodeChange(BaseModel):
    """Represents a single code change."""
    file_path: str
    change_type: ChangeType
    importance: ChangeImportance
    diff_text: str
    summary: Optional[str] = None
    line_count: int = 0

    # Extracted semantic information
    functions_added: List[str] = Field(default_factory=list)
    functions_modified: List[str] = Field(default_factory=list)
    functions_deleted: List[str] = Field(default_factory=list)
    classes_added: List[str] = Field(default_factory=list)
    classes_modified: List[str] = Field(default_factory=list)


class GitAnalysisResult(BaseModel):
    """Result of Git analysis."""
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
    """A single changelog entry."""
    date: datetime
    content: str
    commit_hash: Optional[str] = None
    author: Optional[str] = None

    def format_chinese_date(self) -> str:
        """Format date in Chinese format: 2026年01月22日"""
        return self.date.strftime("%Y年%m月%d日")

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        date_str = self.format_chinese_date()
        return f"{date_str}  {self.content}"


class MarkdownUpdateConfig(BaseModel):
    """Configuration for markdown updates."""
    heading_marker: str = "## 更新日志"
    max_entries: Optional[int] = None
    insert_at_top: bool = True
    preserve_formatting: bool = True


class FilterConfig(BaseModel):
    """Configuration for diff filtering."""
    ignore_whitespace: bool = True
    ignore_comments: bool = False
    ignore_imports: bool = False
    min_importance: ChangeImportance = ChangeImportance.NORMAL
    max_context_lines: int = 3
    token_budget: Optional[int] = None

    # File patterns to ignore
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
