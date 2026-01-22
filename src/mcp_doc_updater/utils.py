"""Utility functions for MCP Doc Updater."""

import os
import re
from pathlib import Path
from typing import Optional, Tuple
from fnmatch import fnmatch


def should_ignore_file(file_path: str, ignore_patterns: list[str]) -> bool:
    """
    Check if a file should be ignored based on patterns.

    Args:
        file_path: Path to the file
        ignore_patterns: List of glob patterns to ignore

    Returns:
        True if file should be ignored
    """
    file_path_normalized = file_path.replace("\\", "/")

    for pattern in ignore_patterns:
        if fnmatch(file_path_normalized, pattern):
            return True
        # Also check if any parent directory matches
        parts = file_path_normalized.split("/")
        for i in range(len(parts)):
            partial_path = "/".join(parts[:i+1])
            if fnmatch(partial_path, pattern):
                return True

    return False


def is_whitespace_only(line: str) -> bool:
    """Check if a line contains only whitespace."""
    return len(line.strip()) == 0


def is_comment_line(line: str, language: Optional[str] = None) -> bool:
    """
    Check if a line is a comment.

    Args:
        line: The line to check
        language: Optional language hint (python, javascript, etc.)

    Returns:
        True if line is a comment
    """
    stripped = line.strip()

    # Common comment patterns
    comment_patterns = [
        r'^#',           # Python, Shell
        r'^//',          # JavaScript, C++, Java
        r'^/\*',         # C-style block comment start
        r'^\*',          # C-style block comment continuation
        r'^\*/',         # C-style block comment end
        r'^<!--',        # HTML/XML
        r'^"""',         # Python docstring
        r"^'''",         # Python docstring
    ]

    for pattern in comment_patterns:
        if re.match(pattern, stripped):
            return True

    return False


def is_import_line(line: str) -> bool:
    """Check if a line is an import statement."""
    stripped = line.strip()

    import_patterns = [
        r'^import\s+',
        r'^from\s+.+\s+import\s+',
        r'^require\(',
        r'^const\s+.+\s*=\s*require\(',
        r'^import\s+.+\s+from\s+',
    ]

    for pattern in import_patterns:
        if re.match(pattern, stripped):
            return True

    return False


def extract_function_name(line: str) -> Optional[str]:
    """
    Extract function name from a function definition line.

    Args:
        line: The line to analyze

    Returns:
        Function name if found, None otherwise
    """
    # Python function
    match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
    if match:
        return match.group(1)

    # JavaScript/TypeScript function
    match = re.search(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
    if match:
        return match.group(1)

    # Arrow function with name
    match = re.search(r'(?:const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\(', line)
    if match:
        return match.group(1)

    return None


def extract_class_name(line: str) -> Optional[str]:
    """
    Extract class name from a class definition line.

    Args:
        line: The line to analyze

    Returns:
        Class name if found, None otherwise
    """
    # Python/JavaScript/TypeScript class
    match = re.search(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
    if match:
        return match.group(1)

    return None


def count_tokens_estimate(text: str) -> int:
    """
    Estimate token count for text.
    Rough approximation: ~4 characters per token.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4


def truncate_text(text: str, max_tokens: int) -> str:
    """
    Truncate text to fit within token budget.

    Args:
        text: Text to truncate
        max_tokens: Maximum tokens allowed

    Returns:
        Truncated text with ellipsis if needed
    """
    estimated_tokens = count_tokens_estimate(text)

    if estimated_tokens <= max_tokens:
        return text

    # Calculate how many characters we can keep
    max_chars = max_tokens * 4

    if len(text) <= max_chars:
        return text

    # Truncate and add ellipsis
    return text[:max_chars - 10] + "\n...\n(truncated)"


def normalize_path(path: str) -> str:
    """
    Normalize a file path for consistent comparison.

    Args:
        path: Path to normalize

    Returns:
        Normalized path
    """
    return str(Path(path).as_posix())


def get_file_extension(file_path: str) -> str:
    """
    Get file extension from path.

    Args:
        file_path: Path to file

    Returns:
        File extension (without dot)
    """
    return Path(file_path).suffix.lstrip(".")


def is_code_file(file_path: str) -> bool:
    """
    Check if file is a code file based on extension.

    Args:
        file_path: Path to file

    Returns:
        True if file is a code file
    """
    code_extensions = {
        "py", "js", "ts", "jsx", "tsx", "java", "c", "cpp", "h", "hpp",
        "cs", "go", "rs", "rb", "php", "swift", "kt", "scala", "r",
        "m", "mm", "sh", "bash", "zsh", "fish", "ps1", "sql", "html",
        "css", "scss", "sass", "less", "vue", "svelte", "dart", "lua",
    }

    ext = get_file_extension(file_path)
    return ext.lower() in code_extensions


def find_git_repo() -> Optional[Path]:
    """
    Find the Git repository by searching upward from current directory.

    Returns:
        Path to Git repository root, or None if not found
    """
    current = Path.cwd()

    # Search upward for .git directory
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    # Check root directory
    if (current / ".git").exists():
        return current

    return None


def find_readme_file(repo_path: Path) -> Optional[Path]:
    """
    Find README file in the repository.

    Args:
        repo_path: Path to Git repository

    Returns:
        Path to README file, or None if not found
    """
    # Common README file names (case-insensitive)
    readme_names = [
        "README.md",
        "readme.md",
        "Readme.md",
        "README.MD",
        "README",
        "readme",
        "README.txt",
        "readme.txt",
        "README.rst",
        "readme.rst",
    ]

    for name in readme_names:
        readme_path = repo_path / name
        if readme_path.exists():
            return readme_path

    return None


def find_changelog_heading(readme_path: Path) -> Optional[str]:
    """
    Find existing changelog heading in README file.

    Args:
        readme_path: Path to README file

    Returns:
        Changelog heading marker if found, None otherwise
    """
    if not readme_path.exists():
        return None

    try:
        content = readme_path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Common changelog heading patterns (case-insensitive)
    changelog_patterns = [
        r'^(#{1,6}\s*更新日志)',
        r'^(#{1,6}\s*Changelog)',
        r'^(#{1,6}\s*CHANGELOG)',
        r'^(#{1,6}\s*Change Log)',
        r'^(#{1,6}\s*变更日志)',
        r'^(#{1,6}\s*版本历史)',
        r'^(#{1,6}\s*Version History)',
        r'^(#{1,6}\s*Release Notes)',
        r'^(#{1,6}\s*发布说明)',
    ]

    for line in content.split('\n'):
        line = line.strip()
        for pattern in changelog_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1)

    return None


def auto_detect_paths() -> Tuple[Optional[Path], Optional[Path]]:
    """
    Auto-detect Git repository and README file paths.

    Returns:
        Tuple of (repo_path, readme_path), either can be None if not found
    """
    repo_path = find_git_repo()
    if not repo_path:
        return None, None

    readme_path = find_readme_file(repo_path)
    return repo_path, readme_path
