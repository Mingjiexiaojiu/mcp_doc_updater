"""MCP server for doc updater tool."""

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
from .utils import auto_detect_paths, find_changelog_heading


# Tool input models
class UpdateReadmeChangelogInput(BaseModel):
    """Input for update_readme_changelog tool."""
    repo_path: Optional[str] = Field(
        default=None,
        description="Path to Git repository (auto-detected if not provided)"
    )
    readme_path: Optional[str] = Field(
        default=None,
        description="Path to README file (auto-detected if not provided, relative to repo or absolute)"
    )
    comparison_mode: str = Field(
        default="latest_vs_previous",
        description="Comparison mode: latest_vs_previous, working_tree_vs_head, or latest_vs_tag"
    )
    heading_marker: Optional[str] = Field(
        default=None,
        description="Markdown heading to insert changelog under (auto-detected if not provided)"
    )
    filter_trivial: bool = Field(
        default=True,
        description="Whether to filter out trivial changes"
    )
    use_smart_summary: bool = Field(
        default=True,
        description="Whether to generate smart summary from code analysis"
    )
    tag_name: Optional[str] = Field(
        default=None,
        description="Tag name for latest_vs_tag mode"
    )
    token_budget: Optional[int] = Field(
        default=None,
        description="Optional token budget for diff analysis"
    )


# Create MCP server
app = Server("mcp-doc-updater")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="update_readme_changelog",
            description=(
                "Analyze Git code changes and update README changelog with full auto-detection. "
                "Automatically detects: Git repository path, README file location, and changelog heading. "
                "Intelligently extracts key changes, filters trivial modifications, "
                "and generates Chinese changelog entries in format: YYYY年MM月DD日  内容. "
                "All parameters are optional and will be auto-detected if not provided."
            ),
            inputSchema=UpdateReadmeChangelogInput.model_json_schema(),
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "update_readme_changelog":
        return await handle_update_readme_changelog(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_update_readme_changelog(arguments: dict) -> list[TextContent]:
    """
    Handle update_readme_changelog tool call.

    Args:
        arguments: Tool arguments

    Returns:
        List of TextContent with results
    """
    try:
        # Parse and validate input
        input_data = UpdateReadmeChangelogInput(**arguments)

        # Auto-detect paths if not provided
        if not input_data.repo_path or not input_data.readme_path:
            detected_repo, detected_readme = auto_detect_paths()

            if not input_data.repo_path:
                if detected_repo:
                    input_data.repo_path = str(detected_repo)
                else:
                    return [TextContent(
                        type="text",
                        text="Error: Could not auto-detect Git repository. Please provide repo_path parameter."
                    )]

            if not input_data.readme_path:
                if detected_readme:
                    input_data.readme_path = str(detected_readme)
                else:
                    return [TextContent(
                        type="text",
                        text="Error: Could not auto-detect README file. Please provide readme_path parameter."
                    )]

        # Resolve paths
        repo_path = Path(input_data.repo_path).resolve()
        if not repo_path.exists():
            return [TextContent(
                type="text",
                text=f"Error: Repository path does not exist: {repo_path}"
            )]

        # Resolve README path
        readme_path = Path(input_data.readme_path)
        if not readme_path.is_absolute():
            readme_path = repo_path / readme_path
        readme_path = readme_path.resolve()

        if not readme_path.exists():
            return [TextContent(
                type="text",
                text=f"Error: README file does not exist: {readme_path}"
            )]

        # Auto-detect heading marker if not provided
        if not input_data.heading_marker:
            detected_heading = find_changelog_heading(readme_path)
            if detected_heading:
                input_data.heading_marker = detected_heading
            else:
                # Use default Chinese heading
                input_data.heading_marker = "## 更新日志"

        # Parse comparison mode
        try:
            comparison_mode = ComparisonMode(input_data.comparison_mode)
        except ValueError:
            return [TextContent(
                type="text",
                text=f"Error: Invalid comparison mode: {input_data.comparison_mode}"
            )]

        # Configure filter
        filter_config = FilterConfig(
            min_importance=ChangeImportance.NORMAL if input_data.filter_trivial else ChangeImportance.TRIVIAL,
            token_budget=input_data.token_budget,
        )

        # Configure markdown updater
        markdown_config = MarkdownUpdateConfig(
            heading_marker=input_data.heading_marker,
        )

        # Step 1: Analyze Git changes
        analyzer = GitAnalyzer(str(repo_path), filter_config)
        analysis = analyzer.analyze_changes(
            mode=comparison_mode,
            tag_name=input_data.tag_name,
        )

        if not analysis.changes:
            return [TextContent(
                type="text",
                text="No significant changes detected."
            )]

        # Step 2: Filter changes
        diff_filter = DiffFilter(filter_config)
        filtered_changes = diff_filter.filter_changes(analysis.changes)

        if not filtered_changes:
            return [TextContent(
                type="text",
                text="No significant changes after filtering."
            )]

        # Update analysis with filtered changes
        analysis.changes = filtered_changes

        # Step 3: Generate changelog entry
        generator = ChangelogGenerator()
        entry = generator.generate_from_analysis(
            analysis,
            use_smart_summary=input_data.use_smart_summary,
        )

        # Step 4: Update README
        updater = MarkdownUpdater(markdown_config)
        success, message = updater.update_readme(str(readme_path), entry)

        if not success:
            return [TextContent(
                type="text",
                text=f"Error: {message}"
            )]

        # Build success response
        response_parts = [
            f"✓ Successfully updated {readme_path.name}",
            f"",
            f"Auto-detected paths:",
            f"- Repository: {repo_path}",
            f"- README: {readme_path}",
            f"- Heading marker: {input_data.heading_marker}",
            f"",
            f"Changelog entry:",
            f"{entry.to_markdown()}",
            f"",
            f"Analysis summary:",
            f"- Comparison mode: {comparison_mode.value}",
            f"- Files changed: {analysis.total_files_changed}",
            f"- Changes analyzed: {len(filtered_changes)}",
        ]

        if analysis.commit_hash:
            response_parts.append(f"- Commit: {analysis.commit_hash}")

        if analysis.author:
            response_parts.append(f"- Author: {analysis.author}")

        # Add details about filtered changes
        if filtered_changes:
            response_parts.append(f"")
            response_parts.append(f"Key changes:")
            for i, change in enumerate(filtered_changes[:5], 1):  # Show top 5
                response_parts.append(f"{i}. {change.summary or change.file_path}")

            if len(filtered_changes) > 5:
                response_parts.append(f"... and {len(filtered_changes) - 5} more")

        return [TextContent(
            type="text",
            text="\n".join(response_parts)
        )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}\n\nPlease check your input parameters and try again."
        )]


def main():
    """Main entry point for the MCP server."""
    import mcp.server.stdio

    # Run the server
    asyncio.run(mcp.server.stdio.stdio_server(app))


if __name__ == "__main__":
    main()
