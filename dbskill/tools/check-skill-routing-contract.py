#!/usr/bin/env python3
"""静态检查当前目标编排与交接契约；实际行为需另做对话验收。"""

import json
import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT_DIR / ".claude-plugin" / "marketplace.json"
DBS_SKILL_PATH = ROOT_DIR / "skills" / "dbs" / "SKILL.md"
OFFICIAL_NAMES_PATH = (
    ROOT_DIR / "skills" / "dbs" / "references" / "official-skill-names.txt"
)

ROUTING_CONTRACT_MARKER = "## 跨 Skill 交接契约"
ENTRY_MARKERS = (
    "## 模式 B：任务编排与执行",
    "### 1．解读任务",
    "### 2．设计组合",
    "#### 动态拆解",
    "### 3．向用户说明组合",
    "### 4．执行与调整",
    "scripts/list-official-skills.py",
    "references/composition-contract.md",
)
COMPOSITION_MARKERS = (
    "## 二、动态拆解",
    "## 三、流程结构",
    "## 四、合并方式",
    "### 隔离对照",
    "## 六、交接包",
    "## 七、停止与调整",
)
# 防止重新引入已经移除的全局强制暂停与单一结论约束。
# 此处检查明确的旧指令，不能替代模型行为测试。
RETIRED_ENTRY_RULES = (
    "本轮不得执行入选 Skill",
    "提示词生成后立即结束当前轮次",
    "输出推荐和组合提示词后立即结束",
    "业务结论全部留给用户下一轮发送提示词后生成",
    "用户只有 1 个最终任务和 1 份最终交付物",
    "最终只交付一份由主 Skill 统领的结果",
)


def check_entry_contract(entry_text: str, composition_text: str) -> list[str]:
    errors = []
    for marker in ENTRY_MARKERS:
        if marker not in entry_text:
            errors.append(f"skills/dbs/SKILL.md 缺少当前目标编排章节或资源：{marker}")
    for marker in COMPOSITION_MARKERS:
        if marker not in composition_text:
            errors.append(f"多方法处理契约缺少章节：{marker}")
    for path, content in (("skills/dbs/SKILL.md", entry_text),
                          ("skills/dbs/references/composition-contract.md", composition_text)):
        for rule in RETIRED_ENTRY_RULES:
            if rule in content:
                errors.append(f"{path} 含已废弃的强制流程：{rule}")
    return errors
CONDITIONAL_NAVIGATION_MARKER = "不点名其他 Skill"

# 叶子 Skill 只描述还需要的能力，能力到 Skill 的匹配由 /dbs 完成。
# 以下点名属于工具依赖、共用存档格式或用法示例，新增 Skill 时无需修改。
ALLOWED_LEAF_MENTIONS = {
    "dbs-save": {"dbs-restore", "dbs-report", "dbs-diagnosis", "dbs-benchmark"},
    "dbs-restore": {"dbs-save", "dbs-report"},
    "dbs-report": {"dbs-save", "dbs-restore", "dbs-diagnosis"},
    "dbs-skill-maker": {"dbs-install-skill"},
    "dbs-install-skill": {"dbs-diagnosis"},
    "dbs-update": {"dbs-diagnosis"},
}


def find_leaf_mentions(name: str, text: str, formal_names: list[str]) -> list[tuple[int, str]]:
    """返回叶子 Skill 文本中点名其他正式叶子 Skill 的位置（行号, 被点名的 Skill）。"""
    others = [
        other
        for other in formal_names
        if other not in {"dbs", name} and other not in ALLOWED_LEAF_MENTIONS.get(name, set())
    ]
    if not others:
        return []
    pattern = re.compile(
        r"(?<![\w-])(" + "|".join(sorted(map(re.escape, others), key=len, reverse=True)) + r")(?![\w-])"
    )
    return [
        (line_number, match.group(1))
        for line_number, line in enumerate(text.splitlines(), start=1)
        for match in pattern.finditer(line)
    ]

DIRECT_HANDOFF_PATTERNS = (
    re.compile(r"(路由到|转到|交给|衔接)\s*[`*]*(/dbs-[a-z0-9-]+)"),
    re.compile(r"建议(?:你)?(?:先)?(?:用|去)\s*[`*]*(/dbs-[a-z0-9-]+)"),
    re.compile(r"试试\s*[`*]*(/dbs-[a-z0-9-]+)"),
)


def main() -> None:
    marketplace = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
    formal_names = [plugin["name"] for plugin in marketplace.get("plugins", [])]
    errors: list[str] = []

    snapshot_names = [
        line.strip()
        for line in OFFICIAL_NAMES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    expected_snapshot_names = [name for name in formal_names if name != "dbs"]
    if snapshot_names != expected_snapshot_names:
        errors.append(
            "skills/dbs/references/official-skill-names.txt "
            "与 Marketplace 正式条目顺序或内容不一致"
        )

    dbs_text = DBS_SKILL_PATH.read_text(encoding="utf-8")
    if ROUTING_CONTRACT_MARKER not in dbs_text:
        errors.append("skills/dbs/SKILL.md 缺少「跨 Skill 交接契约」")
    composition_path = DBS_SKILL_PATH.parent / "references/composition-contract.md"
    if not composition_path.is_file():
        errors.append("缺少 skills/dbs/references/composition-contract.md")
    else:
        errors.extend(check_entry_contract(dbs_text, composition_path.read_text(encoding="utf-8")))
    if "## 模式 B：任务后导航" in dbs_text or "### 导航地图" in dbs_text:
        errors.append("skills/dbs/SKILL.md 仍含旧版任务后静态导航")

    for name in formal_names:
        skill_path = ROOT_DIR / "skills" / name / "SKILL.md"
        if not skill_path.is_file():
            errors.append(f"正式 Skill 缺少定义文件：skills/{name}/SKILL.md")
            continue

        text = skill_path.read_text(encoding="utf-8")
        if name != "dbs" and CONDITIONAL_NAVIGATION_MARKER not in text:
            errors.append(f"skills/{name}/SKILL.md 缺少条件式 /dbs 导航规则")

        if name == "dbs":
            continue

        skill_dir = ROOT_DIR / "skills" / name
        for path in [skill_path, *sorted(skill_dir.glob("references/*.md"))]:
            for line_number, mentioned in find_leaf_mentions(
                name, path.read_text(encoding="utf-8"), formal_names
            ):
                errors.append(
                    f"{path.relative_to(ROOT_DIR)}:{line_number} 点名了其他 Skill {mentioned}；"
                    "叶子 Skill 只描述还需要的能力，由 /dbs 匹配具体 Skill"
                )

        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in DIRECT_HANDOFF_PATTERNS:
                match = pattern.search(line)
                if match:
                    errors.append(
                        f"skills/{name}/SKILL.md:{line_number} "
                        f"直接指定了下一站 {match.group(2)}：{line.strip()}"
                    )
                    break

    archive_contract_text = (
        ROOT_DIR / "shared" / "references" / "archive-contract.md"
    ).read_text(encoding="utf-8")
    if "只有用户已经明确选择下一个 Skill" not in archive_contract_text:
        errors.append("存档契约的 next_skill 字段缺少「用户明确选择」约束")

    restore_text = (ROOT_DIR / "skills" / "dbs-restore" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    if "用户说「就接着上次确认的下一步走」" not in restore_text:
        errors.append("dbs-restore 缺少用户明确确认 next_skill 后再接续的规则")

    guide_text = (ROOT_DIR / "docs" / "新手入门.md").read_text(encoding="utf-8")
    if "**常见衔接：**" in guide_text:
        errors.append("docs/新手入门.md 仍含直接指定下一站的「常见衔接」")
    repeated_guide_navigation = "**继续推进：** 完成本 Skill 后输入 `/dbs`。"
    if repeated_guide_navigation in guide_text:
        errors.append(
            "docs/新手入门.md 仍在每个 Skill 条目后重复动态导航提示"
        )
    shared_guide_navigation = (
        "完成任何 Skill 后，可以继续补充事实或直接说明下一步。"
    )
    if guide_text.count(shared_guide_navigation) != 1:
        errors.append("docs/新手入门.md 应且只能保留 1 处统一动态导航说明")

    retired_doc_rules = (
        "你发送该提示词后",
        "推荐的 Skill 才开始完成具体任务",
        "生成下一段可执行提示词",
        "It generates a directly usable task prompt",
        "そのまま送信できるタスクプロンプトを生成",
        "바로 보낼 수 있는 작업 프롬프트를 생성",
        "生成一段可以直接繼續發送的提示詞",
    )
    for path in [ROOT_DIR / "docs/新手入门.md", *ROOT_DIR.glob("README*.md")]:
        for rule in retired_doc_rules:
            if rule in path.read_text(encoding="utf-8"):
                errors.append(f"{path.relative_to(ROOT_DIR)} 仍描述已移除的复制提示词流程：{rule}")

    readme_text = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    if "常见衔接方式" in readme_text:
        errors.append("README.md 仍把文档描述为「常见衔接方式」")

    route_map_text = (ROOT_DIR / "docs" / "skill-link-map.mmd").read_text(
        encoding="utf-8"
    )
    for marker in ("当前任务未完成，方法仍匹配", "继续当前 Skill", "前提失效或方法不匹配", "当前目标已完成"):
        if marker not in route_map_text:
            errors.append(f"docs/skill-link-map.mmd 缺少继续、调整或完成条件：{marker}")

    route_svg_text = (ROOT_DIR / "docs" / "skill-link-map-4x3.svg").read_text(
        encoding="utf-8"
    )
    view_box_match = re.search(r'viewBox="([^"]+)"', route_svg_text)
    if view_box_match is None:
        errors.append("docs/skill-link-map-4x3.svg 缺少 viewBox")
    else:
        _, _, width, height = map(float, view_box_match.group(1).split())
        if abs(width / height - 4 / 3) > 0.001:
            errors.append(
                "docs/skill-link-map-4x3.svg 画布比例为 "
                f"{width / height:.3f}，应为横版 4:3"
            )

    if errors:
        print("Skill 编排契约校验失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        sys.exit(1)

    leaf_count = len([name for name in formal_names if name != "dbs"])
    print(
        "Skill 编排契约静态校验通过（不代表对话行为已验证）："
        f"{len(formal_names)} 个正式 Skill，"
        f"{leaf_count} 个叶子 Skill 只描述能力、不点名其他 Skill"
    )


if __name__ == "__main__":
    main()
