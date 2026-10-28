#!/usr/bin/env python3
"""生成 dbskill 发布版本的全部派生字段。"""

import argparse
import json
import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def normalize_version(value: str) -> str:
    version = value.removeprefix("v")
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"版本号必须符合 MAJOR.MINOR.PATCH：{value}")
    return version


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"未找到唯一的 {label}")
    return updated


def normalize_notice(value: str) -> str:
    notice = value.strip()
    if not 20 <= len(notice) <= 80:
        raise ValueError("用户收益摘要必须为 20～80 个字符")
    if any(character in notice for character in "\r\n\t"):
        raise ValueError("用户收益摘要不能包含换行或制表符")
    return notice


def prepare(version: str, notice: str) -> None:
    version = normalize_version(version)
    notice = normalize_notice(notice)
    marketplace_path = ROOT_DIR / ".claude-plugin" / "marketplace.json"
    readme_path = ROOT_DIR / "README.md"
    dbs_skill_path = ROOT_DIR / "skills" / "dbs" / "SKILL.md"
    update_path = ROOT_DIR / "UPDATE.json"

    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    marketplace.setdefault("metadata", {})["version"] = version
    for plugin in marketplace.get("plugins", []):
        plugin["version"] = version

    readme = readme_path.read_text(encoding="utf-8")
    readme = replace_once(
        readme,
        r"(https://img\.shields\.io/badge/version-)[0-9.]+(-[A-Fa-f0-9]{6}\.svg(?:\?[^)]*)?)",
        rf"\g<1>{version}\g<2>",
        "README Version Badge",
    )

    dbs_skill = dbs_skill_path.read_text(encoding="utf-8")
    dbs_skill = replace_once(
        dbs_skill,
        r'(DBS_LOCAL_VERSION=")(\d+\.\d+\.\d+)(")',
        rf"\g<1>{version}\g<3>",
        "dbs/SKILL.md DBS_LOCAL_VERSION",
    )

    update_manifest = {
        "version": version,
        "notice": notice,
        "details_url": "https://github.com/dontbesilent2025/dbskill/commits/main",
    }

    (ROOT_DIR / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    marketplace_path.write_text(
        json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    readme_path.write_text(readme, encoding="utf-8")
    for translation in ROOT_DIR.glob("README.*.md"):
        content = replace_once(translation.read_text(encoding="utf-8"),
            r"(https://img\.shields\.io/badge/version-)[0-9.]+(-[A-Fa-f0-9]{6}\.svg(?:\?[^)]*)?)",
            rf"\g<1>{version}\g<2>", translation.name + " Version Badge")
        translation.write_text(content, encoding="utf-8")
    dbs_skill_path.write_text(dbs_skill, encoding="utf-8")
    update_path.write_text(
        json.dumps(update_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已将发布版本字段同步为 v{version}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare", help="写入发布版本派生字段")
    prepare_parser.add_argument("version", help="例如 v2.17.7 或 2.17.7")
    prepare_parser.add_argument(
        "--notice",
        required=True,
        help="20～80 个字符的用户收益摘要",
    )
    args = parser.parse_args()

    try:
        if args.command == "prepare":
            prepare(args.version, args.notice)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"发布准备失败：{error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
