"""MCP Doc Updater - A tool for updating README changelogs based on Git changes."""

__version__ = "0.1.0"

from .models import (
    ComparisonMode,
    ChangeImportance,
    ChangeType,
    CodeChange,
    GitAnalysisResult,
    ChangelogEntry,
    MarkdownUpdateConfig,
    FilterConfig,
)

__all__ = [
    "ComparisonMode",
    "ChangeImportance",
    "ChangeType",
    "CodeChange",
    "GitAnalysisResult",
    "ChangelogEntry",
    "MarkdownUpdateConfig",
    "FilterConfig",
]
