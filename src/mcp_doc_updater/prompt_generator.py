
 #从 Git 分析结果生成提示词。

from datetime import datetime
from typing import List, Optional
from .models import (
    GitAnalysisResult,
    CodeChange,
    ChangeType,
    ChangeImportance,
)


class PromptGenerator:
    """从 Git 分析生成用于 AI 的提示词。"""

    def __init__(self, max_diff_lines: int = 50):
        """
        初始化提示词生成器。

        Args:
            max_diff_lines: 每个文件包含的最大 diff 行数
        """
        self.max_diff_lines = max_diff_lines

    def generate_from_analysis(
        self,
        analysis: GitAnalysisResult,
        include_diff: bool = True,
        language: str = "zh",
    ) -> str:
        """
        从 Git 分析结果生成提示词。

        Args:
            analysis: GitAnalysisResult
            include_diff: 是否包含 diff 内容
            language: 输出语言 ('zh' 或 'en')

        Returns:
            生成的提示词字符串
        """
        if language == "zh":
            return self._generate_chinese_prompt(analysis, include_diff)
        else:
            return self._generate_english_prompt(analysis, include_diff)

    def _generate_chinese_prompt(
        self,
        analysis: GitAnalysisResult,
        include_diff: bool,
    ) -> str:
        """
        生成中文提示词。

        Args:
            analysis: GitAnalysisResult
            include_diff: 是否包含 diff 内容

        Returns:
            中文提示词
        """
        prompt_parts = []

        # 获取当前日期
        current_date = analysis.timestamp or datetime.now()
        date_str = current_date.strftime("%Y年%m月%d日")

        # 标题和任务说明
        prompt_parts.append("# 任务：生成 README 更新日志条目")
        prompt_parts.append("")
        prompt_parts.append("请根据以下代码变化信息，生成一条可以直接写入 README 的更新日志条目。")
        prompt_parts.append("")

        # 要求
        prompt_parts.append("## 输出要求")
        prompt_parts.append("1. **严格按照以下格式输出**（注意日期和内容之间有两个空格）：")
        prompt_parts.append(f"   ```")
        prompt_parts.append(f"   {date_str}  变化内容描述")
        prompt_parts.append(f"   ```")
        prompt_parts.append("")
        prompt_parts.append("2. **内容要求**：")
        prompt_parts.append("   - 使用中文描述")
        prompt_parts.append("   - 简洁明了，突出重点变化")
        prompt_parts.append("   - 使用用户友好的语言，避免过多技术细节")
        prompt_parts.append("   - 多个变化用分号（；）或顿号（、）分隔")
        prompt_parts.append("   - 一行内完成，不要换行")
        prompt_parts.append("")
        prompt_parts.append("3. **禁止事项**：")
        prompt_parts.append("   - 不要添加任何额外的说明文字")
        prompt_parts.append("   - 不要添加作者、提交哈希等元信息")
        prompt_parts.append("   - 不要添加 markdown 格式（如加粗、斜体等）")
        prompt_parts.append("   - 只输出一行日志条目")
        prompt_parts.append("")

        # 基本信息
        prompt_parts.append("## 代码变化基本信息")
        prompt_parts.append(f"- 日期: {date_str}")
        prompt_parts.append(f"- 比较模式: {analysis.comparison_mode.value}")
        prompt_parts.append(f"- 变化的文件数: {analysis.total_files_changed}")
        prompt_parts.append(f"- 新增行数: {analysis.total_lines_added}")
        prompt_parts.append(f"- 删除行数: {analysis.total_lines_deleted}")

        if analysis.commit_message:
            prompt_parts.append(f"- 提交消息: {analysis.commit_message}")

        if analysis.author:
            prompt_parts.append(f"- 作者: {analysis.author}")

        prompt_parts.append("")

        # 变化摘要
        if analysis.changes:
            prompt_parts.append("## 代码变化摘要统计")
            prompt_parts.append("")
            prompt_parts.append(self._generate_changes_summary(analysis.changes))
            prompt_parts.append("")

        # 详细变化
        if analysis.changes:
            prompt_parts.append("## 详细变化列表")
            prompt_parts.append("")
            for i, change in enumerate(analysis.changes, 1):
                prompt_parts.append(f"### {i}. {change.file_path}")
                prompt_parts.append(f"- 变化类型: {self._translate_change_type(change.change_type)}")
                prompt_parts.append(f"- 重要性: {self._translate_importance(change.importance)}")
                prompt_parts.append(f"- 变化行数: {change.line_count}")

                if change.summary:
                    prompt_parts.append(f"- 摘要: {change.summary}")

                # 语义信息
                if change.functions_added:
                    prompt_parts.append(f"- 新增函数: {', '.join(change.functions_added)}")
                if change.functions_modified:
                    prompt_parts.append(f"- 修改函数: {', '.join(change.functions_modified)}")
                if change.functions_deleted:
                    prompt_parts.append(f"- 删除函数: {', '.join(change.functions_deleted)}")
                if change.classes_added:
                    prompt_parts.append(f"- 新增类: {', '.join(change.classes_added)}")
                if change.classes_modified:
                    prompt_parts.append(f"- 修改类: {', '.join(change.classes_modified)}")

                # Diff 内容
                if include_diff and change.diff_text:
                    prompt_parts.append("")
                    prompt_parts.append("**Diff 内容:**")
                    prompt_parts.append("```diff")
                    prompt_parts.append(self._truncate_diff(change.diff_text))
                    prompt_parts.append("```")

                prompt_parts.append("")

        # 输出格式示例
        prompt_parts.append("## 输出格式示例")
        prompt_parts.append("")
        prompt_parts.append("**正确示例：**")
        prompt_parts.append(f"```")
        prompt_parts.append(f"{date_str}  新增用户认证模块；优化数据库查询性能；修复登录bug")
        prompt_parts.append(f"```")
        prompt_parts.append("")
        prompt_parts.append("**更多示例：**")
        prompt_parts.append(f"- `{date_str}  重构项目架构，将更新日志生成改为提示词生成；新增多语言支持`")
        prompt_parts.append(f"- `{date_str}  新增函数: handle_request、process_data；更新配置文件`")
        prompt_parts.append(f"- `{date_str}  修复登录验证bug；优化数据库查询性能；更新依赖版本`")
        prompt_parts.append("")
        prompt_parts.append("**错误示例（不要这样输出）：**")
        prompt_parts.append("- ❌ 添加了说明文字：`更新日志：2026年01月23日  新增功能`")
        prompt_parts.append("- ❌ 包含作者信息：`2026年01月23日  新增功能 (by 张三)`")
        prompt_parts.append("- ❌ 使用 markdown 格式：`2026年01月23日  **新增功能**`")
        prompt_parts.append("- ❌ 多行输出：")
        prompt_parts.append("  ```")
        prompt_parts.append("  2026年01月23日")
        prompt_parts.append("  新增功能")
        prompt_parts.append("  ```")
        prompt_parts.append("")
        prompt_parts.append("---")
        prompt_parts.append("")
        prompt_parts.append("**请严格按照格式生成更新日志条目（只输出一行，格式为：日期  内容）：**")

        return "\n".join(prompt_parts)

    def _generate_english_prompt(
        self,
        analysis: GitAnalysisResult,
        include_diff: bool,
    ) -> str:
        """
        生成英文提示词。

        Args:
            analysis: GitAnalysisResult
            include_diff: 是否包含 diff 内容

        Returns:
            英文提示词
        """
        prompt_parts = []

        # Get current date
        current_date = analysis.timestamp or datetime.now()
        date_str = current_date.strftime("%B %d, %Y")  # e.g., "January 23, 2026"

        # Title and task description
        prompt_parts.append("# Task: Generate README Changelog Entry")
        prompt_parts.append("")
        prompt_parts.append("Please generate a changelog entry that can be directly written to the README based on the following code changes.")
        prompt_parts.append("")

        # Requirements
        prompt_parts.append("## Output Requirements")
        prompt_parts.append("1. **Strictly follow this format** (note: two spaces between date and content):")
        prompt_parts.append(f"   ```")
        prompt_parts.append(f"   {date_str}  Description of changes")
        prompt_parts.append(f"   ```")
        prompt_parts.append("")
        prompt_parts.append("2. **Content Requirements**:")
        prompt_parts.append("   - Use clear, user-friendly language")
        prompt_parts.append("   - Be concise and highlight key changes")
        prompt_parts.append("   - Avoid excessive technical jargon")
        prompt_parts.append("   - Separate multiple changes with semicolons (;)")
        prompt_parts.append("   - Complete in one line, no line breaks")
        prompt_parts.append("")
        prompt_parts.append("3. **Prohibited**:")
        prompt_parts.append("   - Do not add any additional explanatory text")
        prompt_parts.append("   - Do not include author, commit hash, or other metadata")
        prompt_parts.append("   - Do not add markdown formatting (bold, italic, etc.)")
        prompt_parts.append("   - Output only one line of changelog entry")
        prompt_parts.append("")

        # Basic information
        prompt_parts.append("## Code Changes Basic Information")
        prompt_parts.append(f"- Date: {date_str}")
        prompt_parts.append(f"- Comparison mode: {analysis.comparison_mode.value}")
        prompt_parts.append(f"- Files changed: {analysis.total_files_changed}")
        prompt_parts.append(f"- Lines added: {analysis.total_lines_added}")
        prompt_parts.append(f"- Lines deleted: {analysis.total_lines_deleted}")

        if analysis.commit_message:
            prompt_parts.append(f"- Commit message: {analysis.commit_message}")

        if analysis.author:
            prompt_parts.append(f"- Author: {analysis.author}")

        prompt_parts.append("")

        # Changes summary
        if analysis.changes:
            prompt_parts.append("## Code Changes Summary Statistics")
            prompt_parts.append("")
            prompt_parts.append(self._generate_changes_summary_en(analysis.changes))
            prompt_parts.append("")

        # Detailed changes
        if analysis.changes:
            prompt_parts.append("## Detailed Changes List")
            prompt_parts.append("")
            for i, change in enumerate(analysis.changes, 1):
                prompt_parts.append(f"### {i}. {change.file_path}")
                prompt_parts.append(f"- Change type: {change.change_type.value}")
                prompt_parts.append(f"- Importance: {change.importance.value}")
                prompt_parts.append(f"- Lines changed: {change.line_count}")

                if change.summary:
                    prompt_parts.append(f"- Summary: {change.summary}")

                # Semantic information
                if change.functions_added:
                    prompt_parts.append(f"- Functions added: {', '.join(change.functions_added)}")
                if change.functions_modified:
                    prompt_parts.append(f"- Functions modified: {', '.join(change.functions_modified)}")
                if change.functions_deleted:
                    prompt_parts.append(f"- Functions deleted: {', '.join(change.functions_deleted)}")
                if change.classes_added:
                    prompt_parts.append(f"- Classes added: {', '.join(change.classes_added)}")
                if change.classes_modified:
                    prompt_parts.append(f"- Classes modified: {', '.join(change.classes_modified)}")

                # Diff content
                if include_diff and change.diff_text:
                    prompt_parts.append("")
                    prompt_parts.append("**Diff:**")
                    prompt_parts.append("```diff")
                    prompt_parts.append(self._truncate_diff(change.diff_text))
                    prompt_parts.append("```")

                prompt_parts.append("")

        # Output format examples
        prompt_parts.append("## Output Format Examples")
        prompt_parts.append("")
        prompt_parts.append("**Correct Examples:**")
        prompt_parts.append(f"```")
        prompt_parts.append(f"{date_str}  Added user authentication module; optimized database query performance; fixed login bug")
        prompt_parts.append(f"```")
        prompt_parts.append("")
        prompt_parts.append("**More Examples:**")
        prompt_parts.append(f"- `{date_str}  Refactored project architecture; added multi-language support`")
        prompt_parts.append(f"- `{date_str}  Added handle_request and process_data functions; updated config files`")
        prompt_parts.append(f"- `{date_str}  Fixed login validation bug; optimized database queries; updated dependencies`")
        prompt_parts.append("")
        prompt_parts.append("**Incorrect Examples (do not output like this):**")
        prompt_parts.append("- ❌ Added explanatory text: `Changelog: January 23, 2026  Added new feature`")
        prompt_parts.append("- ❌ Included author info: `January 23, 2026  Added new feature (by John Doe)`")
        prompt_parts.append("- ❌ Used markdown formatting: `January 23, 2026  **Added new feature**`")
        prompt_parts.append("- ❌ Multi-line output:")
        prompt_parts.append("  ```")
        prompt_parts.append("  January 23, 2026")
        prompt_parts.append("  Added new feature")
        prompt_parts.append("  ```")
        prompt_parts.append("")
        prompt_parts.append("---")
        prompt_parts.append("")
        prompt_parts.append("**Please strictly follow the format to generate the changelog entry (output only one line, format: date  content):**")

        return "\n".join(prompt_parts)

    def _generate_changes_summary(self, changes: List[CodeChange]) -> str:
        """
        生成变化的中文摘要统计。

        Args:
            changes: 代码变更列表

        Returns:
            摘要字符串
        """
        added_count = sum(1 for c in changes if c.change_type == ChangeType.ADDED)
        modified_count = sum(1 for c in changes if c.change_type == ChangeType.MODIFIED)
        deleted_count = sum(1 for c in changes if c.change_type == ChangeType.DELETED)
        renamed_count = sum(1 for c in changes if c.change_type == ChangeType.RENAMED)

        total_functions_added = sum(len(c.functions_added) for c in changes)
        total_functions_modified = sum(len(c.functions_modified) for c in changes)
        total_classes_added = sum(len(c.classes_added) for c in changes)

        summary_parts = []

        if added_count > 0:
            summary_parts.append(f"- 新增文件: {added_count} 个")
        if modified_count > 0:
            summary_parts.append(f"- 修改文件: {modified_count} 个")
        if deleted_count > 0:
            summary_parts.append(f"- 删除文件: {deleted_count} 个")
        if renamed_count > 0:
            summary_parts.append(f"- 重命名文件: {renamed_count} 个")

        if total_classes_added > 0:
            summary_parts.append(f"- 新增类: {total_classes_added} 个")
        if total_functions_added > 0:
            summary_parts.append(f"- 新增函数: {total_functions_added} 个")
        if total_functions_modified > 0:
            summary_parts.append(f"- 修改函数: {total_functions_modified} 个")

        return "\n".join(summary_parts) if summary_parts else "无显著变化"

    def _generate_changes_summary_en(self, changes: List[CodeChange]) -> str:
        """
        生成变化的英文摘要统计。

        Args:
            changes: 代码变更列表

        Returns:
            摘要字符串
        """
        added_count = sum(1 for c in changes if c.change_type == ChangeType.ADDED)
        modified_count = sum(1 for c in changes if c.change_type == ChangeType.MODIFIED)
        deleted_count = sum(1 for c in changes if c.change_type == ChangeType.DELETED)
        renamed_count = sum(1 for c in changes if c.change_type == ChangeType.RENAMED)

        total_functions_added = sum(len(c.functions_added) for c in changes)
        total_functions_modified = sum(len(c.functions_modified) for c in changes)
        total_classes_added = sum(len(c.classes_added) for c in changes)

        summary_parts = []

        if added_count > 0:
            summary_parts.append(f"- Files added: {added_count}")
        if modified_count > 0:
            summary_parts.append(f"- Files modified: {modified_count}")
        if deleted_count > 0:
            summary_parts.append(f"- Files deleted: {deleted_count}")
        if renamed_count > 0:
            summary_parts.append(f"- Files renamed: {renamed_count}")

        if total_classes_added > 0:
            summary_parts.append(f"- Classes added: {total_classes_added}")
        if total_functions_added > 0:
            summary_parts.append(f"- Functions added: {total_functions_added}")
        if total_functions_modified > 0:
            summary_parts.append(f"- Functions modified: {total_functions_modified}")

        return "\n".join(summary_parts) if summary_parts else "No significant changes"

    def _truncate_diff(self, diff_text: str) -> str:
        """
        截断 diff 内容到指定行数。

        Args:
            diff_text: 完整的 diff 文本

        Returns:
            截断后的 diff 文本
        """
        lines = diff_text.split("\n")
        if len(lines) <= self.max_diff_lines:
            return diff_text

        truncated = lines[:self.max_diff_lines]
        truncated.append(f"... (省略 {len(lines) - self.max_diff_lines} 行)")
        return "\n".join(truncated)

    def _translate_change_type(self, change_type: ChangeType) -> str:
        """翻译变化类型为中文。"""
        translations = {
            ChangeType.ADDED: "新增",
            ChangeType.MODIFIED: "修改",
            ChangeType.DELETED: "删除",
            ChangeType.RENAMED: "重命名",
        }
        return translations.get(change_type, change_type.value)

    def _translate_importance(self, importance: ChangeImportance) -> str:
        """翻译重要性级别为中文。"""
        translations = {
            ChangeImportance.CRITICAL: "关键",
            ChangeImportance.IMPORTANT: "重要",
            ChangeImportance.NORMAL: "普通",
            ChangeImportance.TRIVIAL: "琐碎",
        }
        return translations.get(importance, importance.value)
