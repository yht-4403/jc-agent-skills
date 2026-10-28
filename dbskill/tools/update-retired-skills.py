#!/usr/bin/env python3
"""根据 Git 历史生成或校验已下线 Skill 的官方版本指纹。

下线一个正式 Skill 时，先在 skills/dbs-update/references/retired-skills.json 中加入
{"name": "<skill>"}，再运行本脚本写入该 Skill 每个历史版本 SKILL.md 的 SHA-256。
加 --check 时只校验，不写入；CI 用它确认名单与 Git 历史一致。
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RETIRED_PATH = ROOT_DIR / "skills" / "dbs-update" / "references" / "retired-skills.json"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT_DIR, text=True)


def normalized_sha256(content: bytes) -> str:
    return hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()


def historical_hashes(name: str) -> list[str]:
    path = f"skills/{name}/SKILL.md"
    hashes = []
    for commit in git("log", "--format=%H", "--", path).split():
        try:
            content = subprocess.check_output(
                ["git", "show", f"{commit}:{path}"], cwd=ROOT_DIR, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            continue  # 该提交删除了文件
        digest = normalized_sha256(content)
        if digest not in hashes:
            hashes.append(digest)
    return sorted(hashes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验，不写入")
    args = parser.parse_args()

    data = json.loads(RETIRED_PATH.read_text(encoding="utf-8"))
    marketplace = json.loads(
        (ROOT_DIR / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    formal_names = {plugin["name"] for plugin in marketplace.get("plugins", [])}
    errors = []

    for entry in data.get("skills", []):
        name = entry.get("name", "")
        if name in formal_names:
            errors.append(f"{name} 仍是 Marketplace 正式条目，不能列为已下线")
            continue
        expected = historical_hashes(name)
        if not expected:
            errors.append(f"Git 历史中找不到 skills/{name}/SKILL.md")
            continue
        if args.check:
            if sorted(entry.get("sha256", [])) != expected:
                errors.append(f"{name} 的版本指纹与 Git 历史不一致，请运行 python3 tools/update-retired-skills.py")
        else:
            entry["sha256"] = expected

    if errors:
        print("已下线 Skill 名单校验失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        sys.exit(1)

    if not args.check:
        RETIRED_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(entry.get("sha256", [])) for entry in data.get("skills", []))
    print(f"已下线 Skill 名单{'校验通过' if args.check else '已更新'}：{len(data.get('skills', []))} 个 Skill，{total} 个历史版本指纹")


if __name__ == "__main__":
    main()
