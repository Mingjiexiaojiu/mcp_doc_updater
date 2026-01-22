"""Smart diff filtering to reduce token usage while preserving important changes."""

import re
from typing import List, Tuple
from .models import CodeChange, ChangeImportance, FilterConfig
from .utils import (
    is_whitespace_only,
    is_comment_line,
    is_import_line,
    extract_function_name,
    extract_class_name,
    count_tokens_estimate,
)


class DiffFilter:
    """Filters and processes diffs to extract important changes."""

    def __init__(self, config: FilterConfig):
        """
        Initialize diff filter.

        Args:
            config: Filter configuration
        """
        self.config = config

    def filter_changes(self, changes: List[CodeChange]) -> List[CodeChange]:
        """
        Filter and process changes based on configuration.

        Args:
            changes: List of code changes

        Returns:
            Filtered list of code changes
        """
        filtered = []

        for change in changes:
            # Assess importance
            self._assess_importance(change)

            # Skip if below minimum importance
            if self._importance_level(change.importance) < self._importance_level(self.config.min_importance):
                continue

            # Extract semantic information
            self._extract_semantic_info(change)

            # Compress diff text
            change.diff_text = self._compress_diff(change.diff_text)

            # Generate summary
            change.summary = self._generate_change_summary(change)

            filtered.append(change)

        # Sort by importance
        filtered.sort(key=lambda c: self._importance_level(c.importance), reverse=True)

        # Apply token budget if specified
        if self.config.token_budget:
            filtered = self._apply_token_budget(filtered, self.config.token_budget)

        return filtered

    def _assess_importance(self, change: CodeChange) -> None:
        """
        Assess the importance of a code change.

        Args:
            change: CodeChange to assess (modified in place)
        """
        diff_lines = change.diff_text.split("\n")
        importance_score = 0

        for line in diff_lines:
            if not line.startswith(("+", "-")):
                continue

            # Remove the +/- prefix
            content = line[1:].strip()

            if not content:
                continue

            # Skip trivial changes
            if self.config.ignore_whitespace and is_whitespace_only(content):
                continue

            if self.config.ignore_comments and is_comment_line(content):
                continue

            if self.config.ignore_imports and is_import_line(content):
                continue

            # Assess line importance
            line_importance = self._assess_line_importance(content)
            importance_score += line_importance

        # Determine overall importance
        if importance_score >= 10:
            change.importance = ChangeImportance.CRITICAL
        elif importance_score >= 5:
            change.importance = ChangeImportance.IMPORTANT
        elif importance_score >= 2:
            change.importance = ChangeImportance.NORMAL
        else:
            change.importance = ChangeImportance.TRIVIAL

    def _assess_line_importance(self, line: str) -> int:
        """
        Assess the importance of a single line.

        Args:
            line: Line to assess

        Returns:
            Importance score (higher = more important)
        """
        score = 1  # Base score

        # Critical patterns
        critical_patterns = [
            r'\bdef\s+\w+\s*\(',           # Function definition
            r'\bclass\s+\w+',              # Class definition
            r'\basync\s+def\s+\w+',        # Async function
            r'\breturn\s+',                # Return statement
            r'\braise\s+',                 # Exception raising
            r'\bthrow\s+',                 # JavaScript throw
            r'\bexport\s+',                # Export statement
            r'\bpublic\s+',                # Public modifier
            r'\bprivate\s+',               # Private modifier
        ]

        for pattern in critical_patterns:
            if re.search(pattern, line):
                score += 3
                break

        # Important patterns
        important_patterns = [
            r'\bif\s+',                    # Conditional
            r'\bfor\s+',                   # Loop
            r'\bwhile\s+',                 # Loop
            r'\btry\s*:',                  # Try block
            r'\bcatch\s*\(',               # Catch block
            r'\bawait\s+',                 # Await
            r'=\s*\w+\(',                  # Function call assignment
        ]

        for pattern in important_patterns:
            if re.search(pattern, line):
                score += 2
                break

        # Deduct for trivial patterns
        trivial_patterns = [
            r'^\s*$',                      # Empty line
            r'^\s*#',                      # Comment
            r'^\s*//',                     # Comment
            r'^\s*console\.log',           # Debug logging
            r'^\s*print\(',                # Debug print
        ]

        for pattern in trivial_patterns:
            if re.search(pattern, line):
                score = 0
                break

        return score

    def _extract_semantic_info(self, change: CodeChange) -> None:
        """
        Extract semantic information from diff.

        Args:
            change: CodeChange to analyze (modified in place)
        """
        diff_lines = change.diff_text.split("\n")

        for line in diff_lines:
            if not line.startswith(("+", "-")):
                continue

            prefix = line[0]
            content = line[1:]

            # Extract function names
            func_name = extract_function_name(content)
            if func_name:
                if prefix == "+":
                    change.functions_added.append(func_name)
                elif prefix == "-":
                    change.functions_deleted.append(func_name)

            # Extract class names
            class_name = extract_class_name(content)
            if class_name:
                if prefix == "+":
                    change.classes_added.append(class_name)

    def _compress_diff(self, diff_text: str) -> str:
        """
        Compress diff text by removing unnecessary context.

        Args:
            diff_text: Original diff text

        Returns:
            Compressed diff text
        """
        lines = diff_text.split("\n")
        compressed_lines = []
        context_buffer = []
        last_change_index = -1

        for i, line in enumerate(lines):
            # Keep header lines
            if line.startswith(("diff --git", "index", "---", "+++")):
                compressed_lines.append(line)
                continue

            # Keep hunk headers
            if line.startswith("@@"):
                compressed_lines.append(line)
                context_buffer = []
                continue

            # Check if this is a change line
            is_change = line.startswith(("+", "-"))

            if is_change:
                # Add buffered context before this change
                if context_buffer and (last_change_index == -1 or i - last_change_index > self.config.max_context_lines):
                    # Only add last N context lines
                    compressed_lines.extend(context_buffer[-self.config.max_context_lines:])
                else:
                    compressed_lines.extend(context_buffer)

                context_buffer = []
                compressed_lines.append(line)
                last_change_index = i
            else:
                # This is a context line
                if last_change_index != -1 and i - last_change_index <= self.config.max_context_lines:
                    # Within context window of last change
                    compressed_lines.append(line)
                else:
                    # Buffer this context line
                    context_buffer.append(line)

                    # If buffer is too large, clear it
                    if len(context_buffer) > self.config.max_context_lines * 2:
                        context_buffer = []

        return "\n".join(compressed_lines)

    def _generate_change_summary(self, change: CodeChange) -> str:
        """
        Generate a human-readable summary of the change.

        Args:
            change: CodeChange to summarize

        Returns:
            Summary string
        """
        parts = []

        # File and change type
        parts.append(f"{change.change_type.value}: {change.file_path}")

        # Functions
        if change.functions_added:
            parts.append(f"新增函数: {', '.join(change.functions_added)}")
        if change.functions_modified:
            parts.append(f"修改函数: {', '.join(change.functions_modified)}")
        if change.functions_deleted:
            parts.append(f"删除函数: {', '.join(change.functions_deleted)}")

        # Classes
        if change.classes_added:
            parts.append(f"新增类: {', '.join(change.classes_added)}")
        if change.classes_modified:
            parts.append(f"修改类: {', '.join(change.classes_modified)}")

        # Line count
        if change.line_count > 0:
            parts.append(f"({change.line_count} 行变化)")

        return " | ".join(parts)

    def _apply_token_budget(self, changes: List[CodeChange], budget: int) -> List[CodeChange]:
        """
        Apply token budget by truncating changes list.

        Args:
            changes: List of changes (should be sorted by importance)
            budget: Token budget

        Returns:
            Truncated list of changes
        """
        total_tokens = 0
        result = []

        for change in changes:
            change_tokens = count_tokens_estimate(change.diff_text)

            if total_tokens + change_tokens > budget:
                # Try to include at least the summary
                summary_tokens = count_tokens_estimate(change.summary or "")
                if total_tokens + summary_tokens <= budget:
                    # Replace diff with summary only
                    change.diff_text = f"(Summary only - exceeded token budget)\n{change.summary}"
                    result.append(change)
                    total_tokens += summary_tokens
                break

            result.append(change)
            total_tokens += change_tokens

        return result

    def _importance_level(self, importance: ChangeImportance) -> int:
        """Convert importance enum to numeric level."""
        levels = {
            ChangeImportance.CRITICAL: 4,
            ChangeImportance.IMPORTANT: 3,
            ChangeImportance.NORMAL: 2,
            ChangeImportance.TRIVIAL: 1,
        }
        return levels.get(importance, 0)


class TokenOptimizer:
    """Optimizes token usage for changes."""

    @staticmethod
    def create_compact_summary(changes: List[CodeChange]) -> str:
        """
        Create a compact summary of all changes.

        Args:
            changes: List of code changes

        Returns:
            Compact summary string
        """
        if not changes:
            return "无变化"

        # Group by change type
        by_type = {}
        for change in changes:
            change_type = change.change_type.value
            if change_type not in by_type:
                by_type[change_type] = []
            by_type[change_type].append(change)

        summary_parts = []

        # Summarize each type
        for change_type, type_changes in by_type.items():
            files = [c.file_path for c in type_changes]
            if len(files) <= 3:
                file_list = ", ".join(files)
            else:
                file_list = f"{', '.join(files[:3])} 等{len(files)}个文件"

            summary_parts.append(f"{change_type}: {file_list}")

        return "; ".join(summary_parts)
