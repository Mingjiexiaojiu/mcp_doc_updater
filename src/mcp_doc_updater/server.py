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
from .changelog_generator import ChangelogGenerator
from .markdown_updater import MarkdownUpdater
from .models import (
    ComparisonMode,
    FilterConfig,
    MarkdownUpdateConfig,
    ChangeImportance,
)
from .utils import auto_detect_paths, find_changelog_heading, auto_detect_comparison_mode


# 工具输入模型
class UpdateReadmeChangelogInput(BaseModel):
    """update_readme_changelog 工具的输入。"""
    repo_path: Optional[str] = Field(
        default=None,
        description="Git 仓库路径（如果未提供则自动检测）"
    )
    readme_path: Optional[str] = Field(
        default=None,
        description="README 文件路径（如果未提供则自动检测，相对于仓库或绝对路径）"
    )
    comparison_mode: Optional[str] = Field(
        default=None,
        description="比较模式（如果未提供则自动检测）：latest_vs_previous、working_tree_vs_head 或 latest_vs_tag"
    )
    heading_marker: Optional[str] = Field(
        default=None,
        description="插入更新日志的 Markdown 标题（如果未提供则自动检测）"
    )
    filter_trivial: bool = Field(
        default=True,
        description="是否过滤掉琐碎的变化"
    )
    use_smart_summary: bool = Field(
        default=True,
        description="是否从代码分析生成智能摘要"
    )
    tag_name: Optional[str] = Field(
        default=None,
        description="latest_vs_tag 模式的标签名称"
    )
    token_budget: Optional[int] = Field(
        default=None,
        description="差异分析的可选 token 预算"
    )


# 创建 MCP 服务器
app = Server("mcp-doc-updater")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用的工具。"""
    return [
        Tool(
            name="update_readme_changelog",
            description=(
                "分析 Git 代码变化并更新 README 更新日志，具有完整的自动检测功能。"
                "自动检测：Git 仓库路径、README 文件位置、更新日志标题和比较模式。"
                "比较模式逻辑：如果工作树有未提交的变化，使用 'working_tree_vs_head'；"
                "如果工作树干净，使用 'latest_vs_previous'。"
                "智能提取关键变化，过滤琐碎修改，"
                "并生成中文更新日志条目，格式为：YYYY年MM月DD日  内容。"
                "所有参数都是可选的，如果未提供将自动检测。"
            ),
            inputSchema=UpdateReadmeChangelogInput.model_json_schema(),
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用。"""
    if name == "update_readme_changelog":
        return await handle_update_readme_changelog(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_update_readme_changelog(arguments: dict) -> list[TextContent]:
    """
    处理 update_readme_changelog 工具调用。

    参数:
        arguments: 工具参数

    返回:
        包含结果的 TextContent 列表
    """
    try:
        # 解析并验证输入
        input_data = UpdateReadmeChangelogInput(**arguments)

        # 如果未提供则自动检测路径
        if not input_data.repo_path or not input_data.readme_path:
            detected_repo, detected_readme = auto_detect_paths()

            if not input_data.repo_path:
                if detected_repo:
                    input_data.repo_path = str(detected_repo)
                else:
                    return [TextContent(
                        type="text",
                        text="错误：无法自动检测 Git 仓库。请提供 repo_path 参数。"
                    )]

            if not input_data.readme_path:
                if detected_readme:
                    input_data.readme_path = str(detected_readme)
                else:
                    return [TextContent(
                        type="text",
                        text="错误：无法自动检测 README 文件。请提供 readme_path 参数。"
                    )]

        # 解析路径
        repo_path = Path(input_data.repo_path).resolve()
        if not repo_path.exists():
            return [TextContent(
                type="text",
                text=f"错误：仓库路径不存在：{repo_path}"
            )]

        # 解析 README 路径
        readme_path = Path(input_data.readme_path)
        if not readme_path.is_absolute():
            readme_path = repo_path / readme_path
        readme_path = readme_path.resolve()

        if not readme_path.exists():
            return [TextContent(
                type="text",
                text=f"错误：README 文件不存在：{readme_path}"
            )]

        # 如果未提供则自动检测标题标记
        if not input_data.heading_marker:
            detected_heading = find_changelog_heading(readme_path)
            if detected_heading:
                input_data.heading_marker = detected_heading
            else:
                # 使用默认中文标题
                input_data.heading_marker = "## 更新日志"

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

        # 配置 markdown 更新器
        markdown_config = MarkdownUpdateConfig(
            heading_marker=input_data.heading_marker,
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

        # 步骤 3：生成更新日志条目
        generator = ChangelogGenerator()
        entry = generator.generate_from_analysis(
            analysis,
            use_smart_summary=input_data.use_smart_summary,
        )

        # 步骤 4：更新 README
        updater = MarkdownUpdater(markdown_config)
        success, message = updater.update_readme(str(readme_path), entry)

        if not success:
            return [TextContent(
                type="text",
                text=f"错误：{message}"
            )]

        # 构建成功响应
        response_parts = [
            f"✓ 成功更新 {readme_path.name}",
            f"",
            f"自动检测的配置：",
            f"- 仓库：{repo_path}",
            f"- README：{readme_path}",
            f"- 标题标记：{input_data.heading_marker}",
            f"- 比较模式：{comparison_mode.value}",
            f"",
            f"更新日志条目：",
            f"{entry.to_markdown()}",
            f"",
            f"分析摘要：",
            f"- 变化的文件：{analysis.total_files_changed}",
            f"- 分析的变化：{len(filtered_changes)}",
        ]

        if analysis.commit_hash:
            response_parts.append(f"- 提交：{analysis.commit_hash}")

        if analysis.author:
            response_parts.append(f"- 作者：{analysis.author}")

        # 添加关于过滤变化的详细信息
        if filtered_changes:
            response_parts.append(f"")
            response_parts.append(f"关键变化：")
            for i, change in enumerate(filtered_changes[:5], 1):  # 显示前 5 个
                response_parts.append(f"{i}. {change.summary or change.file_path}")

            if len(filtered_changes) > 5:
                response_parts.append(f"... 还有 {len(filtered_changes) - 5} 个")

        return [TextContent(
            type="text",
            text="\n".join(response_parts)
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
