#!/usr/bin/env python3
"""校验 dbskill 发布版本在全部公开入口保持一致。"""

import json
import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
version = (ROOT_DIR / "VERSION").read_text(encoding="utf-8").strip()
marketplace_path = ROOT_DIR / ".claude-plugin" / "marketplace.json"
marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
dbs_skill = (ROOT_DIR / "skills" / "dbs" / "SKILL.md").read_text(encoding="utf-8")
update_path = ROOT_DIR / "UPDATE.json"
update_manifest = json.loads(update_path.read_text(encoding="utf-8"))

errors = []
metadata_version = marketplace.get("metadata", {}).get("version")
if metadata_version != version:
    errors.append(
        f"metadata.version 为 {metadata_version!r}，VERSION 为 {version!r}"
    )

badge_version = re.search(
    r"https://img\.shields\.io/badge/version-([0-9.]+)-[A-Fa-f0-9]{6}\.svg(?:\?[^)]*)?", readme
)
if badge_version is None:
    errors.append("README 未找到 Version Badge")
elif badge_version.group(1) != version:
    errors.append(
        f"README Version Badge 为 {badge_version.group(1)!r}，VERSION 为 {version!r}"
    )

for translation in ROOT_DIR.glob("README.*.md"):
    match = re.search(r"badge/version-([0-9.]+)-", translation.read_text(encoding="utf-8"))
    if not match or match.group(1) != version:
        errors.append(f"{translation.name} Version Badge 与 VERSION 不一致")

dbs_local_version = re.search(r'DBS_LOCAL_VERSION="([0-9.]+)"', dbs_skill)
if dbs_local_version is None:
    errors.append("skills/dbs/SKILL.md 未找到 DBS_LOCAL_VERSION")
elif dbs_local_version.group(1) != version:
    errors.append(
        "skills/dbs/SKILL.md 的 DBS_LOCAL_VERSION 为 "
        f"{dbs_local_version.group(1)!r}，VERSION 为 {version!r}"
    )

update_version = update_manifest.get("version")
if update_version != version:
    errors.append(
        f"UPDATE.json version 为 {update_version!r}，VERSION 为 {version!r}"
    )

notice = update_manifest.get("notice")
if not isinstance(notice, str) or not 20 <= len(notice.strip()) <= 80:
    errors.append("UPDATE.json notice 必须为 20～80 个字符")
elif notice != notice.strip() or any(character in notice for character in "\r\n\t"):
    errors.append("UPDATE.json notice 不能包含首尾空白、换行或制表符")

expected_details_url = "https://github.com/dontbesilent2025/dbskill/commits/main"
if update_manifest.get("details_url") != expected_details_url:
    errors.append(
        "UPDATE.json details_url 必须指向官方 main 分支提交记录"
    )

for plugin in marketplace.get("plugins", []):
    plugin_version = plugin.get("version")
    if plugin_version != version:
        errors.append(
            f"插件 {plugin.get('name', '<未命名>')} 的 version 为 "
            f"{plugin_version!r}，应为 {version!r}"
        )

if errors:
    print("发布版本校验失败：", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print(
    f"发布版本校验通过：{version} "
    f"（{len(marketplace.get('plugins', []))} 个插件）"
)
