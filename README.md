# MCP Doc Updater

一个基于MCP (Model Context Protocol) 的智能文档更新工具，能够自动分析Git代码变化并生成用于AI的提示词，让AI帮你生成更新日志。

## 特性

- 🔍 **智能代码分析**: 自动分析Git仓库的代码变化，识别关键修改
- 🎯 **智能过滤**: 三层过滤机制，过滤掉空白、注释等琐碎变化，只保留重要修改
- 📊 **Token优化**: 智能压缩diff内容，减少token使用，提高效率
- 🤖 **AI提示词生成**: 生成结构化的提示词，包含代码变化摘要、详细信息和diff内容
- 🌐 **多语言支持**: 支持中文和英文提示词生成
- 🔄 **多种比较模式**: 支持最新commit对比、工作区对比、tag对比等多种模式
- 🎨 **语义识别**: 自动识别函数、类的新增、修改和删除

## 安装

### 前置要求

- Python 3.10 或更高版本
- Git

### 安装步骤

1. 克隆仓库:
```bash
git clone <repository-url>
cd mcp_doc_updater
```

2. 安装依赖:
```bash
pip install -e .
```

或者使用开发模式（包含测试工具）:
```bash
pip install -e ".[dev]"
```

## 使用方法

### 作为MCP工具使用

MCP Doc Updater 主要设计为MCP工具，可以在Claude Desktop或其他支持MCP的应用中使用。

#### 配置Claude Desktop

在Claude Desktop的配置文件中添加以下内容：

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

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

#### 在Claude中使用

配置完成后，在Claude Desktop中可以直接调用工具：

```
请使用generate_changelog_prompt工具分析我的代码变化
```

工具会返回一个结构化的提示词，你可以将这个提示词发送给AI来生成更新日志内容。

### 工具参数

`generate_changelog_prompt` 工具支持以下参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `repo_path` | string | 自动检测 | Git仓库路径（可选，自动检测当前目录） |
| `comparison_mode` | string | 自动检测 | 比较模式 |
| `filter_trivial` | boolean | `true` | 是否过滤琐碎变化 |
| `include_diff` | boolean | `true` | 是否在提示词中包含diff内容 |
| `language` | string | `zh` | 提示词语言（'zh'或'en'） |
| `tag_name` | string | `null` | Tag名称（用于latest_vs_tag模式） |
| `token_budget` | integer | `null` | Token预算限制 |
| `max_diff_lines` | integer | `50` | 每个文件包含的最大diff行数 |

**自动检测功能：**
- 如果不提供 `repo_path`，工具会自动向上搜索 `.git` 目录来定位仓库
- 如果不提供 `comparison_mode`，工具会根据工作区状态自动选择合适的比较模式

#### 比较模式

- `latest_vs_previous`: 比较最新commit和上一个commit（默认）
- `working_tree_vs_head`: 比较工作区和HEAD
- `latest_vs_tag`: 比较最新commit和指定tag

### 使用示例

#### 示例1: 基本使用（自动检测）

在 Claude Desktop 中直接调用，无需提供任何参数：

```
请使用generate_changelog_prompt工具分析代码变化
```

或者使用空的 JSON：
```json
{}
```

工具会自动检测当前 Git 仓库，并返回一个提示词。

#### 示例2: 手动指定路径

```json
{
  "repo_path": "/path/to/your/repo"
}
```

#### 示例3: 生成英文提示词

```json
{
  "language": "en"
}
```

#### 示例4: 比较工作区变化

```json
{
  "comparison_mode": "working_tree_vs_head"
}
```

#### 示例5: 不包含diff内容

```json
{
  "include_diff": false
}
```

#### 示例6: 限制Token使用

```json
{
  "repo_path": "/path/to/your/repo",
  "token_budget": 2000,
  "max_diff_lines": 30
}
```

## 工作原理

### 1. Git分析

工具使用GitPython分析代码变化，支持多种比较模式：
- 提取文件变化列表
- 获取diff内容
- 识别变化类型（新增、修改、删除、重命名）

### 2. 智能过滤

三层过滤机制确保只保留重要变化：

**第一层：文件级过滤**
- 忽略配置文件、日志文件、锁文件
- 忽略IDE配置目录
- 忽略依赖目录

**第二层：行级过滤**
- 过滤空白行变化
- 过滤纯注释行变化
- 过滤import语句变化（可配置）

**第三层：语义识别**
- 识别函数定义、类定义
- 评估变化重要性（CRITICAL > IMPORTANT > NORMAL > TRIVIAL）
- 只保留达到阈值的变化

### 3. Token优化

- 按重要性排序变化
- 压缩diff上下文（只保留前后3行）
- 在token预算内截断
- 生成紧凑摘要

### 4. 提示词生成

根据分析结果生成结构化的提示词：
- 包含任务说明和要求
- 提供基本信息（比较模式、文件数、行数等）
- 生成代码变化摘要统计
- 列出详细变化列表（文件路径、变化类型、重要性等）
- 可选包含diff内容
- 提供输出格式示例
- 支持中文和英文两种语言

### 5. AI生成更新日志

将生成的提示词发送给AI模型（如Claude），AI会根据提示词中的信息生成简洁、用户友好的更新日志条目。

## 配置

### 过滤配置

可以通过`FilterConfig`自定义过滤行为：

```python
from mcp_doc_updater.models import FilterConfig, ChangeImportance

config = FilterConfig(
    ignore_whitespace=True,
    ignore_comments=False,
    ignore_imports=False,
    min_importance=ChangeImportance.NORMAL,
    max_context_lines=3,
    token_budget=2000,
    ignore_patterns=[
        "*.lock",
        "*.log",
        "__pycache__/*",
        ".git/*",
    ]
)
```

### Markdown配置

可以通过`MarkdownUpdateConfig`自定义Markdown更新行为：

```python
from mcp_doc_updater.models import MarkdownUpdateConfig

config = MarkdownUpdateConfig(
    heading_marker="## 更新日志",
    max_entries=10,
    insert_at_top=True,
    preserve_formatting=True,
)
```

## 项目结构

```
mcp_doc_updater/
├── src/
│   └── mcp_doc_updater/
│       ├── __init__.py              # 包初始化
│       ├── server.py                # MCP服务器主入口
│       ├── git_analyzer.py          # Git差异分析
│       ├── diff_filter.py           # 智能差异过滤
│       ├── prompt_generator.py      # 提示词生成
│       ├── markdown_updater.py      # Markdown文档更新（保留）
│       ├── models.py                # 数据模型
│       └── utils.py                 # 工具函数
├── tests/                           # 测试目录
├── examples/                        # 示例配置
├── pyproject.toml                   # 项目配置
├── README.md                        # 项目文档
└── .gitignore                       # Git忽略文件
```

## 开发

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black src/
```

### 类型检查

```bash
mypy src/
```

## 技术栈

- **MCP SDK**: Model Context Protocol Python SDK
- **GitPython**: Git操作库
- **Pydantic**: 数据验证和模型
- **python-dateutil**: 日期处理

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 更新日志

2026年01月22日  重构项目架构，将更新日志生成改为提示词生成，支持AI辅助生成更新日志；新增多语言支持（中文/英文） 

2026年01月22日  项目成立，实现基础MCP服务器框架和核心功能模块
