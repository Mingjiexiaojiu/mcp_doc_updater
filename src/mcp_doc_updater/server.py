"""MCP 文档更新工具的服务器。"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field

from .git_analyzer import GitAnalyzer
from .diff_filter import DiffFilter
from .prompt_generator import PromptGenerator
from .models import (
    ComparisonMode,
    FilterConfig,
    ChangeImportance,
)
from .utils import auto_detect_paths, auto_detect_comparison_mode


# 工具输入模型
class GenerateChangelogPromptInput(BaseModel):
    """generate_changelog_prompt 工具的输入。"""
    repo_path: Optional[str] = Field(
        default=None,
        description="Git 仓库路径（如果未提供则自动检测）"
    )
    comparison_mode: Optional[str] = Field(
        default=None,
        description="比较模式（如果未提供则自动检测）：latest_vs_previous、working_tree_vs_head 或 latest_vs_tag"
    )
    filter_trivial: bool = Field(
        default=True,
        description="是否过滤掉琐碎的变化"
    )
    include_diff: bool = Field(
        default=True,
        description="是否在提示词中包含 diff 内容"
    )
    language: str = Field(
        default="zh",
        description="提示词语言：'zh' (中文) 或 'en' (英文)"
    )
    tag_name: Optional[str] = Field(
        default=None,
        description="latest_vs_tag 模式的标签名称"
    )
    token_budget: Optional[int] = Field(
        default=None,
        description="差异分析的可选 token 预算"
    )
    max_diff_lines: int = Field(
        default=50,
        description="每个文件包含的最大 diff 行数"
    )


# 创建 MCP 服务器
app = Server("mcp-doc-updater")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用的工具。"""
    return [
        Tool(
            name="generate_changelog_prompt",
            description=(
                "分析 Git 代码变化并生成用于 AI 的提示词，用于生成更新日志。"
                "自动检测：Git 仓库路径、比较模式。"
                "比较模式逻辑：如果工作树有未提交的变化，使用 'working_tree_vs_head'；"
                "如果工作树干净，使用 'latest_vs_previous'。"
                "智能提取关键变化，过滤琐碎修改，"
                "并生成结构化的提示词，包含代码变化摘要、详细信息和 diff 内容。"
                "返回的提示词可以直接发送给 AI 模型来生成更新日志条目。"
            ),
            inputSchema=GenerateChangelogPromptInput.model_json_schema(),
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用。"""
    if name == "generate_changelog_prompt":
        return await handle_generate_changelog_prompt(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_generate_changelog_prompt(arguments: dict) -> list[TextContent]:
    """
    处理 generate_changelog_prompt 工具调用。

    参数:
        arguments: 工具参数

    返回:
        包含提示词的 TextContent 列表
    """
    try:
        # 解析并验证输入
        input_data = GenerateChangelogPromptInput(**arguments)

        # 如果未提供则自动检测仓库路径
        if not input_data.repo_path:
            detected_repo, _ = auto_detect_paths()

            if detected_repo:
                input_data.repo_path = str(detected_repo)
            else:
                return [TextContent(
                    type="text",
                    text="错误：无法自动检测 Git 仓库。请提供 repo_path 参数。"
                )]

        # 解析路径
        repo_path = Path(input_data.repo_path).resolve()
        if not repo_path.exists():
            return [TextContent(
                type="text",
                text=f"错误：仓库路径不存在：{repo_path}"
            )]

        # 如果未提供则自动检测比较模式
        if not input_data.comparison_mode:
            input_data.comparison_mode = auto_detect_comparison_mode(repo_path)

        # 解析比较模式
        try:
            comparison_mode = ComparisonMode(input_data.comparison_mode)
        except ValueError:
            return [TextContent(
                type="text",
                text=f"错误：无效的比较模式：{input_data.comparison_mode}"
            )]

        # 配置过滤器
        filter_config = FilterConfig(
            min_importance=ChangeImportance.NORMAL if input_data.filter_trivial else ChangeImportance.TRIVIAL,
            token_budget=input_data.token_budget,
        )

        # 步骤 1：分析 Git 变化
        analyzer = GitAnalyzer(str(repo_path), filter_config)
        analysis = analyzer.analyze_changes(
            mode=comparison_mode,
            tag_name=input_data.tag_name,
        )

        if not analysis.changes:
            return [TextContent(
                type="text",
                text="未检测到重要变化。"
            )]

        # 步骤 2：过滤变化
        diff_filter = DiffFilter(filter_config)
        filtered_changes = diff_filter.filter_changes(analysis.changes)

        if not filtered_changes:
            return [TextContent(
                type="text",
                text="过滤后没有重要变化。"
            )]

        # 使用过滤后的变化更新分析
        analysis.changes = filtered_changes

        # 步骤 3：生成提示词
        generator = PromptGenerator(max_diff_lines=input_data.max_diff_lines)
        prompt = generator.generate_from_analysis(
            analysis,
            include_diff=input_data.include_diff,
            language=input_data.language,
        )

        # 返回提示词
        return [TextContent(
            type="text",
            text=prompt
        )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"错误：{str(e)}\n\n请检查您的输入参数并重试。"
        )]


def main():
    """MCP 服务器的主入口点。"""
    import mcp.server.stdio

    # 运行服务器
    asyncio.run(mcp.server.stdio.stdio_server(app))


if __name__ == "__main__":
    main()
