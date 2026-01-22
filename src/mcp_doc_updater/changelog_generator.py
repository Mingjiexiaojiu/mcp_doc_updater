"""从 Git 分析结果生成更新日志。"""

from datetime import datetime
from typing import List, Optional
from .models import (
    GitAnalysisResult,
    ChangelogEntry,
    CodeChange,
    ChangeType,
)


class ChangelogGenerator:
    """从 Git 分析生成更新日志条目。"""

    def generate_from_commit(
        self,
        commit_message: str,
        commit_hash: Optional[str] = None,
        author: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> ChangelogEntry:
        """
        从提交消息生成更新日志条目。

        Args:
            commit_message: 提交消息
            commit_hash: 可选的提交哈希
            author: 可选的作者名称
            timestamp: 可选的时间戳

        Returns:
            ChangelogEntry
        """
        # 清理提交消息
        content = commit_message.strip().split("\n")[0]  # 仅使用第一行

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
        从 Git 分析结果生成更新日志条目。

        Args:
            analysis: GitAnalysisResult
            use_smart_summary: 是否生成智能摘要

        Returns:
            ChangelogEntry
        """
        if use_smart_summary and analysis.changes:
            content = self._generate_smart_summary(analysis.changes)
        else:
            # 回退到提交消息或基本摘要
            content = analysis.commit_message or analysis.summary

        return ChangelogEntry(
            date=analysis.timestamp or datetime.now(),
            content=content,
            commit_hash=analysis.commit_hash,
            author=analysis.author,
        )

    def _generate_smart_summary(self, changes: List[CodeChange]) -> str:
        """
        从代码变更生成智能摘要。

        Args:
            changes: 代码变更列表

        Returns:
            中文智能摘要字符串
        """
        if not changes:
            return "无代码变化"

        # 对变更进行分类
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

        # 构建摘要部分
        summary_parts = []

        # 新功能（新增的文件/类/函数）
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

        # 修改
        if modified_files or functions_modified:
            mod_parts = []

            if functions_modified:
                if len(functions_modified) <= 3:
                    func_list = "、".join(functions_modified)
                    mod_parts.append(f"更新函数: {func_list}")
                else:
                    mod_parts.append(f"更新{len(functions_modified)}个函数")

            if modified_files and not functions_modified:
                # 如果我们还没有提到函数，则只提到文件
                if len(modified_files) <= 2:
                    file_list = "、".join([self._get_file_name(f) for f in modified_files])
                    mod_parts.append(f"更新文件: {file_list}")
                else:
                    mod_parts.append(f"更新{len(modified_files)}个文件")

            if mod_parts:
                summary_parts.append("，".join(mod_parts))

        # 删除
        if deleted_files:
            if len(deleted_files) <= 2:
                file_list = "、".join([self._get_file_name(f) for f in deleted_files])
                summary_parts.append(f"删除文件: {file_list}")
            else:
                summary_parts.append(f"删除{len(deleted_files)}个文件")

        # 组合所有部分
        if summary_parts:
            return "；".join(summary_parts)
        else:
            return f"更新{len(changes)}个文件"

    def _get_file_name(self, file_path: str) -> str:
        """
        从路径中提取文件名。

        Args:
            file_path: 完整文件路径

        Returns:
            仅文件名
        """
        return file_path.split("/")[-1]

    def generate_batch(
        self,
        analyses: List[GitAnalysisResult],
        use_smart_summary: bool = True,
    ) -> List[ChangelogEntry]:
        """
        生成多个更新日志条目。

        Args:
            analyses: GitAnalysisResult 列表
            use_smart_summary: 是否使用智能摘要

        Returns:
            ChangelogEntry 列表
        """
        entries = []

        for analysis in analyses:
            entry = self.generate_from_analysis(analysis, use_smart_summary)
            entries.append(entry)

        return entries

    def format_entries(self, entries: List[ChangelogEntry]) -> str:
        """
        将多个条目格式化为 Markdown。

        Args:
            entries: ChangelogEntry 列表

        Returns:
            格式化的 Markdown 字符串
        """
        lines = []

        for entry in entries:
            lines.append(entry.to_markdown())

        return "\n".join(lines)
