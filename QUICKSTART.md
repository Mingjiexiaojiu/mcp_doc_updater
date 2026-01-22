# Quick Start Guide

## Installation

1. Install the package:
```bash
pip install -e .
```

2. Verify installation:
```bash
python -c "import mcp_doc_updater; print(mcp_doc_updater.__version__)"
```

## Configuration

### Claude Desktop Setup

1. Open Claude Desktop configuration file:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Add the MCP server configuration:
```json
{
  "mcpServers": {
    "doc-updater": {
      "command": "python",
      "args": ["-m", "mcp_doc_updater.server"],
      "cwd": "E:\\Develop\\Project\\Demoidea\\mcp_doc_updater"
    }
  }
}
```

3. Restart Claude Desktop

## Usage

### Basic Usage

In Claude Desktop, ask:
```
请使用update_readme_changelog工具分析我的Git仓库变化并更新README
```

### With Parameters

```
请使用update_readme_changelog工具，参数如下：
- repo_path: /path/to/your/repo
- readme_path: README.md
- comparison_mode: latest_vs_previous
```

## Testing

Run tests:
```bash
pytest tests/
```

Run specific test:
```bash
python tests/test_basic.py
```

## Development

### Project Structure

```
mcp_doc_updater/
├── src/mcp_doc_updater/     # Source code
│   ├── server.py            # MCP server entry point
│   ├── git_analyzer.py      # Git analysis
│   ├── diff_filter.py       # Smart filtering
│   ├── changelog_generator.py  # Changelog generation
│   ├── markdown_updater.py  # Markdown updates
│   ├── models.py            # Data models
│   └── utils.py             # Utilities
├── tests/                   # Tests
├── examples/                # Example configs
└── pyproject.toml          # Project config
```

### Key Components

1. **GitAnalyzer**: Analyzes Git repository changes
2. **DiffFilter**: Filters and prioritizes changes
3. **ChangelogGenerator**: Generates Chinese changelog entries
4. **MarkdownUpdater**: Updates README files

## Troubleshooting

### Import Error

If you get `ModuleNotFoundError: No module named 'mcp_doc_updater'`:
```bash
pip install -e .
```

### MCP Module Not Found

If you get `ModuleNotFoundError: No module named 'mcp'`:
```bash
pip install mcp GitPython
```

### Git Repository Not Found

Ensure the `repo_path` parameter points to a valid Git repository.

### README Not Found

Ensure the `readme_path` parameter points to an existing file.

## Examples

### Example 1: Update from Latest Commit

```json
{
  "repo_path": "E:\\Develop\\Project\\Demoidea\\mcp_doc_updater",
  "readme_path": "README.md"
}
```

### Example 2: Update from Working Tree

```json
{
  "repo_path": "E:\\Develop\\Project\\Demoidea\\mcp_doc_updater",
  "readme_path": "README.md",
  "comparison_mode": "working_tree_vs_head"
}
```

### Example 3: Custom Heading

```json
{
  "repo_path": "E:\\Develop\\Project\\Demoidea\\mcp_doc_updater",
  "readme_path": "README.md",
  "heading_marker": "## 版本历史"
}
```

## Next Steps

1. Configure Claude Desktop with the MCP server
2. Test the tool with your own repository
3. Customize filter and markdown configurations
4. Explore advanced features like token budgets and smart summaries
