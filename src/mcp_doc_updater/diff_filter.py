"""智能差异过滤，在保留重要变化的同时减少令牌使用量。"""

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
    """过滤和处理差异以提取重要变化。"""

    def __init__(self, config: FilterConfig):
        """
        初始化差异过滤器。

        Args:
            config: 过滤器配置
        """
        self.config = config

    def filter_changes(self, changes: List[CodeChange]) -> List[CodeChange]:
        """
        根据配置过滤和处理变化。

        Args:
            changes: 代码变化列表

        Returns:
            过滤后的代码变化列表
        """
        filtered = []

        for change in changes:
            # 评估重要性
            self._assess_importance(change)

            # 如果低于最小重要性则跳过
            if self._importance_level(change.importance) < self._importance_level(self.config.min_importance):
                continue

            # 提取语义信息
            self._extract_semantic_info(change)

            # 压缩差异文本
            change.diff_text = self._compress_diff(change.diff_text)

            # 生成摘要
            change.summary = self._generate_change_summary(change)

            filtered.append(change)

        # 按重要性排序
        filtered.sort(key=lambda c: self._importance_level(c.importance), reverse=True)

        # 如果指定了令牌预算则应用
        if self.config.token_budget:
            filtered = self._apply_token_budget(filtered, self.config.token_budget)

        return filtered

    def _assess_importance(self, change: CodeChange) -> None:
        """
        评估代码变化的重要性。

        Args:
            change: 要评估的 CodeChange（就地修改）
        """
        diff_lines = change.diff_text.split("\n")
        importance_score = 0

        for line in diff_lines:
            if not line.startswith(("+", "-")):
                continue

            # 移除 +/- 前缀
            content = line[1:].strip()

            if not content:
                continue

            # 跳过琐碎的变化
            if self.config.ignore_whitespace and is_whitespace_only(content):
                continue

            if self.config.ignore_comments and is_comment_line(content):
                continue

            if self.config.ignore_imports and is_import_line(content):
                continue

            # 评估行的重要性
            line_importance = self._assess_line_importance(content)
            importance_score += line_importance

        # 确定整体重要性
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
        评估单行的重要性。

        Args:
            line: 要评估的行

        Returns:
            重要性分数（越高越重要）
        """
        score = 1  # 基础分数

        # 关键模式
        critical_patterns = [
            r'\bdef\s+\w+\s*\(',           # 函数定义
            r'\bclass\s+\w+',              # 类定义
            r'\basync\s+def\s+\w+',        # 异步函数
            r'\breturn\s+',                # 返回语句
            r'\braise\s+',                 # 抛出异常
            r'\bthrow\s+',                 # JavaScript throw
            r'\bexport\s+',                # 导出语句
            r'\bpublic\s+',                # 公共修饰符
            r'\bprivate\s+',               # 私有修饰符
        ]

        for pattern in critical_patterns:
            if re.search(pattern, line):
                score += 3
                break

        # 重要模式
        important_patterns = [
            r'\bif\s+',                    # 条件语句
            r'\bfor\s+',                   # 循环
            r'\bwhile\s+',                 # 循环
            r'\btry\s*:',                  # try 块
            r'\bcatch\s*\(',               # catch 块
            r'\bawait\s+',                 # await
            r'=\s*\w+\(',                  # 函数调用赋值
        ]

        for pattern in important_patterns:
            if re.search(pattern, line):
                score += 2
                break

        # 扣除琐碎模式的分数
        trivial_patterns = [
            r'^\s*$',                      # 空行
            r'^\s*#',                      # 注释
            r'^\s*//',                     # 注释
            r'^\s*console\.log',           # 调试日志
            r'^\s*print\(',                # 调试打印
        ]

        for pattern in trivial_patterns:
            if re.search(pattern, line):
                score = 0
                break

        return score

    def _extract_semantic_info(self, change: CodeChange) -> None:
        """
        从差异中提取语义信息。

        Args:
            change: 要分析的 CodeChange（就地修改）
        """
        diff_lines = change.diff_text.split("\n")

        for line in diff_lines:
            if not line.startswith(("+", "-")):
                continue

            prefix = line[0]
            content = line[1:]

            # 提取函数名
            func_name = extract_function_name(content)
            if func_name:
                if prefix == "+":
                    change.functions_added.append(func_name)
                elif prefix == "-":
                    change.functions_deleted.append(func_name)

            # 提取类名
            class_name = extract_class_name(content)
            if class_name:
                if prefix == "+":
                    change.classes_added.append(class_name)

    def _compress_diff(self, diff_text: str) -> str:
        """
        通过删除不必要的上下文来压缩差异文本。

        Args:
            diff_text: 原始差异文本

        Returns:
            压缩后的差异文本
        """
        lines = diff_text.split("\n")
        compressed_lines = []
        context_buffer = []
        last_change_index = -1

        for i, line in enumerate(lines):
            # 保留头部行
            if line.startswith(("diff --git", "index", "---", "+++")):
                compressed_lines.append(line)
                continue

            # 保留块头部
            if line.startswith("@@"):
                compressed_lines.append(line)
                context_buffer = []
                continue

            # 检查这是否是变化行
            is_change = line.startswith(("+", "-"))

            if is_change:
                # 在此变化之前添加缓冲的上下文
                if context_buffer and (last_change_index == -1 or i - last_change_index > self.config.max_context_lines):
                    # 只添加最后 N 行上下文
                    compressed_lines.extend(context_buffer[-self.config.max_context_lines:])
                else:
                    compressed_lines.extend(context_buffer)

                context_buffer = []
                compressed_lines.append(line)
                last_change_index = i
            else:
                # 这是上下文行
                if last_change_index != -1 and i - last_change_index <= self.config.max_context_lines:
                    # 在最后一次变化的上下文窗口内
                    compressed_lines.append(line)
                else:
                    # 缓冲此上下文行
                    context_buffer.append(line)

                    # 如果缓冲区太大，清空它
                    if len(context_buffer) > self.config.max_context_lines * 2:
                        context_buffer = []

        return "\n".join(compressed_lines)

    def _generate_change_summary(self, change: CodeChange) -> str:
        """
        生成变化的可读摘要。

        Args:
            change: 要总结的 CodeChange

        Returns:
            摘要字符串
        """
        parts = []

        # 文件和变化类型
        parts.append(f"{change.change_type.value}: {change.file_path}")

        # 函数
        if change.functions_added:
            parts.append(f"新增函数: {', '.join(change.functions_added)}")
        if change.functions_modified:
            parts.append(f"修改函数: {', '.join(change.functions_modified)}")
        if change.functions_deleted:
            parts.append(f"删除函数: {', '.join(change.functions_deleted)}")

        # 类
        if change.classes_added:
            parts.append(f"新增类: {', '.join(change.classes_added)}")
        if change.classes_modified:
            parts.append(f"修改类: {', '.join(change.classes_modified)}")

        # 行数
        if change.line_count > 0:
            parts.append(f"({change.line_count} 行变化)")

        return " | ".join(parts)

    def _apply_token_budget(self, changes: List[CodeChange], budget: int) -> List[CodeChange]:
        """
        通过截断变化列表来应用令牌预算。

        Args:
            changes: 变化列表（应按重要性排序）
            budget: 令牌预算

        Returns:
            截断后的变化列表
        """
        total_tokens = 0
        result = []

        for change in changes:
            change_tokens = count_tokens_estimate(change.diff_text)

            if total_tokens + change_tokens > budget:
                # 尝试至少包含摘要
                summary_tokens = count_tokens_estimate(change.summary or "")
                if total_tokens + summary_tokens <= budget:
                    # 仅用摘要替换差异
                    change.diff_text = f"(仅摘要 - 超出令牌预算)\n{change.summary}"
                    result.append(change)
                    total_tokens += summary_tokens
                break

            result.append(change)
            total_tokens += change_tokens

        return result

    def _importance_level(self, importance: ChangeImportance) -> int:
        """将重要性枚举转换为数字级别。"""
        levels = {
            ChangeImportance.CRITICAL: 4,
            ChangeImportance.IMPORTANT: 3,
            ChangeImportance.NORMAL: 2,
            ChangeImportance.TRIVIAL: 1,
        }
        return levels.get(importance, 0)


class TokenOptimizer:
    """优化变化的令牌使用量。"""

    @staticmethod
    def create_compact_summary(changes: List[CodeChange]) -> str:
        """
        创建所有变化的紧凑摘要。

        Args:
            changes: 代码变化列表

        Returns:
            紧凑摘要字符串
        """
        if not changes:
            return "无变化"

        # 按变化类型分组
        by_type = {}
        for change in changes:
            change_type = change.change_type.value
            if change_type not in by_type:
                by_type[change_type] = []
            by_type[change_type].append(change)

        summary_parts = []

        # 总结每种类型
        for change_type, type_changes in by_type.items():
            files = [c.file_path for c in type_changes]
            if len(files) <= 3:
                file_list = ", ".join(files)
            else:
                file_list = f"{', '.join(files[:3])} 等{len(files)}个文件"

            summary_parts.append(f"{change_type}: {file_list}")

        return "; ".join(summary_parts)
