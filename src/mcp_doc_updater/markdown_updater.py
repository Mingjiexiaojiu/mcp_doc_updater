"""Markdown document updater for inserting changelog entries."""

import re
from pathlib import Path
from typing import Optional, Tuple
from .models import ChangelogEntry, MarkdownUpdateConfig


class MarkdownUpdater:
    """Updates markdown documents with changelog entries."""

    def __init__(self, config: Optional[MarkdownUpdateConfig] = None):
        """
        Initialize markdown updater.

        Args:
            config: Optional configuration
        """
        self.config = config or MarkdownUpdateConfig()

    def update_readme(
        self,
        file_path: str,
        entry: ChangelogEntry,
    ) -> Tuple[bool, str]:
        """
        Update README file with new changelog entry.

        Args:
            file_path: Path to README file
            entry: Changelog entry to insert

        Returns:
            Tuple of (success, message)
        """
        path = Path(file_path)

        # Check if file exists
        if not path.exists():
            return False, f"File not found: {file_path}"

        # Read current content
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"Failed to read file: {e}"

        # Find heading position
        position = self.find_heading_position(content, self.config.heading_marker)

        if position == -1:
            return False, f"Heading not found: {self.config.heading_marker}"

        # Insert entry
        new_content = self.insert_entry(content, position, entry)

        # Apply max entries limit if configured
        if self.config.max_entries:
            new_content = self._limit_entries(new_content, position)

        # Write back to file
        try:
            path.write_text(new_content, encoding="utf-8")
            return True, f"Successfully updated {file_path}"
        except Exception as e:
            return False, f"Failed to write file: {e}"

    def find_heading_position(self, content: str, heading: str) -> int:
        """
        Find the position of a markdown heading.

        Args:
            content: Markdown content
            heading: Heading to find (e.g., "## 更新日志")

        Returns:
            Character position after the heading, or -1 if not found
        """
        # Escape special regex characters in heading
        escaped_heading = re.escape(heading)

        # Pattern to match the heading (with optional trailing whitespace)
        pattern = rf'^{escaped_heading}\s*$'

        lines = content.split("\n")

        for i, line in enumerate(lines):
            if re.match(pattern, line.strip()):
                # Found the heading, return position after this line
                position = sum(len(l) + 1 for l in lines[:i+1])  # +1 for newline
                return position

        return -1

    def insert_entry(
        self,
        content: str,
        position: int,
        entry: ChangelogEntry,
    ) -> str:
        """
        Insert changelog entry at specified position.

        Args:
            content: Original content
            position: Position to insert at
            entry: Changelog entry

        Returns:
            Updated content
        """
        # Format entry as markdown
        entry_text = entry.to_markdown()

        # Determine insertion text
        if self.config.insert_at_top:
            # Insert at the top (right after heading)
            # Add blank line before entry if content doesn't start with one
            if position < len(content) and content[position] != "\n":
                insertion = f"\n{entry_text}\n"
            else:
                insertion = f"{entry_text}\n"
        else:
            # Insert at the bottom (before next heading or end)
            insertion = f"{entry_text}\n"

        # Insert the entry
        new_content = content[:position] + insertion + content[position:]

        return new_content

    def _limit_entries(self, content: str, heading_position: int) -> str:
        """
        Limit the number of changelog entries.

        Args:
            content: Content with entries
            heading_position: Position of the changelog heading

        Returns:
            Content with limited entries
        """
        if not self.config.max_entries:
            return content

        # Find all entries after the heading
        lines = content[heading_position:].split("\n")

        # Pattern to match changelog entries (date format: YYYY年MM月DD日)
        entry_pattern = r'^\d{4}年\d{2}月\d{2}日\s+'

        entry_lines = []
        other_lines = []
        entry_count = 0

        for line in lines:
            if re.match(entry_pattern, line):
                entry_count += 1
                if entry_count <= self.config.max_entries:
                    entry_lines.append(line)
            else:
                # Check if we've passed all entries
                if entry_count > 0 and not re.match(entry_pattern, line):
                    # This is content after entries
                    other_lines.append(line)
                elif entry_count == 0:
                    # This is content before first entry
                    entry_lines.append(line)

        # Reconstruct content
        new_section = "\n".join(entry_lines)
        if other_lines:
            new_section += "\n" + "\n".join(other_lines)

        return content[:heading_position] + new_section

    def create_changelog_section(self, heading: Optional[str] = None) -> str:
        """
        Create a new changelog section.

        Args:
            heading: Optional custom heading

        Returns:
            Markdown text for changelog section
        """
        heading = heading or self.config.heading_marker
        return f"{heading}\n\n"

    def append_to_file(
        self,
        file_path: str,
        entry: ChangelogEntry,
    ) -> Tuple[bool, str]:
        """
        Append changelog entry to end of file.

        Args:
            file_path: Path to file
            entry: Changelog entry

        Returns:
            Tuple of (success, message)
        """
        path = Path(file_path)

        try:
            # Read existing content
            if path.exists():
                content = path.read_text(encoding="utf-8")
            else:
                content = ""

            # Append entry
            if content and not content.endswith("\n"):
                content += "\n"

            content += entry.to_markdown() + "\n"

            # Write back
            path.write_text(content, encoding="utf-8")

            return True, f"Successfully appended to {file_path}"

        except Exception as e:
            return False, f"Failed to append to file: {e}"

    def validate_markdown(self, content: str) -> Tuple[bool, str]:
        """
        Validate markdown content.

        Args:
            content: Markdown content

        Returns:
            Tuple of (is_valid, message)
        """
        # Check for basic markdown structure
        if not content.strip():
            return False, "Content is empty"

        # Check for at least one heading
        if not re.search(r'^#+\s+', content, re.MULTILINE):
            return False, "No headings found"

        return True, "Valid markdown"
