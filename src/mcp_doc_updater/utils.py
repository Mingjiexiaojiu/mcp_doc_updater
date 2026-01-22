"""MCP Doc Updater 的工具函数。"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from fnmatch import fnmatch


def should_ignore_file(file_path: str, ignore_patterns: list[str]) -> bool:
    """
    根据模式检查文件是否应该被忽略。

    参数:
        file_path: 文件路径
        ignore_patterns: 要忽略的 glob 模式列表

    返回:
        如果文件应该被忽略则返回 True
    """
    file_path_normalized = file_path.replace("\\", "/")

    for pattern in ignore_patterns:
        if fnmatch(file_path_normalized, pattern):
            return True
        # 同时检查任何父目录是否匹配
        parts = file_path_normalized.split("/")
        for i in range(len(parts)):
            partial_path = "/".join(parts[:i+1])
            if fnmatch(partial_path, pattern):
                return True

    return False


def is_whitespace_only(line: str) -> bool:
    """检查一行是否只包含空白字符。"""
    return len(line.strip()) == 0


def is_comment_line(line: str, language: Optional[str] = None) -> bool:
    """
    检查一行是否是注释。

    参数:
        line: 要检查的行
        language: 可选的语言提示（python、javascript 等）

    返回:
        如果是注释行则返回 True
    """
    stripped = line.strip()

    # 常见的注释模式
    comment_patterns = [
        r'^#',           # Python, Shell
        r'^//',          # JavaScript, C++, Java
        r'^/\*',         # C 风格块注释开始
        r'^\*',          # C 风格块注释延续
        r'^\*/',         # C 风格块注释结束
        r'^<!--',        # HTML/XML
        r'^"""',         # Python 文档字符串
        r"^'''",         # Python 文档字符串
    ]

    for pattern in comment_patterns:
        if re.match(pattern, stripped):
            return True

    return False


def is_import_line(line: str) -> bool:
    """检查一行是否是导入语句。"""
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
    从函数定义行中提取函数名。

    参数:
        line: 要分析的行

    返回:
        如果找到则返回函数名，否则返回 None
    """
    # Python 函数
    match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
    if match:
        return match.group(1)

    # JavaScript/TypeScript 函数
    match = re.search(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
    if match:
        return match.group(1)

    # 带名称的箭头函数
    match = re.search(r'(?:const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\(', line)
    if match:
        return match.group(1)

    return None


def extract_class_name(line: str) -> Optional[str]:
    """
    从类定义行中提取类名。

    参数:
        line: 要分析的行

    返回:
        如果找到则返回类名，否则返回 None
    """
    # Python/JavaScript/TypeScript 类
    match = re.search(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
    if match:
        return match.group(1)

    return None


def count_tokens_estimate(text: str) -> int:
    """
    估算文本的 token 数量。
    粗略近似：约每 4 个字符一个 token。

    参数:
        text: 要估算的文本

    返回:
        估算的 token 数量
    """
    return len(text) // 4


def truncate_text(text: str, max_tokens: int) -> str:
    """
    截断文本以适应 token 预算。

    参数:
        text: 要截断的文本
        max_tokens: 允许的最大 token 数

    返回:
        如果需要则带省略号的截断文本
    """
    estimated_tokens = count_tokens_estimate(text)

    if estimated_tokens <= max_tokens:
        return text

    # 计算我们可以保留多少字符
    max_chars = max_tokens * 4

    if len(text) <= max_chars:
        return text

    # 截断并添加省略号
    return text[:max_chars - 10] + "\n...\n(truncated)"


def normalize_path(path: str) -> str:
    """
    规范化文件路径以便一致比较。

    参数:
        path: 要规范化的路径

    返回:
        规范化的路径
    """
    return str(Path(path).as_posix())


def get_file_extension(file_path: str) -> str:
    """
    从路径获取文件扩展名。

    参数:
        file_path: 文件路径

    返回:
        文件扩展名（不带点）
    """
    return Path(file_path).suffix.lstrip(".")


def is_code_file(file_path: str) -> bool:
    """
    根据扩展名检查文件是否是代码文件。

    参数:
        file_path: 文件路径

    返回:
        如果是代码文件则返回 True
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
    通过从当前目录向上搜索来查找 Git 仓库。

    返回:
        Git 仓库根目录的路径，如果未找到则返回 None
    """
    current = Path.cwd()

    # 向上搜索 .git 目录
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    # 检查根目录
    if (current / ".git").exists():
        return current

    return None


def find_readme_file(repo_path: Path) -> Optional[Path]:
    """
    在仓库中查找 README 文件。

    参数:
        repo_path: Git 仓库路径

    返回:
        README 文件的路径，如果未找到则返回 None
    """
    # 常见的 README 文件名（不区分大小写）
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


def has_working_tree_changes(repo_path: Path) -> bool:
    """
    检查工作树中是否有未提交的变化。

    参数:
        repo_path: Git 仓库路径

    返回:
        如果有未提交的变化（已暂存或未暂存）则返回 True
    """
    try:
        # 运行 git status --porcelain 检查变化
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=True,
        )

        # 如果输出不为空，则有变化
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        # 如果 git 命令失败，假设没有变化
        return False
    except Exception:
        # 如果发生任何其他错误，假设没有变化
        return False


def auto_detect_comparison_mode(repo_path: Path) -> str:
    """
    根据仓库状态自动检测合适的比较模式。

    逻辑:
    - 如果工作树有变化：使用 "working_tree_vs_head"（比较未提交的变化）
    - 如果工作树干净：使用 "latest_vs_previous"（比较最近两次提交）

    参数:
        repo_path: Git 仓库路径

    返回:
        比较模式字符串
    """
    if has_working_tree_changes(repo_path):
        return "working_tree_vs_head"
    else:
        return "latest_vs_previous"


def find_changelog_heading(readme_path: Path) -> Optional[str]:
    """
    在 README 文件中查找现有的更新日志标题。

    参数:
        readme_path: README 文件路径

    返回:
        如果找到则返回更新日志标题标记，否则返回 None
    """
    if not readme_path.exists():
        return None

    try:
        content = readme_path.read_text(encoding="utf-8")
    except Exception:
        return None

    # 常见的更新日志标题模式（不区分大小写）
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
    自动检测 Git 仓库和 README 文件路径。

    返回:
        (repo_path, readme_path) 的元组，任一都可能为 None（如果未找到）
    """
    repo_path = find_git_repo()
    if not repo_path:
        return None, None

    readme_path = find_readme_file(repo_path)
    return repo_path, readme_path
