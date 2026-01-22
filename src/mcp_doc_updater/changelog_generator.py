"""Changelog generation from Git analysis results."""

from datetime import datetime
from typing import List, Optional
from .models import (
    GitAnalysisResult,
    ChangelogEntry,
    CodeChange,
    ChangeType,
)


class ChangelogGenerator:
    """Generates changelog entries from Git analysis."""

    def generate_from_commit(
        self,
        commit_message: str,
        commit_hash: Optional[str] = None,
        author: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> ChangelogEntry:
        """
        Generate changelog entry from commit message.

        Args:
            commit_message: Commit message
            commit_hash: Optional commit hash
            author: Optional author name
            timestamp: Optional timestamp

        Returns:
            ChangelogEntry
        """
        # Clean up commit message
        content = commit_message.strip().split("\n")[0]  # Use first line only

        return ChangelogEntry(
            date=timestamp or datetime.now(),
            content=content,
            commit_hash=commit_hash,
            author=author,
        )

    def generate_from_analysis(
        self,
        analysis: GitAnalysisResult,
        use_smart_summary: bool = True,
    ) -> ChangelogEntry:
        """
        Generate changelog entry from Git analysis result.

        Args:
            analysis: GitAnalysisResult
            use_smart_summary: Whether to generate smart summary

        Returns:
            ChangelogEntry
        """
        if use_smart_summary and analysis.changes:
            content = self._generate_smart_summary(analysis.changes)
        else:
            # Fall back to commit message or basic summary
            content = analysis.commit_message or analysis.summary

        return ChangelogEntry(
            date=analysis.timestamp or datetime.now(),
            content=content,
            commit_hash=analysis.commit_hash,
            author=analysis.author,
        )

    def _generate_smart_summary(self, changes: List[CodeChange]) -> str:
        """
        Generate intelligent summary from code changes.

        Args:
            changes: List of code changes

        Returns:
            Smart summary string in Chinese
        """
        if not changes:
            return "无代码变化"

        # Categorize changes
        added_files = []
        modified_files = []
        deleted_files = []
        functions_added = []
        functions_modified = []
        classes_added = []

        for change in changes:
            if change.change_type == ChangeType.ADDED:
                added_files.append(change.file_path)
            elif change.change_type == ChangeType.MODIFIED:
                modified_files.append(change.file_path)
            elif change.change_type == ChangeType.DELETED:
                deleted_files.append(change.file_path)

            functions_added.extend(change.functions_added)
            functions_modified.extend(change.functions_modified)
            classes_added.extend(change.classes_added)

        # Build summary parts
        summary_parts = []

        # New features (added files/classes/functions)
        if added_files or classes_added or functions_added:
            feature_parts = []

            if classes_added:
                feature_parts.append(f"新增{len(classes_added)}个类")

            if functions_added:
                if len(functions_added) <= 3:
                    func_list = "、".join(functions_added)
                    feature_parts.append(f"新增函数: {func_list}")
                else:
                    feature_parts.append(f"新增{len(functions_added)}个函数")

            if added_files:
                if len(added_files) <= 2:
                    file_list = "、".join([self._get_file_name(f) for f in added_files])
                    feature_parts.append(f"新增文件: {file_list}")
                else:
                    feature_parts.append(f"新增{len(added_files)}个文件")

            if feature_parts:
                summary_parts.append("，".join(feature_parts))

        # Modifications
        if modified_files or functions_modified:
            mod_parts = []

            if functions_modified:
                if len(functions_modified) <= 3:
                    func_list = "、".join(functions_modified)
                    mod_parts.append(f"更新函数: {func_list}")
                else:
                    mod_parts.append(f"更新{len(functions_modified)}个函数")

            if modified_files and not functions_modified:
                # Only mention files if we didn't already mention functions
                if len(modified_files) <= 2:
                    file_list = "、".join([self._get_file_name(f) for f in modified_files])
                    mod_parts.append(f"更新文件: {file_list}")
                else:
                    mod_parts.append(f"更新{len(modified_files)}个文件")

            if mod_parts:
                summary_parts.append("，".join(mod_parts))

        # Deletions
        if deleted_files:
            if len(deleted_files) <= 2:
                file_list = "、".join([self._get_file_name(f) for f in deleted_files])
                summary_parts.append(f"删除文件: {file_list}")
            else:
                summary_parts.append(f"删除{len(deleted_files)}个文件")

        # Combine all parts
        if summary_parts:
            return "；".join(summary_parts)
        else:
            return f"更新{len(changes)}个文件"

    def _get_file_name(self, file_path: str) -> str:
        """
        Extract file name from path.

        Args:
            file_path: Full file path

        Returns:
            File name only
        """
        return file_path.split("/")[-1]

    def generate_batch(
        self,
        analyses: List[GitAnalysisResult],
        use_smart_summary: bool = True,
    ) -> List[ChangelogEntry]:
        """
        Generate multiple changelog entries.

        Args:
            analyses: List of GitAnalysisResult
            use_smart_summary: Whether to use smart summaries

        Returns:
            List of ChangelogEntry
        """
        entries = []

        for analysis in analyses:
            entry = self.generate_from_analysis(analysis, use_smart_summary)
            entries.append(entry)

        return entries

    def format_entries(self, entries: List[ChangelogEntry]) -> str:
        """
        Format multiple entries as markdown.

        Args:
            entries: List of ChangelogEntry

        Returns:
            Formatted markdown string
        """
        lines = []

        for entry in entries:
            lines.append(entry.to_markdown())

        return "\n".join(lines)
