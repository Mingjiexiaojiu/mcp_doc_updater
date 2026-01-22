"""Tests for MCP Doc Updater."""

import pytest
from pathlib import Path


def test_imports():
    """Test that all modules can be imported."""
    from mcp_doc_updater import (
        ComparisonMode,
        ChangeImportance,
        ChangeType,
        CodeChange,
        GitAnalysisResult,
        ChangelogEntry,
        MarkdownUpdateConfig,
        FilterConfig,
    )

    assert ComparisonMode.LATEST_VS_PREVIOUS is not None
    assert ChangeImportance.CRITICAL is not None
    assert ChangeType.ADDED is not None


def test_changelog_entry_format():
    """Test changelog entry formatting."""
    from datetime import datetime
    from mcp_doc_updater.models import ChangelogEntry

    entry = ChangelogEntry(
        date=datetime(2026, 1, 22),
        content="测试内容",
        commit_hash="abc123",
        author="Test Author",
    )

    assert entry.format_chinese_date() == "2026年01月22日"
    assert entry.to_markdown() == "2026年01月22日  测试内容"


def test_filter_config_defaults():
    """Test filter config defaults."""
    from mcp_doc_updater.models import FilterConfig, ChangeImportance

    config = FilterConfig()

    assert config.ignore_whitespace is True
    assert config.min_importance == ChangeImportance.NORMAL
    assert config.max_context_lines == 3
    assert len(config.ignore_patterns) > 0


def test_markdown_config_defaults():
    """Test markdown config defaults."""
    from mcp_doc_updater.models import MarkdownUpdateConfig

    config = MarkdownUpdateConfig()

    assert config.heading_marker == "## 更新日志"
    assert config.insert_at_top is True
    assert config.preserve_formatting is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
