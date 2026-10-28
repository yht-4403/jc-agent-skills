#!/usr/bin/env python3
"""校验存档契约的真源完整，dbs-save、dbs-restore、dbs-report 只引用各自的副本、不各自重写。

副本与真源是否一致由 tools/sync-shared-references.py --check 校验。
"""

import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT_DIR / "shared" / "references" / "archive-contract.md"

FRONTMATTER_FIELDS = ("slug", "timestamp", "title", "source_skill", "status", "next_skill")
BODY_SECTIONS = ("用户主诉", "已得出的结论", "用户已否决的方向", "待验证假设", "已确认的下一步", "备注")
STATUS_VALUES = ("in-progress", "resolved", "abandoned")

# 每个存档 Skill 必须出现的契约链接。
REQUIRED_LINKS = {
    "dbs-save": "references/archive-contract.md",
    "dbs-restore": "references/archive-contract.md",
    "dbs-report": "references/archive-contract.md",
}

# 这些内容只能写在契约里；出现在 SKILL.md 中说明又在各自重写规则。
REDEFINITION_MARKERS = {
    "basename $(pwd)": "项目名规则",
    '"mode":': "存档位置配置格式",
    "| `default` | `~/.dbs/` |": "存档位置模式表",
    "in-progress | resolved | abandoned": "status 取值",
    "推荐下一步": "旧版段落名",
    "## 用户面向的措辞约定": "措辞约定",
}


def check_contract(text: str) -> list[str]:
    errors = []
    for field in FRONTMATTER_FIELDS:
        if not re.search(rf"^{field}: ", text, re.M):
            errors.append(f"存档契约缺少 frontmatter 字段 {field}")
    positions = []
    for section in BODY_SECTIONS:
        marker = f"`## {section}`"
        if marker not in text:
            errors.append(f"存档契约缺少正文段落 {section}")
        else:
            positions.append(text.index(marker))
    if positions != sorted(positions):
        errors.append("存档契约的正文段落顺序与约定不一致")
    for value in STATUS_VALUES:
        if f"`{value}`" not in text:
            errors.append(f"存档契约缺少 status 取值 {value}")
    if "只有用户已经明确选择下一个 Skill" not in text:
        errors.append("存档契约缺少 next_skill 只记录用户明确选择的约束")
    return errors


def check_skill(name: str, text: str) -> list[str]:
    errors = []
    if REQUIRED_LINKS[name] not in text:
        errors.append(f"skills/{name}/SKILL.md 没有引用存档契约 {REQUIRED_LINKS[name]}")
    for marker, label in REDEFINITION_MARKERS.items():
        if marker in text:
            errors.append(f"skills/{name}/SKILL.md 自行定义了{label}（{marker}），应只写在存档契约中")
    return errors


def main() -> None:
    errors = []
    if not CONTRACT_PATH.is_file():
        errors.append(f"缺少存档契约 {CONTRACT_PATH.relative_to(ROOT_DIR)}")
    else:
        errors.extend(check_contract(CONTRACT_PATH.read_text(encoding="utf-8")))
    for name in REQUIRED_LINKS:
        skill_path = ROOT_DIR / "skills" / name / "SKILL.md"
        if not skill_path.is_file():
            errors.append(f"缺少 skills/{name}/SKILL.md")
            continue
        errors.extend(check_skill(name, skill_path.read_text(encoding="utf-8")))

    if errors:
        print("存档契约校验失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        sys.exit(1)
    print("存档契约校验通过：dbs-save、dbs-restore、dbs-report 均引用契约，且未自行重写规则")


if __name__ == "__main__":
    main()
