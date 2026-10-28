#!/usr/bin/env python3
"""Validate the public numbered prompts shipped inside the dbs Skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


NUMBER = re.compile(r"[0-9]{3}\Z")
REQUIRED_SECTIONS = (
    "## 用户要完成的事",
    "## 需要的输入",
    "## 执行步骤",
    "## 交付结果",
    "## 验收标准",
    "## 适用边界",
)


def validate(root: Path) -> list[str]:
    prompt_root = root / "skills" / "dbs" / "numbered-prompts"
    errors: list[str] = []
    state_file = prompt_root / "allocation.json"
    if not state_file.is_file():
        return [f"缺少编号分配状态：{state_file}"]
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
        issued = state["issued"]
        retired = state["retired"]
        if state.get("schema_version") != 2 or not isinstance(issued, list) or not isinstance(retired, list):
            raise ValueError("编号分配状态格式错误")
        if any(not isinstance(code, str) or NUMBER.fullmatch(code) is None for code in issued + retired):
            raise ValueError("issued 和 retired 只允许三位数字")
        if issued != sorted(set(issued)) or retired != sorted(set(retired)):
            raise ValueError("issued 和 retired 必须唯一且升序")
        if not set(retired).issubset(issued):
            raise ValueError("retired 必须属于 issued")
    except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as error:
        return [f"编号分配状态无效：{error}"]

    numbers: list[int] = []
    prompt_data: dict[str, tuple[str, str, str]] = {}
    for entry in sorted(prompt_root.iterdir()):
        if entry.name in {"allocation.json", "catalog.json"}:
            continue
        if entry.is_symlink() or not entry.is_dir() or NUMBER.fullmatch(entry.name) is None:
            errors.append(f"编号目录只允许三位数字：{entry.name}")
            continue
        numbers.append(int(entry.name))
        prompt = entry / "PROMPT.md"
        if not prompt.is_file() or prompt.is_symlink():
            errors.append(f"{entry.name} 缺少普通文件 PROMPT.md")
            continue
        text = prompt.read_text(encoding="utf-8")
        if not re.search(rf"(?m)^# {entry.name}｜\S.+$", text):
            errors.append(f"{entry.name}/PROMPT.md 首行应包含编号和标题")
        if not re.search(r"(?m)^来源：\S.*$", text):
            errors.append(f"{entry.name}/PROMPT.md 缺少非空来源")
        positions: list[int] = []
        for section in REQUIRED_SECTIONS:
            match = re.search(rf"(?m)^{re.escape(section)}\s*$", text)
            if match is None:
                errors.append(f"{entry.name}/PROMPT.md 缺少 {section}")
            else:
                positions.append(match.start())
        if len(positions) == len(REQUIRED_SECTIONS):
            if positions != sorted(positions):
                errors.append(f"{entry.name}/PROMPT.md 六个章节顺序不正确")
            for index, section in enumerate(REQUIRED_SECTIONS):
                start = positions[index] + len(section)
                end = positions[index + 1] if index + 1 < len(positions) else len(text)
                if not text[start:end].strip():
                    errors.append(f"{entry.name}/PROMPT.md 的 {section} 没有内容")
        title_match = re.search(rf"(?m)^# {entry.name}｜(.+)$", text)
        purpose_match = re.search(r"(?ms)^## 用户要完成的事\s*\n(.*?)(?=^## |\Z)", text)
        if title_match and purpose_match:
            purpose_lines = [" ".join(line.split()) for line in purpose_match.group(1).splitlines() if line.strip()]
            if purpose_lines:
                digest = hashlib.sha256(prompt.read_bytes()).hexdigest()
                prompt_data[entry.name] = (title_match.group(1).strip(), purpose_lines[0], digest)
        if re.search(r"(?m)^---\s*$", text[:100]):
            errors.append(f"{entry.name}/PROMPT.md 不使用 Skill frontmatter")
        for nested in entry.rglob("*"):
            if nested.is_symlink():
                errors.append(f"{nested.relative_to(prompt_root)} 不允许符号链接")
            if nested.name == "SKILL.md":
                errors.append(f"{nested.relative_to(prompt_root)} 不得注册为独立 Skill")

    catalog_path = prompt_root / "catalog.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        items = catalog["items"]
        if catalog.get("schema_version") != 1 or not isinstance(items, list):
            raise ValueError("目录格式错误")
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        errors.append(f"编号目录 catalog.json 无效：{error}")
        items = []
    listed_codes: list[str] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            errors.append("catalog.json 存在格式错误的条目")
            continue
        code = item["id"]
        listed_codes.append(code)
        expected = prompt_data.get(code)
        if expected is None:
            errors.append(f"catalog.json 的编号 {code} 缺少有效 PROMPT.md")
            continue
        if (item.get("title"), item.get("purpose"), item.get("sha256")) != expected:
            errors.append(f"catalog.json 的编号 {code} 与正文标题、用途或 SHA-256 不一致")
    if listed_codes != sorted(set(listed_codes)):
        errors.append("catalog.json 的编号必须唯一且升序")
    if set(listed_codes) != {f"{number:03d}" for number in numbers}:
        errors.append("catalog.json 与编号目录的编号集合不一致")
    active = {f"{number:03d}" for number in numbers}
    if active != set(issued) - set(retired):
        errors.append("allocation.json 的 issued、retired 与现有编号目录不一致")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", type=Path)
    root = parser.parse_args().root.expanduser().resolve()
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    prompt_root = root / "skills" / "dbs" / "numbered-prompts"
    count = sum(1 for entry in prompt_root.iterdir() if entry.is_dir())
    print(f"编号提示词校验通过：{count} 个编号")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
