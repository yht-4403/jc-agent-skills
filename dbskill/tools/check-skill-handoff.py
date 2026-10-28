#!/usr/bin/env python3
"""校验正式 Skill frontmatter 中的接手字段 metadata.dbs-handoff。

/dbs 先读全部接手字段拆分任务，再完整读取入选 Skill 的正文。字段格式：

metadata:
  dbs-handoff: |
    - <接手时的状态> → <交出的东西>
    - 不交出：<容易被误以为会做、其实不做的事>

全部正式 Skill 补齐前，缺字段只提示；传入 --require-all 时缺字段视为错误。
是否点名其他 Skill 由 check-skill-routing-contract.py 对整份 SKILL.md 统一检查。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT_DIR / ".claude-plugin" / "marketplace.json"

FIELD = "dbs-handoff"
ARROW = "→"
NOT_DELIVERED_PREFIX = "不交出："
MAX_CHARS = 500
EXEMPT = {"dbs", "dbs-update"}


def read_frontmatter(text: str) -> str:
    match = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", text, re.DOTALL)
    if match is None:
        raise ValueError("缺少合法的 YAML frontmatter")
    return match.group(1)


def read_handoff(text: str) -> list[str] | None:
    """返回字段中的各行；没有字段时返回 None。"""
    lines = read_frontmatter(text).splitlines()
    in_metadata = False
    for index, line in enumerate(lines):
        if line.startswith("metadata:"):
            in_metadata = True
            continue
        if in_metadata and line and not line[0].isspace():
            in_metadata = False
        if not in_metadata:
            continue
        match = re.match(rf"^(\s+){re.escape(FIELD)}:\s*\|\s*$", line)
        if match is None:
            continue
        key_indent = len(match.group(1))
        entries: list[str] = []
        for continuation in lines[index + 1 :]:
            if not continuation.strip():
                continue
            indent = len(continuation) - len(continuation.lstrip())
            if indent <= key_indent:
                break
            entries.append(continuation.strip())
        return entries
    return None


def check_entries(entries: list[str]) -> list[str]:
    errors = []
    if not entries:
        return ["字段为空"]
    handoffs = [e for e in entries if not e.startswith(f"- {NOT_DELIVERED_PREFIX}")]
    not_delivered = [e for e in entries if e.startswith(f"- {NOT_DELIVERED_PREFIX}")]
    for entry in entries:
        if not entry.startswith("- "):
            errors.append(f"每行须以「- 」开头：{entry}")
    if not handoffs:
        errors.append(f"至少需要 1 行「接手状态 {ARROW} 交出内容」")
    for entry in handoffs:
        if entry.count(ARROW) != 1:
            errors.append(f"接手行须恰好包含 1 个「{ARROW}」：{entry}")
    if len(not_delivered) != 1:
        errors.append(f"须有且只有 1 行「- {NOT_DELIVERED_PREFIX}…」")
    elif entries[-1] != not_delivered[0]:
        errors.append(f"「{NOT_DELIVERED_PREFIX}」须放在最后一行")
    total = sum(len(e) for e in entries)
    if total > MAX_CHARS:
        errors.append(f"总长 {total} 个字符，超过 {MAX_CHARS}")
    return errors


def main() -> int:
    require_all = "--require-all" in sys.argv[1:]
    marketplace = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
    names = [p["name"] for p in marketplace.get("plugins", []) if p["name"] not in EXEMPT]

    errors: list[str] = []
    missing: list[str] = []
    for name in names:
        path = ROOT_DIR / "skills" / name / "SKILL.md"
        if not path.is_file():
            continue
        try:
            entries = read_handoff(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append(f"skills/{name}/SKILL.md：{exc}")
            continue
        if entries is None:
            missing.append(name)
            continue
        errors.extend(f"skills/{name}/SKILL.md {FIELD}：{e}" for e in check_entries(entries))

    if missing:
        message = f"{len(missing)}/{len(names)} 个正式 Skill 尚未填写 {FIELD}：" + "、".join(missing)
        if require_all:
            errors.append(message)
        else:
            print(f"提示：{message}")

    if errors:
        print("接手字段检查失败：")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"接手字段检查通过（已填写 {len(names) - len(missing)}/{len(names)}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
