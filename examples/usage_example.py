"""示例：如何在 Python 代码中使用 MCP Doc Updater"""

from src.mcp_doc_updater.git_analyzer import GitAnalyzer
from src.mcp_doc_updater.diff_filter import DiffFilter
from src.mcp_doc_updater.changelog_generator import ChangelogGenerator
from src.mcp_doc_updater.markdown_updater import MarkdownUpdater
from src.mcp_doc_updater.utils import auto_detect_paths
from src.mcp_doc_updater.models import (
    ComparisonMode,
    FilterConfig,
    MarkdownUpdateConfig,
    ChangeImportance,
)


def auto_detect_example():
    """使用自动检测功能的示例"""

    # 1. 自动检测 Git 仓库和 README 文件
    repo_path, readme_path = auto_detect_paths()

    if not repo_path:
        print("✗ 未找到 Git 仓库")
        return

    if not readme_path:
        print("✗ 未找到 README 文件")
        return

    print(f"✓ 自动检测到仓库: {repo_path}")
    print(f"✓ 自动检测到 README: {readme_path}")

    # 2. 创建过滤配置
    filter_config = FilterConfig(
        min_importance=ChangeImportance.NORMAL,
        token_budget=2000,
    )

    # 3. 分析 Git 变化
    analyzer = GitAnalyzer(str(repo_path), filter_config)
    analysis = analyzer.analyze_changes(
        mode=ComparisonMode.LATEST_VS_PREVIOUS
    )

    print(f"发现 {len(analysis.changes)} 个文件变化")

    # 4. 过滤变化
    diff_filter = DiffFilter(filter_config)
    filtered_changes = diff_filter.filter_changes(analysis.changes)

    print(f"过滤后剩余 {len(filtered_changes)} 个重要变化")

    # 5. 更新分析结果
    analysis.changes = filtered_changes

    # 6. 生成更新日志条目
    generator = ChangelogGenerator()
    entry = generator.generate_from_analysis(
        analysis,
        use_smart_summary=True
    )

    print(f"生成的日志条目：{entry.to_markdown()}")

    # 7. 更新 README
    markdown_config = MarkdownUpdateConfig(
        heading_marker="## 更新日志",
        insert_at_top=True,
    )

    updater = MarkdownUpdater(markdown_config)
    success, message = updater.update_readme(str(readme_path), entry)

    if success:
        print(f"✓ 成功更新 README: {message}")
    else:
        print(f"✗ 更新失败: {message}")


def update_changelog_example():
    """完整的更新日志示例（手动指定路径）"""

    # 1. 配置
    repo_path = "E:\\Develop\\Project\\MyProject"
    readme_path = "E:\\Develop\\Project\\MyProject\\README.md"

    # 2. 创建过滤配置
    filter_config = FilterConfig(
        min_importance=ChangeImportance.NORMAL,  # 只保留普通及以上重要性的变化
        token_budget=2000,  # 限制 token 使用
    )

    # 3. 分析 Git 变化
    analyzer = GitAnalyzer(repo_path, filter_config)
    analysis = analyzer.analyze_changes(
        mode=ComparisonMode.LATEST_VS_PREVIOUS  # 比较最新和上一个 commit
    )

    print(f"发现 {len(analysis.changes)} 个文件变化")

    # 4. 过滤变化
    diff_filter = DiffFilter(filter_config)
    filtered_changes = diff_filter.filter_changes(analysis.changes)

    print(f"过滤后剩余 {len(filtered_changes)} 个重要变化")

    # 5. 更新分析结果
    analysis.changes = filtered_changes

    # 6. 生成更新日志条目
    generator = ChangelogGenerator()
    entry = generator.generate_from_analysis(
        analysis,
        use_smart_summary=True  # 使用智能摘要
    )

    print(f"生成的日志条目：{entry.to_markdown()}")

    # 7. 更新 README
    markdown_config = MarkdownUpdateConfig(
        heading_marker="## 更新日志",  # 在这个标题下插入
        insert_at_top=True,  # 插入到顶部
    )

    updater = MarkdownUpdater(markdown_config)
    success, message = updater.update_readme(readme_path, entry)

    if success:
        print(f"✓ 成功更新 README: {message}")
    else:
        print(f"✗ 更新失败: {message}")


def simple_example():
    """简单示例：只使用默认配置"""

    from src.mcp_doc_updater.git_analyzer import GitAnalyzer
    from src.mcp_doc_updater.changelog_generator import ChangelogGenerator
    from src.mcp_doc_updater.markdown_updater import MarkdownUpdater

    # 分析变化
    analyzer = GitAnalyzer("E:\\Develop\\Project\\MyProject")
    analysis = analyzer.analyze_changes()

    # 生成日志
    generator = ChangelogGenerator()
    entry = generator.generate_from_analysis(analysis)

    # 更新 README
    updater = MarkdownUpdater()
    success, message = updater.update_readme(
        "E:\\Develop\\Project\\MyProject\\README.md",
        entry
    )

    print(message)


if __name__ == "__main__":
    # 运行自动检测示例（推荐）
    auto_detect_example()

    # 或运行完整示例
    # update_changelog_example()

    # 或运行简单示例
    # simple_example()
