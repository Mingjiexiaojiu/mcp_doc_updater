"""Git analysis functionality for extracting code changes."""

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
    """Analyzes Git repository changes."""

    def __init__(self, repo_path: str, filter_config: Optional[FilterConfig] = None):
        """
        Initialize Git analyzer.

        Args:
            repo_path: Path to Git repository
            filter_config: Optional filter configuration
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
        Analyze changes based on comparison mode.

        Args:
            mode: Comparison mode
            tag_name: Tag name for LATEST_VS_TAG mode

        Returns:
            GitAnalysisResult with analyzed changes
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
        """Analyze changes between latest commit and previous commit."""
        commits = list(self.repo.iter_commits(max_count=2))

        if len(commits) < 2:
            # Only one commit, compare with empty tree
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
        """Analyze changes between working tree and HEAD."""
        # Get unstaged changes
        unstaged_diffs = self.repo.index.diff(None, create_patch=True)
        # Get staged changes
        staged_diffs = self.repo.head.commit.diff(create_patch=True)

        # Combine both
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
        """Analyze changes between latest commit and a tag."""
        if not tag_name:
            # Find the latest tag
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
        Process Git diffs into CodeChange objects.

        Args:
            diffs: List of Git diff objects

        Returns:
            List of CodeChange objects
        """
        changes = []

        for diff in diffs:
            # Determine file path
            file_path = diff.b_path if diff.b_path else diff.a_path
            if not file_path:
                continue

            # Check if file should be ignored
            if should_ignore_file(file_path, self.filter_config.ignore_patterns):
                continue

            # Only process code files
            if not is_code_file(file_path):
                continue

            # Determine change type
            change_type = self._determine_change_type(diff)

            # Get diff text
            try:
                diff_text = diff.diff.decode("utf-8") if diff.diff else ""
            except (UnicodeDecodeError, AttributeError):
                diff_text = ""

            if not diff_text:
                continue

            # Count lines
            line_count = len([line for line in diff_text.split("\n") if line.startswith(("+", "-"))])

            # Create CodeChange object
            change = CodeChange(
                file_path=file_path,
                change_type=change_type,
                importance=ChangeImportance.NORMAL,  # Will be assessed by filter
                diff_text=diff_text,
                line_count=line_count,
            )

            changes.append(change)

        return changes

    def _determine_change_type(self, diff: Diff) -> ChangeType:
        """Determine the type of change from a diff."""
        if diff.new_file:
            return ChangeType.ADDED
        elif diff.deleted_file:
            return ChangeType.DELETED
        elif diff.renamed_file:
            return ChangeType.RENAMED
        else:
            return ChangeType.MODIFIED

    def _generate_summary(self, changes: List[CodeChange]) -> str:
        """Generate a summary of changes."""
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
