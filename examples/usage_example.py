"""示例：如何在 Python 代码中使用 MCP Doc Updater"""

from src.mcp_doc_updater.git_analyzer import GitAnalyzer
from src.mcp_doc_updater.diff_filter import DiffFilter
from src.mcp_doc_updater.prompt_generator import PromptGenerator
from src.mcp_doc_updater.utils import auto_detect_paths, auto_detect_comparison_mode
from src.mcp_doc_updater.models import (
    ComparisonMode,
    FilterConfig,
    ChangeImportance,
)


def auto_detect_example():
    """使用自动检测功能的示例"""

    # 1. 自动检测 Git 仓库
    repo_path, _ = auto_detect_paths()

    if not repo_path:
        print("✗ 未找到 Git 仓库")
        return

    print(f"✓ 自动检测到仓库: {repo_path}")

    # 2. 自动检测比较模式
    comparison_mode_str = auto_detect_comparison_mode(repo_path)
    comparison_mode = ComparisonMode(comparison_mode_str)
    print(f"✓ 自动检测到比较模式: {comparison_mode.value}")

    # 3. 创建过滤配置
    filter_config = FilterConfig(
        min_importance=ChangeImportance.NORMAL,
        token_budget=2000,
    )

    # 4. 分析 Git 变化
    analyzer = GitAnalyzer(str(repo_path), filter_config)
    analysis = analyzer.analyze_changes(mode=comparison_mode)

    print(f"✓ 发现 {len(analysis.changes)} 个文件变化")

    if not analysis.changes:
        print("✗ 未检测到变化")
        return

    # 5. 过滤变化
    diff_filter = DiffFilter(filter_config)
    filtered_changes = diff_filter.filter_changes(analysis.changes)

    print(f"✓ 过滤后剩余 {len(filtered_changes)} 个重要变化")

    if not filtered_changes:
        print("✗ 过滤后没有重要变化")
        return

    # 6. 更新分析结果
    analysis.changes = filtered_changes

    # 7. 生成提示词
    generator = PromptGenerator(max_diff_lines=50)
    prompt = generator.generate_from_analysis(
        analysis,
        include_diff=True,
        language="zh"
    )

    print("\n" + "="*80)
    print("生成的提示词：")
    print("="*80)
    print(prompt)
    print("="*80)
    print("\n💡 提示：将上面的提示词发送给 AI（如 Claude），让 AI 生成更新日志条目")


def generate_prompt_example():
    """完整的提示词生成示例（手动指定路径）"""

    # 1. 配置
    repo_path = "E:\\Develop\\Project\\MyProject"

    # 2. 创建过滤配置
    filter_config = FilterConfig(
        min_importance=ChangeImportance.NORMAL,  # 只保留普通及以上重要性的变化
        token_budget=2000,  # 限制 token 使用
        ignore_whitespace=True,  # 忽略空白变化
        ignore_comments=False,  # 不忽略注释变化
    )

    # 3. 分析 Git 变化
    analyzer = GitAnalyzer(repo_path, filter_config)
    analysis = analyzer.analyze_changes(
        mode=ComparisonMode.LATEST_VS_PREVIOUS  # 比较最新和上一个 commit
    )

    print(f"✓ 发现 {len(analysis.changes)} 个文件变化")

    if not analysis.changes:
        print("✗ 未检测到变化")
        return

    # 4. 过滤变化
    diff_filter = DiffFilter(filter_config)
    filtered_changes = diff_filter.filter_changes(analysis.changes)

    print(f"✓ 过滤后剩余 {len(filtered_changes)} 个重要变化")

    if not filtered_changes:
        print("✗ 过滤后没有重要变化")
        return

    # 5. 更新分析结果
    analysis.changes = filtered_changes

    # 6. 生成中文提示词
    generator = PromptGenerator(max_diff_lines=50)
    prompt = generator.generate_from_analysis(
        analysis,
        include_diff=True,  # 包含 diff 内容
        language="zh"  # 中文提示词
    )

    print("\n" + "="*80)
    print("生成的中文提示词：")
    print("="*80)
    print(prompt)
    print("="*80)


def english_prompt_example():
    """生成英文提示词的示例"""

    # 1. 自动检测仓库
    repo_path, _ = auto_detect_paths()

    if not repo_path:
        print("✗ Repository not found")
        return

    print(f"✓ Repository detected: {repo_path}")

    # 2. 配置
    filter_config = FilterConfig(
        min_importance=ChangeImportance.NORMAL,
        token_budget=2000,
    )

    # 3. 分析变化
    analyzer = GitAnalyzer(str(repo_path), filter_config)
    analysis = analyzer.analyze_changes(mode=ComparisonMode.LATEST_VS_PREVIOUS)

    print(f"✓ Found {len(analysis.changes)} file changes")

    if not analysis.changes:
        print("✗ No changes detected")
        return

    # 4. 过滤变化
    diff_filter = DiffFilter(filter_config)
    filtered_changes = diff_filter.filter_changes(analysis.changes)

    print(f"✓ {len(filtered_changes)} important changes after filtering")

    if not filtered_changes:
        print("✗ No important changes after filtering")
        return

    # 5. 更新分析结果
    analysis.changes = filtered_changes

    # 6. 生成英文提示词
    generator = PromptGenerator(max_diff_lines=50)
    prompt = generator.generate_from_analysis(
        analysis,
        include_diff=True,
        language="en"  # English prompt
    )

    print("\n" + "="*80)
    print("Generated English Prompt:")
    print("="*80)
    print(prompt)
    print("="*80)


def simple_example():
    """简单示例：只使用默认配置"""

    from src.mcp_doc_updater.git_analyzer import GitAnalyzer
    from src.mcp_doc_updater.prompt_generator import PromptGenerator

    # 分析变化
    analyzer = GitAnalyzer("E:\\Develop\\Project\\MyProject")
    analysis = analyzer.analyze_changes()

    if not analysis.changes:
        print("未检测到变化")
        return

    # 生成提示词
    generator = PromptGenerator()
    prompt = generator.generate_from_analysis(analysis)

    print(prompt)


def working_tree_example():
    """比较工作区变化的示例"""

    # 1. 自动检测仓库
    repo_path, _ = auto_detect_paths()

    if not repo_path:
        print("✗ 未找到 Git 仓库")
        return

    print(f"✓ 自动检测到仓库: {repo_path}")

    # 2. 配置
    filter_config = FilterConfig(
        min_importance=ChangeImportance.NORMAL,
        token_budget=3000,
    )

    # 3. 分析工作区变化（未提交的变化）
    analyzer = GitAnalyzer(str(repo_path), filter_config)
    analysis = analyzer.analyze_changes(
        mode=ComparisonMode.WORKING_TREE_VS_HEAD  # 比较工作区和 HEAD
    )

    print(f"✓ 发现 {len(analysis.changes)} 个未提交的文件变化")

    if not analysis.changes:
        print("✗ 工作区没有变化")
        return

    # 4. 过滤变化
    diff_filter = DiffFilter(filter_config)
    filtered_changes = diff_filter.filter_changes(analysis.changes)

    print(f"✓ 过滤后剩余 {len(filtered_changes)} 个重要变化")

    if not filtered_changes:
        print("✗ 过滤后没有重要变化")
        return

    # 5. 更新分析结果
    analysis.changes = filtered_changes

    # 6. 生成提示词（不包含 diff 内容，减少输出）
    generator = PromptGenerator(max_diff_lines=30)
    prompt = generator.generate_from_analysis(
        analysis,
        include_diff=False,  # 不包含 diff 内容
        language="zh"
    )

    print("\n" + "="*80)
    print("生成的提示词（不含 diff）：")
    print("="*80)
    print(prompt)
    print("="*80)


def custom_config_example():
    """自定义配置的示例"""

    # 1. 自动检测仓库
    repo_path, _ = auto_detect_paths()

    if not repo_path:
        print("✗ 未找到 Git 仓库")
        return

    print(f"✓ 自动检测到仓库: {repo_path}")

    # 2. 自定义过滤配置
    filter_config = FilterConfig(
        min_importance=ChangeImportance.IMPORTANT,  # 只保留重要及以上的变化
        token_budget=5000,  # 更大的 token 预算
        ignore_whitespace=True,
        ignore_comments=True,  # 忽略注释变化
        ignore_imports=True,  # 忽略 import 变化
        max_context_lines=5,  # 更多的上下文行
        ignore_patterns=[  # 自定义忽略模式
            "*.lock",
            "*.log",
            "*.pyc",
            "__pycache__/*",
            ".git/*",
            "dist/*",
            "build/*",
        ]
    )

    # 3. 分析变化
    analyzer = GitAnalyzer(str(repo_path), filter_config)
    analysis = analyzer.analyze_changes(mode=ComparisonMode.LATEST_VS_PREVIOUS)

    print(f"✓ 发现 {len(analysis.changes)} 个文件变化")

    if not analysis.changes:
        print("✗ 未检测到变化")
        return

    # 4. 过滤变化
    diff_filter = DiffFilter(filter_config)
    filtered_changes = diff_filter.filter_changes(analysis.changes)

    print(f"✓ 过滤后剩余 {len(filtered_changes)} 个重要变化")

    if not filtered_changes:
        print("✗ 过滤后没有重要变化")
        return

    # 5. 更新分析结果
    analysis.changes = filtered_changes

    # 6. 生成提示词（自定义 diff 行数）
    generator = PromptGenerator(max_diff_lines=100)  # 更多的 diff 行数
    prompt = generator.generate_from_analysis(
        analysis,
        include_diff=True,
        language="zh"
    )

    print("\n" + "="*80)
    print("生成的提示词（自定义配置）：")
    print("="*80)
    print(prompt)
    print("="*80)


def save_prompt_to_file_example():
    """将提示词保存到文件的示例"""

    # 1. 自动检测仓库
    repo_path, _ = auto_detect_paths()

    if not repo_path:
        print("✗ 未找到 Git 仓库")
        return

    print(f"✓ 自动检测到仓库: {repo_path}")

    # 2. 配置
    filter_config = FilterConfig(
        min_importance=ChangeImportance.NORMAL,
        token_budget=2000,
    )

    # 3. 分析变化
    analyzer = GitAnalyzer(str(repo_path), filter_config)
    analysis = analyzer.analyze_changes(mode=ComparisonMode.LATEST_VS_PREVIOUS)

    if not analysis.changes:
        print("✗ 未检测到变化")
        return

    # 4. 过滤变化
    diff_filter = DiffFilter(filter_config)
    filtered_changes = diff_filter.filter_changes(analysis.changes)

    if not filtered_changes:
        print("✗ 过滤后没有重要变化")
        return

    # 5. 更新分析结果
    analysis.changes = filtered_changes

    # 6. 生成提示词
    generator = PromptGenerator(max_diff_lines=50)
    prompt = generator.generate_from_analysis(
        analysis,
        include_diff=True,
        language="zh"
    )

    # 7. 保存到文件
    output_file = "changelog_prompt.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"✓ 提示词已保存到: {output_file}")
    print("💡 提示：你可以将文件内容复制并发送给 AI 来生成更新日志")


if __name__ == "__main__":
    print("MCP Doc Updater - 使用示例\n")

    # 运行自动检测示例（推荐）
    print("=" * 80)
    print("示例 1: 自动检测示例")
    print("=" * 80)
    auto_detect_example()

    # 或运行其他示例
    # print("\n" + "=" * 80)
    # print("示例 2: 完整配置示例")
    # print("=" * 80)
    # generate_prompt_example()

    # print("\n" + "=" * 80)
    # print("示例 3: 英文提示词示例")
    # print("=" * 80)
    # english_prompt_example()

    # print("\n" + "=" * 80)
    # print("示例 4: 简单示例")
    # print("=" * 80)
    # simple_example()

    # print("\n" + "=" * 80)
    # print("示例 5: 工作区变化示例")
    # print("=" * 80)
    # working_tree_example()

    # print("\n" + "=" * 80)
    # print("示例 6: 自定义配置示例")
    # print("=" * 80)
    # custom_config_example()

    # print("\n" + "=" * 80)
    # print("示例 7: 保存提示词到文件")
    # print("=" * 80)
    # save_prompt_to_file_example()