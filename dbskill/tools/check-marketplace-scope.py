#!/usr/bin/env python3
"""校验 Claude Code marketplace 的全量入口与单 Skill 暴露范围。"""

import json
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT_DIR / ".claude-plugin" / "marketplace.json"
BUNDLE_MANIFEST_PATH = ROOT_DIR / ".claude-plugin" / "plugin.json"


def published_skill_dirs() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--", "skills/*/SKILL.md"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        paths = [Path(line) for line in result.stdout.splitlines() if line]
    else:
        paths = list((ROOT_DIR / "skills").glob("*/SKILL.md"))

    return sorted(
        path.parent.name for path in paths if "beta" not in path.parent.name
    )


def main() -> None:
    marketplace = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
    plugins = marketplace.get("plugins", [])
    plugin_names = [plugin.get("name") for plugin in plugins]
    expected_paths = [f"./skills/{name}" for name in plugin_names]
    bundle_manifest = json.loads(BUNDLE_MANIFEST_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []

    if len(plugin_names) != len(set(plugin_names)):
        errors.append("marketplace 存在重复插件名")

    for plugin in plugins:
        name = plugin.get("name", "<未命名>")
        expected_source = "./" if name == "dbs" else f"./skills/{name}"
        if plugin.get("source") != expected_source:
            errors.append(
                f"插件 {name} 的 source 为 {plugin.get('source')!r}，"
                f"应为 {expected_source!r}"
            )
        if plugin.get("strict") is not True:
            errors.append(f"插件 {name} 应使用 strict: true 隔离组件")
        if "skills" in plugin:
            errors.append(f"插件 {name} 不应在 marketplace 中重复声明 skills")

    if bundle_manifest.get("name") != "dbs":
        errors.append("根级 plugin.json 的 name 应为 'dbs'")
    if "version" in bundle_manifest:
        errors.append("根级 plugin.json 不应固定 version，应沿用 marketplace 发布版本")
    bundle_paths = bundle_manifest.get("skills")
    if bundle_paths != expected_paths:
        errors.append(
            f"dbs 全量入口的 skills 为 {bundle_paths!r}，应为 {expected_paths!r}"
        )
    if any("beta" in path for path in bundle_paths or []):
        errors.append(f"dbs 全量入口暴露了本地 beta Skill：{bundle_paths!r}")
    for path in bundle_paths or []:
        skill_file = ROOT_DIR / path.removeprefix("./") / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"dbs 全量入口引用了不存在的 {path}/SKILL.md")

    extra_skill_dirs = sorted(set(published_skill_dirs()) - set(plugin_names))
    if extra_skill_dirs:
        errors.append(
            "Git 已跟踪但未登记到 marketplace 的公开 Skill："
            f"{extra_skill_dirs!r}"
        )

    if errors:
        print("Marketplace 暴露范围校验失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        sys.exit(1)

    print(
        "Marketplace 暴露范围校验通过："
        f"dbs 全量入口包含 {len(plugin_names)} 个公开 Skill，"
        f"{len(plugin_names) - 1} 个单 Skill 插件保持隔离"
    )


if __name__ == "__main__":
    main()
