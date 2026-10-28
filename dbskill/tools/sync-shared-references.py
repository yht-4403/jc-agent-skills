#!/usr/bin/env python3
"""把 shared/references/ 中的共享资料复制到需要它的每个 Skill。

多个 Skill 共用的资料只在 shared/references/ 维护一份真源；shared/manifest.json 登记
每份资料要复制到哪些 Skill。每个 Skill 安装后只有自己的目录，所以运行时读取的是
skills/<name>/references/<文件> 这份副本。

默认执行同步；加 --check 时只校验副本与真源一致，不写入，CI 使用这个模式。
"""

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SHARED_DIR = ROOT_DIR / "shared" / "references"
MANIFEST_PATH = ROOT_DIR / "shared" / "manifest.json"


def header(filename: str) -> str:
    # 副本会随 Skill 安装到用户电脑，标记里不写仓库内部路径和维护命令。
    return "<!-- 本文件由 dbskill 统一生成，多个 Skill 共用同一内容，请勿单独修改 -->\n\n"


def expected_copies() -> dict[Path, str]:
    """返回 {副本路径: 期望内容}。"""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    copies = {}
    for filename, skills in manifest.items():
        source = SHARED_DIR / filename
        if not source.is_file():
            raise SystemExit(f"shared/manifest.json 登记的 {filename} 在 shared/references/ 中不存在")
        content = header(filename) + source.read_text(encoding="utf-8")
        for skill in skills:
            skill_dir = ROOT_DIR / "skills" / skill
            if not (skill_dir / "SKILL.md").is_file():
                raise SystemExit(f"shared/manifest.json 为 {filename} 登记的 Skill {skill} 不存在")
            copies[skill_dir / "references" / filename] = content
    return copies


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只校验，不写入")
    args = parser.parse_args()

    copies = expected_copies()
    stale = [
        path for path, content in copies.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != content
    ]

    if args.check:
        if stale:
            print("共享资料副本与真源不一致：", file=sys.stderr)
            for path in stale:
                print(f"- {path.relative_to(ROOT_DIR)}", file=sys.stderr)
            print("请修改 shared/references/ 中的真源，再运行 python3 tools/sync-shared-references.py", file=sys.stderr)
            sys.exit(1)
        print(f"共享资料校验通过：{len(copies)} 份副本与真源一致")
        return

    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(copies[path], encoding="utf-8")
        print(f"已同步 {path.relative_to(ROOT_DIR)}")
    print(f"共享资料同步完成：{len(copies)} 份副本，更新 {len(stale)} 份")


if __name__ == "__main__":
    main()
