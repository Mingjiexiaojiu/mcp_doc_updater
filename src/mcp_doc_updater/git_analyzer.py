"""用于提取代码变更的 Git 分析功能。"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
import git
from git import Repo, Commit, Diff

from .models import (
    ComparisonMode,
    ChangeType,
    ChangeImportance,
    CodeChange,
    GitAnalysisResult,
    FilterConfig,
)
from .utils import should_ignore_file, is_code_file


class GitAnalyzer:
    """分析 Git 仓库的变更。"""

    def __init__(self, repo_path: str, filter_config: Optional[FilterConfig] = None):
        """
        初始化 Git 分析器。

        Args:
            repo_path: Git 仓库路径
            filter_config: 可选的过滤器配置
        """
        self.repo_path = Path(repo_path)
        self.repo = Repo(repo_path)
        self.filter_config = filter_config or FilterConfig()

    def analyze_changes(
        self,
        mode: ComparisonMode = ComparisonMode.LATEST_VS_PREVIOUS,
        tag_name: Optional[str] = None,
    ) -> GitAnalysisResult:
        """
        根据比较模式分析变更。

        Args:
            mode: 比较模式
            tag_name: LATEST_VS_TAG 模式下的标签名称

        Returns:
            包含分析变更的 GitAnalysisResult
        """
        if mode == ComparisonMode.LATEST_VS_PREVIOUS:
            return self._analyze_latest_vs_previous()
        elif mode == ComparisonMode.WORKING_TREE_VS_HEAD:
            return self._analyze_working_tree_vs_head()
        elif mode == ComparisonMode.LATEST_VS_TAG:
            return self._analyze_latest_vs_tag(tag_name)
        else:
            raise ValueError(f"Unknown comparison mode: {mode}")

    def _analyze_latest_vs_previous(self) -> GitAnalysisResult:
        """分析最新提交与前一次提交之间的变更。"""
        commits = list(self.repo.iter_commits(max_count=2))

        if len(commits) < 2:
            # 只有一次提交，与空树比较
            if len(commits) == 1:
                latest_commit = commits[0]
                diffs = latest_commit.diff(git.NULL_TREE)
            else:
                raise ValueError("No commits found in repository")
        else:
            latest_commit = commits[0]
            previous_commit = commits[1]
            diffs = previous_commit.diff(latest_commit)

        changes = self._process_diffs(diffs)

        return GitAnalysisResult(
            comparison_mode=ComparisonMode.LATEST_VS_PREVIOUS,
            changes=changes,
            total_files_changed=len(changes),
            total_lines_added=sum(c.line_count for c in changes if c.change_type == ChangeType.ADDED),
            total_lines_deleted=sum(c.line_count for c in changes if c.change_type == ChangeType.DELETED),
            summary=self._generate_summary(changes),
            commit_hash=latest_commit.hexsha[:8],
            commit_message=latest_commit.message.strip(),
            author=latest_commit.author.name,
            timestamp=datetime.fromtimestamp(latest_commit.committed_date),
        )

    def _analyze_working_tree_vs_head(self) -> GitAnalysisResult:
        """分析工作树与 HEAD 之间的变更。"""
        # 获取未暂存的变更
        unstaged_diffs = self.repo.index.diff(None, create_patch=True)
        # 获取已暂存的变更
        staged_diffs = self.repo.head.commit.diff(create_patch=True)

        # 合并两者
        all_diffs = list(unstaged_diffs) + list(staged_diffs)
        changes = self._process_diffs(all_diffs)

        return GitAnalysisResult(
            comparison_mode=ComparisonMode.WORKING_TREE_VS_HEAD,
            changes=changes,
            total_files_changed=len(changes),
            total_lines_added=sum(c.line_count for c in changes if c.change_type == ChangeType.ADDED),
            total_lines_deleted=sum(c.line_count for c in changes if c.change_type == ChangeType.DELETED),
            summary=self._generate_summary(changes),
            commit_hash=None,
            commit_message="Working tree changes",
            author=None,
            timestamp=datetime.now(),
        )

    def _analyze_latest_vs_tag(self, tag_name: Optional[str]) -> GitAnalysisResult:
        """分析最新提交与标签之间的变更。"""
        if not tag_name:
            # 查找最新的标签
            tags = sorted(self.repo.tags, key=lambda t: t.commit.committed_date, reverse=True)
            if not tags:
                raise ValueError("No tags found in repository")
            tag = tags[0]
        else:
            tag = self.repo.tags[tag_name]

        latest_commit = self.repo.head.commit
        diffs = tag.commit.diff(latest_commit)
        changes = self._process_diffs(diffs)

        return GitAnalysisResult(
            comparison_mode=ComparisonMode.LATEST_VS_TAG,
            changes=changes,
            total_files_changed=len(changes),
            total_lines_added=sum(c.line_count for c in changes if c.change_type == ChangeType.ADDED),
            total_lines_deleted=sum(c.line_count for c in changes if c.change_type == ChangeType.DELETED),
            summary=self._generate_summary(changes),
            commit_hash=latest_commit.hexsha[:8],
            commit_message=latest_commit.message.strip(),
            author=latest_commit.author.name,
            timestamp=datetime.fromtimestamp(latest_commit.committed_date),
        )

    def _process_diffs(self, diffs: List[Diff]) -> List[CodeChange]:
        """
        将 Git diff 处理为 CodeChange 对象。

        Args:
            diffs: Git diff 对象列表

        Returns:
            CodeChange 对象列表
        """
        changes = []

        for diff in diffs:
            # 确定文件路径
            file_path = diff.b_path if diff.b_path else diff.a_path
            if not file_path:
                continue

            # 检查文件是否应该被忽略
            if should_ignore_file(file_path, self.filter_config.ignore_patterns):
                continue

            # 只处理代码文件
            if not is_code_file(file_path):
                continue

            # 确定变更类型
            change_type = self._determine_change_type(diff)

            # 获取 diff 文本
            try:
                diff_text = diff.diff.decode("utf-8") if diff.diff else ""
            except (UnicodeDecodeError, AttributeError):
                diff_text = ""

            if not diff_text:
                continue

            # 统计行数
            line_count = len([line for line in diff_text.split("\n") if line.startswith(("+", "-"))])

            # 创建 CodeChange 对象
            change = CodeChange(
                file_path=file_path,
                change_type=change_type,
                importance=ChangeImportance.NORMAL,  # 将由过滤器评估
                diff_text=diff_text,
                line_count=line_count,
            )

            changes.append(change)

        return changes

    def _determine_change_type(self, diff: Diff) -> ChangeType:
        """从 diff 确定变更类型。"""
        if diff.new_file:
            return ChangeType.ADDED
        elif diff.deleted_file:
            return ChangeType.DELETED
        elif diff.renamed_file:
            return ChangeType.RENAMED
        else:
            return ChangeType.MODIFIED

    def _generate_summary(self, changes: List[CodeChange]) -> str:
        """生成变更摘要。"""
        if not changes:
            return "No changes detected"

        added = sum(1 for c in changes if c.change_type == ChangeType.ADDED)
        modified = sum(1 for c in changes if c.change_type == ChangeType.MODIFIED)
        deleted = sum(1 for c in changes if c.change_type == ChangeType.DELETED)
        renamed = sum(1 for c in changes if c.change_type == ChangeType.RENAMED)

        parts = []
        if added:
            parts.append(f"{added} file(s) added")
        if modified:
            parts.append(f"{modified} file(s) modified")
        if deleted:
            parts.append(f"{deleted} file(s) deleted")
        if renamed:
            parts.append(f"{renamed} file(s) renamed")

        return ", ".join(parts)
