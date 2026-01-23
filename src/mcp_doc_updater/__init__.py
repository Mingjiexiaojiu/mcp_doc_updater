"""MCP Doc Updater - A tool for generating prompts from Git changes for AI-powered changelog generation."""

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
from .prompt_generator import PromptGenerator

__all__ = [
    "ComparisonMode",
    "ChangeImportance",
    "ChangeType",
    "CodeChange",
    "GitAnalysisResult",
    "ChangelogEntry",
    "MarkdownUpdateConfig",
    "FilterConfig",
    "PromptGenerator",
]
