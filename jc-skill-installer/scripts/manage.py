#!/usr/bin/env python3
"""Reconcile JC's cc-switch Skill store with agent runtime links."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = SKILL_DIR.parent
DEFAULT_MANIFEST = SKILL_DIR / "active-skills.json"
DEFAULT_CHANNELS = SKILL_DIR / "skill-channels.json"
DEFAULT_PROFILES = SKILL_DIR / "skill-profiles.json"
DEFAULT_RUNTIME_POLICY = SKILL_DIR / "runtime-policy.json"
DEFAULT_CODEBUDDY_PROJECT = Path.home()
MANAGED_START = "<!-- jc-skill-installer:start -->"
MANAGED_END = "<!-- jc-skill-installer:end -->"
ROUTE_START = "<!-- jc-skill-installer:route:start -->"
ROUTE_END = "<!-- jc-skill-installer:route:end -->"
SCRIPT_ROUTE_START = "# jc-skill-installer:route:start"
SCRIPT_ROUTE_END = "# jc-skill-installer:route:end"


def runtime_dirs() -> list[Path]:
    candidates = [Path.home() / ".codex" / "skills", Path.home() / ".Codex" / "skills"]
    result: list[Path] = []
    for candidate in candidates:
        candidate.mkdir(parents=True, exist_ok=True)
        if any(same_location(candidate, existing) for existing in result):
            continue
        result.append(candidate)
    return result


def claude_runtime_dir() -> Path:
    path = Path.home() / ".claude" / "skills"
    path.mkdir(parents=True, exist_ok=True)
    return path


def gemini_runtime_dir() -> Path:
    path = Path.home() / ".gemini" / "config" / "skills"
    path.mkdir(parents=True, exist_ok=True)
    return path


def dsh_runtime_dir() -> Path:
    """DeepSeek Harness user skill root: ~/.dsh/skills. Do not use ~/.agents/skills."""
    path = Path.home() / ".dsh" / "skills"
    path.mkdir(parents=True, exist_ok=True)
    return path


def workbuddy_runtime_dir() -> Path | None:
    """WorkBuddy is separate from CodeBuddy; only reconcile an installed user root."""
    parent = Path.home() / ".workbuddy"
    return parent / "skills" if parent.is_dir() else None


def kimi_code_runtime_dir() -> Path | None:
    """Verified desktop userRoots: <KIMI_CODE_HOME>/skills, separate from Work."""
    parent = Path(os.environ.get("KIMI_CODE_HOME", str(Path.home() / ".kimi-code"))).expanduser()
    return parent / "skills" if parent.is_dir() else None


def runtime_policy() -> dict:
    if not DEFAULT_RUNTIME_POLICY.is_file():
        return {"version": 1, "platform_owned": {}, "grok": {}}
    data = json.loads(DEFAULT_RUNTIME_POLICY.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError(f"Unsupported runtime policy: {DEFAULT_RUNTIME_POLICY}")
    return data


def platform_owned(runtime: Path) -> set[str]:
    try:
        relative = runtime.resolve().relative_to(Path.home().resolve()).as_posix()
    except ValueError:
        return set()
    names = runtime_policy().get("platform_owned", {}).get(relative, {})
    return set(names)


def grok_binary() -> Path | None:
    found = shutil.which("grok")
    candidate = Path(found) if found else Path.home() / ".grok" / "bin" / "grok"
    return candidate if candidate.is_file() and os.access(candidate, os.X_OK) else None


def update_toml_arrays(content: str, table: str, values: dict[str, list[str]]) -> str:
    """Replace only the named array keys; preserve other TOML fields and comments."""
    parsed = tomllib.loads(content)
    original = parsed.get(table, {})
    if not isinstance(original, dict):
        raise ValueError(f"Expected TOML table: {table}")
    table_match = re.search(rf"(?m)^\[{re.escape(table)}\][ \t]*(?:#.*)?$", content)
    if not table_match:
        updated = content.rstrip() + f"\n\n[{table}]\n"
        updated += "".join(f"{key} = {json.dumps(value, ensure_ascii=False)}\n" for key, value in values.items())
    else:
        start = table_match.end()
        next_table = re.search(r"(?m)^\[", content[start:])
        end = start + next_table.start() if next_table else len(content)
        body = content[start:end]
        for key, value in values.items():
            replacement = f"{key} = {json.dumps(value, ensure_ascii=False)}"
            match = re.search(rf"(?m)^[ \t]*{re.escape(key)}[ \t]*=", body)
            if match:
                value_start = match.end()
                rest = body[value_start:]
                consumed = 0
                for line in rest.splitlines(keepends=True):
                    consumed += len(line)
                    try:
                        tomllib.loads("value = " + rest[:consumed])
                    except tomllib.TOMLDecodeError:
                        continue
                    break
                else:
                    raise ValueError(f"Cannot safely edit TOML array: {table}.{key}")
                body = body[:match.start()] + replacement + "\n" + body[value_start + consumed:]
            else:
                body = body.rstrip() + "\n" + replacement + "\n"
        updated = content[:start] + body + content[end:]
    checked = tomllib.loads(updated)
    for key, value in parsed.items():
        if key != table and checked.get(key) != value:
            raise ValueError(f"TOML edit would change unrelated table: {key}")
    for key, value in original.items():
        if key not in values and checked[table].get(key) != value:
            raise ValueError(f"TOML edit would change unrelated setting: {table}.{key}")
    return updated


def grok_managed_config(root: Path, manifest: Path) -> dict[str, list[str]]:
    policy = runtime_policy().get("grok", {})
    desired = codebuddy_entries(root, manifest)
    direct = [str(desired[name]) for name in policy.get("direct_source_names", []) if name in desired]
    ignore = [str(Path.home() / item["path"])
              for item in policy.get("ignore_home_relative_paths", [])
              if not item.get("when_active") or item["when_active"] in desired]
    return {"paths": direct, "ignore": ignore}


def sync_grok(root: Path, manifest: Path, dry_run: bool = False) -> tuple[int, int]:
    """Use Claude compatibility plus registered direct sources, never another mirror."""
    if grok_binary() is None:
        return 0, 0
    config = Path.home() / ".grok" / "config.toml"
    content = config.read_text(encoding="utf-8") if config.is_file() else ""
    parsed = tomllib.loads(content)
    skills = parsed.get("skills", {})
    required = grok_managed_config(root, manifest)
    receipt = config.parent / ".jc-skill-installer-grok-config.json"
    previous = json.loads(receipt.read_text(encoding="utf-8")) if receipt.is_file() else {}
    if previous and (previous.get("version") != 1 or previous.get("source_root") != str(root.resolve())):
        raise ValueError(f"Conflicting Grok config ownership record: {receipt}")
    values = {}
    for key, paths in required.items():
        existing = skills.get(key, [])
        if not isinstance(existing, list) or not all(isinstance(p, str) for p in existing):
            raise ValueError(f"Invalid Grok skills.{key}: expected string array")
        prior = previous.get("managed", {}).get(key, [])
        values[key] = list(dict.fromkeys([p for p in existing if p not in prior] + paths))
    updated = update_toml_arrays(content, "skills", values)
    legacy = Path.home() / ".grok" / "skills"
    stale = []
    if legacy.is_dir():
        targets = set(codebuddy_entries(root, manifest).values())
        old = Path.home() / ".agents" / "skills"
        for entry in legacy.iterdir():
            if entry.is_symlink() and (inside(entry.resolve(), old) or entry.resolve() in targets):
                stale.append(entry)
    if not dry_run:
        if updated != content:
            config.parent.mkdir(parents=True, exist_ok=True)
            temp = config.with_suffix(".jc-sync.tmp")
            temp.write_text(updated, encoding="utf-8")
            if config.exists():
                temp.chmod(config.stat().st_mode & 0o777)
            temp.replace(config)
        for entry in stale:
            entry.unlink()
        receipt.write_text(json.dumps({"version": 1, "source_root": str(root.resolve()),
                                       "managed": required}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(codebuddy_entries(root, manifest)), len(stale)


def audit_grok(root: Path, manifest: Path) -> list[str]:
    binary = grok_binary()
    if binary is None:
        return []
    config = Path.home() / ".grok" / "config.toml"
    parsed = tomllib.loads(config.read_text(encoding="utf-8")) if config.is_file() else {}
    issues = []
    for key, required in grok_managed_config(root, manifest).items():
        actual = parsed.get("skills", {}).get(key, [])
        for path in required:
            if path not in actual:
                issues.append(f"MISSING_GROK_MANAGED_CONFIG {key}: {path}")
    try:
        process = subprocess.run([str(binary), "inspect", "--json"], capture_output=True,
                                 text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return issues + [f"GROK_DISCOVERY_FAILED {type(error).__name__}"]
    if process.returncode:
        return issues + [f"GROK_DISCOVERY_FAILED exit={process.returncode}"]
    try:
        data = json.loads(process.stdout)
        skills = data["skills"]
    except (json.JSONDecodeError, KeyError):
        return issues + ["INVALID_GROK_DISCOVERY_RESULT"]
    sources = {Path(s["source"]["path"]).resolve().parent for s in skills}
    for name, target in codebuddy_entries(root, manifest).items():
        if target.resolve() not in sources:
            issues.append(f"MISSING_GROK_SOURCE {name}: {target}")
    namespaces = runtime_policy().get("grok", {}).get("namespaced_providers", {})
    for name, count in Counter(s["name"] for s in skills).items():
        if count > 1:
            providers = [s for s in skills if s["name"] == name]
            invocation_names = [s.get("invocableAs") for s in providers]
            registered = namespaces.get(name, {})
            expected_invocations = registered.get("allowed_invocations", [])
            preferred = registered.get("preferred_invocation")
            if (not registered or None in invocation_names or len(set(invocation_names)) != count
                    or set(invocation_names) != set(expected_invocations)
                    or preferred not in invocation_names):
                issues.append(f"DUPLICATE_GROK_SKILL_NAME {name}: {count} providers")
            elif not any(s.get("invocableAs") == preferred and
                         Path(s["source"]["path"]).resolve().parent == codebuddy_entries(root, manifest).get(name)
                         for s in providers):
                issues.append(f"WRONG_GROK_PREFERRED_PROVIDER {name}: {preferred}")
    compatibility = data.get("externalCompat", {}).get("cells", [])
    if not any(c.get("vendor") == "claude" and c.get("surface") == "skills" and c.get("enabled") for c in compatibility):
        issues.append("GROK_CLAUDE_SKILLS_COMPATIBILITY_DISABLED")
    inherited_rule = Path.home() / ".claude" / "CLAUDE.md"
    if not any(item.get("scope") == "global" and same_location(Path(item["path"]), inherited_rule)
               for item in data.get("projectInstructions", []) if item.get("path")):
        issues.append(f"GROK_GLOBAL_MANAGEMENT_RULE_NOT_DISCOVERED {inherited_rule}")
    legacy = Path.home() / ".grok" / "skills"
    if legacy.is_dir():
        for entry in legacy.iterdir():
            if entry.is_symlink() and not entry.exists():
                issues.append(f"BROKEN_GROK_LINK {entry}")
            elif entry.is_dir() and (entry / "SKILL.md").is_file():
                issues.append(f"UNMANAGED_GROK_SKILL {entry}")
    return issues


KIMI_SYNC_STATE = ".jc-skill-installer-links.json"


def kimi_work_runtime_dir() -> Path | None:
    """Discover Work's existing root; never substitute Kimi Code's user directory."""
    override = os.environ.get("JC_KIMI_WORK_SKILLS_DIR")
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_dir():
            raise ValueError(f"Missing Kimi Work skills root: {path}")
        return path
    bases = [Path.home() / "Library" / "Application Support"]
    if os.environ.get("APPDATA"):
        bases.append(Path(os.environ["APPDATA"]))
    candidates = [base / "kimi-desktop" / "daimon-share" / "daimon" / "skills"
                  for base in bases]
    found = [path for path in candidates if path.is_dir()]
    if len(found) > 1:
        raise ValueError("Multiple Kimi Work roots; set JC_KIMI_WORK_SKILLS_DIR")
    return found[0] if found else None


def kimi_owned_links(runtime: Path, root: Path) -> dict[str, str]:
    state = runtime / KIMI_SYNC_STATE
    if not state.exists():
        return {}
    data = json.loads(state.read_text(encoding="utf-8"))
    if data.get("version") != 1 or data.get("source_root") != str(root.resolve()):
        raise ValueError(f"Conflicting Kimi ownership record: {state}")
    links = data.get("links")
    if not isinstance(links, dict):
        raise ValueError(f"Invalid Kimi ownership record: {state}")
    for name, target in links.items():
        if not isinstance(name, str) or not name or "/" in name or "\\" in name or name in {".", ".."}:
            raise ValueError(f"Unsafe Kimi ownership name: {name!r}")
        if not isinstance(target, str) or not inside(Path(target), root):
            raise ValueError(f"Kimi ownership target escapes source: {target!r}")
    return links


def kimi_wrapper_conflicts(entry: Path, target: Path) -> list[str]:
    if entry.is_symlink() or not entry.is_dir():
        return [f"Expected managed Kimi wrapper directory: {entry}"]
    return [f"Modified managed Kimi resource: {child}"
            for child in entry.iterdir()
            if not child.is_symlink() or child.resolve() != (target / child.name).resolve()]


def sync_kimi_work(root: Path, manifest: Path, runtime: Path | None = None,
                   dry_run: bool = False) -> tuple[int, int]:
    runtime = runtime or kimi_work_runtime_dir()
    if runtime is None:
        return (0, 0)
    runtime = runtime.expanduser().resolve()
    if not runtime.is_dir():
        raise ValueError(f"Missing Kimi Work skills root: {runtime}")
    desired = codebuddy_entries(root, manifest)
    owned = kimi_owned_links(runtime, root)
    # Work skips directory symlinks. Use real shells with source-linked children.
    for name in set(desired) | set(owned):
        entry = runtime / name
        if not entry.exists() and not entry.is_symlink():
            continue
        if name not in owned:
            raise ValueError(f"Conflicting unowned Kimi entry: {entry}")
        conflicts = kimi_wrapper_conflicts(entry, Path(owned[name]))
        if conflicts:
            raise ValueError(conflicts[0])
    stale = [name for name in owned if name not in desired
             or Path(owned[name]).resolve() != desired[name].resolve()]
    if dry_run:
        return len(desired), len(stale)
    removed = 0
    for name in stale:
        entry = runtime / name
        if entry.is_dir():
            for child in entry.iterdir():
                child.unlink()
            entry.rmdir()
            removed += 1
    for name, target in desired.items():
        entry = runtime / name
        entry.mkdir(exist_ok=True)
        resources = {child.name: child for child in target.iterdir()
                     if child.name not in {".DS_Store", ".git", "__pycache__"}
                     and not (child.is_symlink() and child.resolve() == target.resolve())}
        for child in entry.iterdir():
            if child.name not in resources:
                child.unlink()
        for resource, source in resources.items():
            ensure_link(entry, resource, source)
    data = {"version": 1, "source_root": str(root.resolve()),
            "links": {name: str(target.resolve()) for name, target in desired.items()}}
    state = runtime / KIMI_SYNC_STATE
    temp = state.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(state)
    return len(desired), removed


def audit_kimi_work(root: Path, manifest: Path) -> list[str]:
    runtime = kimi_work_runtime_dir()
    if runtime is None:
        return []
    owned = kimi_owned_links(runtime, root)
    desired = codebuddy_entries(root, manifest)
    issues = []
    for name, target in desired.items():
        entry = runtime / name
        issues.extend(kimi_wrapper_conflicts(entry, target))
        for source in target.iterdir():
            if source.name in {".DS_Store", ".git", "__pycache__"}:
                continue
            if source.is_symlink() and source.resolve() == target.resolve():
                continue
            link = entry / source.name
            if not link.is_symlink() or link.resolve() != source.resolve():
                issues.append(f"MISSING_OR_WRONG_KIMI_RESOURCE {link}")
        if owned.get(name) != str(target.resolve()):
            issues.append(f"MISSING_KIMI_OWNERSHIP {entry}")
    for name in owned.keys() - desired.keys():
        issues.append(f"STALE_MANAGED_KIMI_ENTRY {runtime / name}")
    exempt = platform_owned(runtime)
    for entry in runtime.iterdir():
        if entry.name not in desired and entry.name not in exempt and (entry / "SKILL.md").is_file():
            issues.append(f"UNMANAGED_KIMI_SKILL {entry}")
    return issues


def managed_rule(agent: str, root: Path = DEFAULT_ROOT) -> str:
    source = root.resolve() / "jc-skill-installer"
    command = "python3 " + shlex.quote(str(source / "scripts" / "manage.py"))
    return (
        f"{MANAGED_START}\n"
        "## Skill management\n\n"
        "凡是新增、创建、安装、更新、启用、停用、卸载、迁移或审计个人 Skill，先读取并遵循：\n\n"
        f"```text\n{source / 'SKILL.md'}\n```\n\n"
        f"个人 Skill 的真实文件只放在 `{root.resolve()}`，活动集合只由 "
        "`jc-skill-installer/active-skills.json` 管理。客户端目录只暴露链接；Kimi Work 使用真实入口目录和链接子资源。\n\n"
        "- 新增：在统一仓库创建或下载到临时目录再导入统一仓库，检查名称、元数据和已有改动，"
        f"然后执行 `{command} activate <仓库相对路径>`。\n"
        "- 更新：只修改或替换统一仓库中的源文件，先保存旧内容；有版本通道的 Skill 按归档规则处理。"
        f"完成后必须执行 `{command} update <仓库相对路径>`，包括新增、删除顶层脚本或参考文件的情况。\n"
        f"- 停用：执行 `{command} deactivate <skill-name>`，保留源文件；不得只删除当前客户端的入口。\n"
        "- 内置 creator、installer、技能市场或其他迁移工具只负责生成或取得候选文件，"
        "不得自行选择全局安装位置、复制实体文件到运行时或用原生 skill delete 删除源链接。"
        "最终导入、启停和同步必须交回本管理器。\n"
        "- 上述命令会自动同步所有已安装的 Codex、Claude Code、Gemini / Antigravity、CodeBuddy、WorkBuddy、"
        "DeepSeek Harness、Kimi Code、Kimi Work 和 Grok Build，并检查规则与文件一致性。"
        "出现冲突或同步失败时先处理并重跑；检查失败不能报告已全部同步。\n\n"
        "应用自带和插件文件由各客户端管理，登记在 runtime-policy.json；不把缓存当个人源仓库。"
        "Grok 通过 Claude 兼容和登记的直接源路径发现 Skill，不创建 `.grok/skills` 镜像；"
        "不重建旧 `.agents/skills`。已登记的架构个人入口为 `user:clean-architecture`，"
        "插件入口 `developer-kit-java:clean-architecture` 保持独立。\n"
        f"{MANAGED_END}"
    )


def upsert_managed_rule(path: Path, title: str, agent: str, root: Path = DEFAULT_ROOT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    block = managed_rule(agent, root)
    if path.is_file():
        current = path.read_text(encoding="utf-8")
    else:
        current = ""
    if MANAGED_START in current or MANAGED_END in current:
        if current.count(MANAGED_START) != 1 or current.count(MANAGED_END) != 1:
            raise ValueError(f"Malformed managed rule markers: {path}")
        before, remainder = current.split(MANAGED_START, 1)
        _, after = remainder.split(MANAGED_END, 1)
        updated = before.rstrip() + "\n\n" + block + after
    elif current.strip():
        updated = current.rstrip() + "\n\n" + block + "\n"
    else:
        updated = title + "\n\n" + block + "\n"
    if updated != current:
        path.write_text(updated, encoding="utf-8")


def managed_rule_targets() -> list[tuple[str, Path]]:
    home = Path.home()
    targets = [("codex", home / ".codex" / "AGENTS.md"),
               ("claude", home / ".claude" / "CLAUDE.md"),
               ("gemini", home / ".gemini" / "GEMINI.md")]
    if (home / ".codebuddy").is_dir():
        targets.append(("codebuddy", home / ".codebuddy" / "CODEBUDDY.md"))
    if workbuddy_runtime_dir() is not None:
        # The embedded CLI defaults to CODEBUDDY.md; custom branding can select
        # WORKBUDDY.md. Keep both supported names governed by the same block.
        targets.extend(("workbuddy", home / ".workbuddy" / name)
                       for name in ("CODEBUDDY.md", "WORKBUDDY.md"))
    if (home / ".dsh").is_dir():
        targets.append(("dsh", home / ".dsh" / "AGENTS.md"))
    kimi_code = kimi_code_runtime_dir()
    if kimi_code is not None:
        targets.append(("kimi-code", kimi_code.parent / "AGENTS.md"))
    kimi_work = kimi_work_runtime_dir()
    if kimi_work is not None:
        config = kimi_work.parent / "config.json"
        if config.is_file():
            data = json.loads(config.read_text(encoding="utf-8"))
            agents = data.get("agents", {})
            defaults = agents.get("defaults", {})
            for entry in agents.get("entries", {}).values():
                value = entry.get("workDir", defaults.get("workDir"))
                if isinstance(value, str):
                    directory = Path(value).expanduser()
                    if directory.is_absolute() and directory.is_dir():
                        pair = ("kimi-work", directory / "AGENTS.md")
                        if pair not in targets:
                            targets.append(pair)
    return targets


def sync_managed_rules(root: Path = DEFAULT_ROOT) -> int:
    targets = managed_rule_targets()
    # Reject malformed blocks throughout the target set before writing any file.
    for _, path in targets:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if MANAGED_START in text or MANAGED_END in text:
            if text.count(MANAGED_START) != 1 or text.count(MANAGED_END) != 1 or text.index(MANAGED_END) < text.index(MANAGED_START):
                raise ValueError(f"Malformed managed rule markers: {path}")
    for client, path in targets:
        upsert_managed_rule(path, f"# Global {client} Instructions", client, root)
    sync_source_routes(root)
    return len(targets)


def audit_managed_rules(root: Path = DEFAULT_ROOT) -> list[str]:
    issues = []
    for client, path in managed_rule_targets():
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        if content.count(MANAGED_START) != 1 or content.count(MANAGED_END) != 1:
            issues.append(f"MISSING_OR_MALFORMED_MANAGED_RULE {path}")
            continue
        start = content.index(MANAGED_START)
        end = content.index(MANAGED_END) + len(MANAGED_END)
        if content[start:end] != managed_rule(client, root):
            issues.append(f"OUTDATED_MANAGED_RULE {path}")
    kimi_work = kimi_work_runtime_dir()
    if kimi_work is not None and not any(client == "kimi-work" for client, _ in managed_rule_targets()):
        issues.append("KIMI_WORK_RULE_TARGET_NOT_CONFIGURED: no existing configured agent workDir")
    issues.extend(source_route_issues(root))
    return issues


def source_route_policy(root: Path) -> dict:
    path = root / "jc-skill-installer" / "runtime-policy.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def source_route_block(root: Path) -> str:
    command = "python3 " + shlex.quote(str(root.resolve() / "jc-skill-installer/scripts/manage.py"))
    return (
        f"{ROUTE_START}\n"
        "## 本机统一 Skill 管理规则\n\n"
        "本 Skill 已接入 JC 统一仓库。执行安装、更新、停用或迁移前，先读取同一仓库的 "
        "`jc-skill-installer/SKILL.md`，由该管理器负责最终存储、活动清单和所有客户端同步。\n\n"
        "在这台机器上，不执行下文的全局 `npx skills add ... -g --all`，不创建 `.agents/skills` "
        "或 Grok 薄适配层，也不按旧脚本清理客户端专属入口。下文这些独立安装步骤仅适用于未接入 JC 管理器的环境。\n\n"
        "新增：把候选文件放到统一仓库，检查名称及已有改动，然后执行 "
        f"`{command} activate <仓库相对路径>`。更新：先获取上游到临时目录，比较、保存本地修改与旧内容，"
        "仅替换对应的统一源文件，遵循已注册的版本归档规则，最后执行 "
        f"`{command} update <仓库相对路径>`；更新整个套件后可执行 `{command} reconcile`。"
        f"停用：执行 `{command} deactivate <skill-name>`。\n\n"
        "管理器检查成功后才能报告完成；失败时保留源文件与原有用户材料，处理冲突后重跑。\n"
        f"{ROUTE_END}"
    )


def script_route_block() -> str:
    return (
        SCRIPT_ROUTE_START + "\n"
        "# A JC-managed checkout delegates before the legacy installer can write.\n"
        '_jc_skill_ancestor="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"\n'
        'while [[ "$_jc_skill_ancestor" != / ]]; do\n'
        '  if [[ -f "$_jc_skill_ancestor/jc-skill-installer/scripts/manage.py" ]]; then\n'
        '    case "${1:-}" in\n'
        '      link|unlink|status)\n'
        '        exec python3 "$_jc_skill_ancestor/jc-skill-installer/scripts/manage.py" dbs-route "$@"\n'
        '        ;;\n'
        '      --help|-h|help|"")\n'
        '        exec python3 "$_jc_skill_ancestor/jc-skill-installer/scripts/manage.py" dbs-route --help\n'
        '        ;;\n'
        '    esac\n'
        '    break\n'
        '  fi\n'
        '  _jc_skill_ancestor="$(dirname "$_jc_skill_ancestor")"\n'
        'done\n'
        'unset _jc_skill_ancestor\n'
        + SCRIPT_ROUTE_END
    )


def source_route_edits(root: Path) -> list[tuple[Path, str, str, str]]:
    policy = source_route_policy(root)
    edits = []
    for entry in policy.get("management_routes", []):
        path = root / entry["path"] / "SKILL.md"
        if not inside(path, root) or not path.is_file():
            raise ValueError(f"Missing or unsafe managed routing source: {path}")
        edits.append((path, ROUTE_START, ROUTE_END, source_route_block(root)))
    for entry in policy.get("management_script_routes", []):
        path = root / entry["path"]
        if not inside(path, root) or not path.is_file():
            raise ValueError(f"Missing or unsafe managed routing script: {path}")
        edits.append((path, SCRIPT_ROUTE_START, SCRIPT_ROUTE_END, script_route_block()))
    return edits


def sync_source_routes(root: Path) -> None:
    replacements = []
    for path, start, end, block in source_route_edits(root):
        current = path.read_text(encoding="utf-8")
        if start in current or end in current:
            if current.count(start) != 1 or current.count(end) != 1 or current.index(end) < current.index(start):
                raise ValueError(f"Malformed source management route: {path}")
            left = current.index(start)
            right = current.index(end) + len(end)
            updated = current[:left] + block + current[right:]
        elif path.name == "SKILL.md":
            lines = current.splitlines(keepends=True)
            if not lines or lines[0].strip() != "---":
                raise ValueError(f"Missing source frontmatter: {path}")
            close = next((i for i,line in enumerate(lines[1:],1) if line.strip() == "---"), None)
            if close is None:
                raise ValueError(f"Unclosed source frontmatter: {path}")
            updated = "".join(lines[:close+1]) + "\n\n" + block + "\n" + "".join(lines[close+1:])
        else:
            lines = current.splitlines(keepends=True)
            if not lines or not lines[0].startswith("#!"):
                raise ValueError(f"Missing script shebang: {path}")
            updated = lines[0] + block + "\n" + "".join(lines[1:])
        if updated != current:
            replacements.append((path, updated))
    for path, content in replacements:
        path.write_text(content, encoding="utf-8")


def source_route_issues(root: Path) -> list[str]:
    issues = []
    try:
        edits = source_route_edits(root)
    except ValueError as error:
        return [str(error)]
    for path, start, end, block in edits:
        content = path.read_text(encoding="utf-8")
        if content.count(start) != 1 or content.count(end) != 1:
            issues.append(f"MISSING_SOURCE_MANAGEMENT_ROUTE {path}")
        elif content[content.index(start):content.index(end)+len(end)] != block:
            issues.append(f"OUTDATED_SOURCE_MANAGEMENT_ROUTE {path}")
    return issues


def bootstrap_manager_entry() -> None:
    for runtime in runtime_dirs():
        ensure_link(runtime, "jc-skill-installer", SKILL_DIR)
    ensure_link(claude_runtime_dir(), "jc-skill-installer", SKILL_DIR)
    ensure_link(gemini_runtime_dir(), "jc-skill-installer", SKILL_DIR)
    sync_managed_rules(DEFAULT_ROOT)


def same_location(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except (FileNotFoundError, OSError):
        return left.absolute() == right.absolute()


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def frontmatter(path: Path) -> tuple[str, str]:
    skill_file = path / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError(f"Missing SKILL.md: {skill_file}")
    name = ""
    description = ""
    description_lines: list[str] = []
    in_description_block = False
    for line in skill_file.read_text(encoding="utf-8").splitlines()[1:]:
        if line.strip() == "---":
            break
        if in_description_block:
            if line.startswith((" ", "\t")) or not line.strip():
                description_lines.append(line.strip())
                continue
            in_description_block = False
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip("'\"")
        elif line.startswith("description:"):
            description = line.split(":", 1)[1].strip().strip("'\"")
            if re.fullmatch(r"[|>][+-]?", description):
                in_description_block = True
                description = ""
    if description_lines:
        description = " ".join(description_lines).strip()
    if not name:
        raise ValueError(f"Missing frontmatter name: {skill_file}")
    return name, description


def skill_paths(target: Path) -> list[Path]:
    """Return a directly linked Skill or Skills nested in a linked repository container."""
    if (target / "SKILL.md").is_file():
        return [target]
    paths = sorted(
        skill_file.parent
        for skill_file in target.rglob("SKILL.md")
        if ".git" not in skill_file.parts
    )
    if not paths:
        raise ValueError(f"No SKILL.md found under runtime target: {target}")
    return paths


def load_manifest(path: Path) -> dict:
    if not path.is_file():
        return {"version": 1, "skills": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("skills"), list):
        raise ValueError(f"Unsupported manifest: {path}")
    return data


def save_manifest(path: Path, entries: dict[str, str]) -> None:
    payload = {
        "version": 1,
        "source_root": "auto:parent-of-jc-skill-installer",
        "skills": [{"name": name, "path": entries[name]} for name in sorted(entries)],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def manifest_entries(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for item in load_manifest(path)["skills"]:
        name = item.get("name")
        relative = item.get("path")
        if not isinstance(name, str) or not isinstance(relative, str) or not name or not relative:
            raise ValueError(f"Invalid manifest entry: {item!r}")
        if name in entries and entries[name] != relative:
            raise ValueError(f"Duplicate manifest name: {name}")
        entries[name] = relative
    return entries


def load_channels(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("channels"), list):
        raise ValueError(f"Unsupported Skill channel registry: {path}")
    result: dict[str, dict] = {}
    for item in data["channels"]:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid Skill channel entry: {item!r}")
        family = item.get("family")
        latest = item.get("latest")
        versions = item.get("versions")
        if (
            not isinstance(family, str)
            or not family
            or not isinstance(latest, str)
            or not isinstance(versions, dict)
            or latest not in versions
            or not all(
                isinstance(version, str)
                and version
                and isinstance(relative, str)
                and relative
                for version, relative in versions.items()
            )
        ):
            raise ValueError(f"Invalid Skill channel entry: {item!r}")
        if family in result:
            raise ValueError(f"Duplicate Skill channel family: {family}")
        result[family] = item
    return result


def save_channels(path: Path, channels: dict[str, dict]) -> None:
    payload = {
        "version": 1,
        "channels": [channels[family] for family in sorted(channels)],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_profiles(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("profiles"), list):
        raise ValueError(f"Unsupported Skill profile registry: {path}")
    result: dict[str, dict] = {}
    for item in data["profiles"]:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid Skill profile entry: {item!r}")
        name = item.get("name")
        skills = item.get("skills", [])
        channel_families = item.get("channels", [])
        required_prefixes = item.get("require_all_prefixes", [])
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(skills, list)
            or not all(isinstance(relative, str) and relative for relative in skills)
            or not isinstance(channel_families, list)
            or not all(
                isinstance(family, str) and family for family in channel_families
            )
            or not isinstance(required_prefixes, list)
            or not all(
                isinstance(prefix, str) and prefix for prefix in required_prefixes
            )
        ):
            raise ValueError(f"Invalid Skill profile entry: {item!r}")
        if name in result:
            raise ValueError(f"Duplicate Skill profile: {name}")
        result[name] = item
    return result


def resolve_profile(
    root: Path, channels_path: Path, profiles_path: Path, profile_name: str
) -> dict[str, str]:
    profiles = load_profiles(profiles_path)
    profile = profiles.get(profile_name)
    if profile is None:
        raise ValueError(f"Unknown Skill profile: {profile_name}")
    relative_paths = list(profile.get("skills", []))
    channels = load_channels(channels_path)
    for family in profile.get("channels", []):
        channel = channels.get(family)
        if channel is None:
            raise ValueError(f"Profile {profile_name} references unknown channel: {family}")
        relative_paths.append(channel["versions"][channel["latest"]])
    entries: dict[str, str] = {}
    for relative in relative_paths:
        target = (root / relative).resolve()
        if not inside(target, root):
            raise ValueError(f"Profile path escapes source root: {relative}")
        frontmatter(target)
        normalized = str(target.relative_to(root.resolve()))
        link_name = target.name
        if link_name in entries and entries[link_name] != normalized:
            raise ValueError(
                f"Profile runtime name conflict: {link_name} -> "
                f"{entries[link_name]} and {normalized}"
            )
        entries[link_name] = normalized
    required_prefixes = profile.get("require_all_prefixes", [])
    if required_prefixes:
        desired_paths = set(entries.values())
        missing: list[str] = []
        for path in catalog_skill_paths(root):
            try:
                declared_name, _ = frontmatter(path)
            except ValueError:
                if any(path.name.startswith(prefix) for prefix in required_prefixes):
                    raise
                continue
            if not any(declared_name.startswith(prefix) for prefix in required_prefixes):
                continue
            relative = str(path.resolve().relative_to(root.resolve()))
            if relative not in desired_paths:
                missing.append(relative)
        if missing:
            raise ValueError(
                f"Profile {profile_name} omits required Skills: {', '.join(sorted(missing))}"
            )
    return entries


def profile_diff(current: dict[str, str], desired: dict[str, str]) -> tuple[list[str], list[str]]:
    current_paths = set(current.values())
    desired_paths = set(desired.values())
    return sorted(desired_paths - current_paths), sorted(current_paths - desired_paths)


def channel_paths(root: Path, channel: dict) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for version, relative in channel["versions"].items():
        target = (root / relative).resolve()
        if not inside(target, root):
            raise ValueError(
                f"Skill channel path escapes source root: {channel['family']} {version} -> {relative}"
            )
        frontmatter(target)
        paths[version] = target
    return paths


def select_latest(
    root: Path, manifest: Path, channels_path: Path, family: str
) -> tuple[str, str, str]:
    channels = load_channels(channels_path)
    channel = channels.get(family)
    if channel is None:
        raise ValueError(f"Unknown Skill channel family: {family}")
    paths = channel_paths(root, channel)
    latest = channel["latest"]
    target = paths[latest]
    latest_relative = str(target.relative_to(root.resolve()))
    family_relatives = {
        str(candidate.relative_to(root.resolve())) for candidate in paths.values()
    }
    entries = {
        link_name: relative
        for link_name, relative in manifest_entries(manifest).items()
        if str((root / relative).resolve().relative_to(root.resolve())) not in family_relatives
    }
    link_name = target.name
    if link_name in entries and entries[link_name] != latest_relative:
        raise ValueError(f"Manifest link conflict: {link_name} -> {entries[link_name]}")
    declared_name, _ = frontmatter(target)
    entries[link_name] = latest_relative
    save_manifest(manifest, entries)
    return family, latest, declared_name


def promote_latest(
    root: Path,
    manifest: Path,
    channels_path: Path,
    family: str,
    version: str,
) -> tuple[str, str, str]:
    channels = load_channels(channels_path)
    channel = channels.get(family)
    if channel is None:
        raise ValueError(f"Unknown Skill channel family: {family}")
    if version not in channel["versions"]:
        available = ", ".join(sorted(channel["versions"]))
        raise ValueError(f"Unknown version for {family}: {version}; available: {available}")
    channel_paths(root, channel)
    channel["latest"] = version
    save_channels(channels_path, channels)
    return select_latest(root, manifest, channels_path, family)


def channel_issues(root: Path, manifest: Path, channels_path: Path) -> list[str]:
    issues: list[str] = []
    channels = load_channels(channels_path)
    active_relatives = set(manifest_entries(manifest).values())
    for family, channel in channels.items():
        try:
            paths = channel_paths(root, channel)
        except ValueError as error:
            issues.append(str(error))
            continue
        relatives = {
            version: str(target.relative_to(root.resolve()))
            for version, target in paths.items()
        }
        active_versions = [
            version for version, relative in relatives.items() if relative in active_relatives
        ]
        if len(active_versions) > 1:
            issues.append(
                f"MULTIPLE_ACTIVE_VERSIONS {family}: {', '.join(sorted(active_versions))}"
            )
        elif active_versions and active_versions[0] != channel["latest"]:
            issues.append(
                f"STALE_LATEST_CHANNEL {family}: active={active_versions[0]} "
                f"latest={channel['latest']}"
            )
    return issues


def catalog_skill_paths(root: Path) -> list[Path]:
    """Discover source Skills without following runtime or dependency trees."""
    ignored = {".git", ".backups", "node_modules", "__pycache__", ".venv", "venv"}
    paths: list[Path] = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if name not in ignored and not (current_path / name).is_symlink()
        ]
        if "SKILL.md" in files:
            paths.append(current_path)
    return sorted(paths)


def search_catalog(
    root: Path, manifest: Path, query: str, limit: int = 12
) -> list[dict[str, object]]:
    normalized_query = " ".join(query.lower().split())
    if not normalized_query:
        raise ValueError("Search query must not be empty")
    base_tokens = [
        token for token in re.split(r"[^0-9a-z\u4e00-\u9fff]+", normalized_query) if token
    ]
    tokens: list[str] = []
    for token in base_tokens:
        tokens.append(token)
        if len(token) >= 4 and all("\u4e00" <= character <= "\u9fff" for character in token):
            tokens.extend(token[index : index + 2] for index in range(len(token) - 1))
    tokens = list(dict.fromkeys(tokens))
    active_paths: set[Path] = set()
    for relative in manifest_entries(manifest).values():
        target = (root / relative).resolve()
        if inside(target, root):
            try:
                active_paths.update(path.resolve() for path in skill_paths(target))
            except ValueError:
                continue
    records: list[dict[str, object]] = []
    for path in catalog_skill_paths(root):
        try:
            name, description = frontmatter(path)
        except (OSError, ValueError):
            continue
        relative = str(path.resolve().relative_to(root.resolve()))
        name_text = name.lower()
        path_text = relative.lower()
        description_text = description.lower()
        score = 0
        if normalized_query in name_text:
            score += 120
        if normalized_query in path_text:
            score += 60
        if normalized_query in description_text:
            score += 45
        for token in tokens:
            if token in name_text:
                score += 25
            if token in path_text:
                score += 12
            if token in description_text:
                score += 8
        if score == 0:
            continue
        records.append(
            {
                "name": name,
                "path": relative,
                "description": description,
                "active": path.resolve() in active_paths,
                "score": score,
            }
        )
    records.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
    return records[:limit]


def ensure_link(runtime: Path, name: str, target: Path) -> None:
    link = runtime / name
    if link.is_symlink():
        if link.resolve() == target.resolve():
            return
        raise ValueError(f"Conflicting symlink: {link} -> {os.readlink(link)}")
    if link.exists():
        raise ValueError(f"Refusing to replace real runtime entry: {link}")
    link.symlink_to(target)


def codebuddy_entries(root: Path, manifest: Path) -> dict[str, Path]:
    """Flatten active manifest targets into CodeBuddy's one-Skill-per-folder layout."""
    result: dict[str, Path] = {}
    for link_name, relative in manifest_entries(manifest).items():
        target = (root / relative).resolve()
        if not inside(target, root):
            raise ValueError(f"Manifest path escapes source root: {relative}")
        nested_skills = skill_paths(target)
        for skill_path in nested_skills:
            declared_name, _ = frontmatter(skill_path)
            codebuddy_name = link_name if len(nested_skills) == 1 else declared_name
            if "/" in codebuddy_name or codebuddy_name in {".", ".."}:
                raise ValueError(f"Unsafe CodeBuddy Skill name: {codebuddy_name}")
            previous = result.get(codebuddy_name)
            if previous and previous != skill_path:
                raise ValueError(
                    f"CodeBuddy Skill name conflict: {codebuddy_name} -> "
                    f"{previous} and {skill_path}"
                )
            result[codebuddy_name] = skill_path
    return result


def sync_flat_runtime(root: Path, manifest: Path, runtime: Path) -> tuple[int, int]:
    """Reconcile a flat runtime directory with the active manifest."""
    runtime.mkdir(parents=True, exist_ok=True)
    desired = codebuddy_entries(root, manifest)
    # Refuse conflicts before removing or creating any entry.
    for name in desired:
        entry = runtime / name
        if entry.exists() and not entry.is_symlink():
            raise ValueError(f"Refusing to replace real runtime entry: {entry}")
    removed = 0
    for entry in runtime.iterdir():
        target = desired.get(entry.name)
        if entry.is_symlink():
            if target is not None and entry.resolve() == target.resolve():
                continue
            entry.unlink()
            removed += 1
            continue
        if entry.name in desired:
            raise ValueError(f"Refusing to replace real runtime entry: {entry}")
    for name, target in desired.items():
        ensure_link(runtime, name, target)
    return len(desired), removed


def sync_codebuddy(root: Path, manifest: Path, project: Path) -> tuple[int, int]:
    """Reconcile a project's .codebuddy/skills symlinks with the active manifest."""
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise ValueError(f"Unsafe or missing CodeBuddy project root: {project}")
    return sync_flat_runtime(root, manifest, project / ".codebuddy" / "skills")


def sync_claude(root: Path, manifest: Path) -> tuple[int, int]:
    """Reconcile Claude Code with the same active manifest used by Codex."""
    return sync_flat_runtime(root, manifest, claude_runtime_dir())


def sync_gemini(root: Path, manifest: Path) -> tuple[int, int]:
    """Reconcile Antigravity/Gemini with the same active manifest used by Codex."""
    return sync_flat_runtime(root, manifest, gemini_runtime_dir())


def sync_dsh(root: Path, manifest: Path) -> tuple[int, int]:
    """Reconcile DeepSeek Harness ~/.dsh/skills with the active manifest."""
    return sync_flat_runtime(root, manifest, dsh_runtime_dir())


def sync_workbuddy(root: Path, manifest: Path, dry_run: bool = False) -> tuple[int, int]:
    runtime = workbuddy_runtime_dir()
    if runtime is None:
        return 0, 0
    desired = codebuddy_entries(root, manifest)
    if runtime.is_dir():
        for name in desired:
            entry = runtime / name
            if entry.exists() and not entry.is_symlink():
                raise ValueError(f"Refusing to replace real WorkBuddy entry: {entry}")
    if dry_run:
        removed = sum(entry.is_symlink() and
                      (entry.name not in desired or entry.resolve() != desired[entry.name].resolve())
                      for entry in runtime.iterdir()) if runtime.is_dir() else 0
        return len(desired), removed
    return sync_flat_runtime(root, manifest, runtime)


def sync_kimi_code(root: Path, manifest: Path, dry_run: bool = False) -> tuple[int, int]:
    runtime = kimi_code_runtime_dir()
    if runtime is None:
        return 0, 0
    desired = codebuddy_entries(root, manifest)
    if runtime.is_dir():
        for name in desired:
            entry = runtime / name
            if entry.exists() and not entry.is_symlink():
                raise ValueError(f"Refusing to replace real Kimi Code entry: {entry}")
    if dry_run:
        removed = sum(entry.is_symlink() and
                      (entry.name not in desired or entry.resolve() != desired[entry.name].resolve())
                      for entry in runtime.iterdir()) if runtime.is_dir() else 0
        return len(desired), removed
    return sync_flat_runtime(root, manifest, runtime)


def describe_sync(results: tuple[tuple[int, int], ...]) -> str:
    names = ("Codex", "Claude Code", "CodeBuddy", "Gemini", "DeepSeek Harness", "Kimi Work", "WorkBuddy", "Grok Build", "Kimi Code")
    parts = [
        (f"{name} {linked} source Skills via config ({removed} retired mirror links removed)"
         if name == "Grok Build" else f"{name} {linked} links ({removed} stale removed)")
        for name, (linked, removed) in zip(names, results, strict=True)
    ]
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def sync_codex(root: Path, manifest: Path) -> tuple[int, int]:
    """Reconcile every Codex runtime with the canonical flat Skill mapping."""
    linked = 0
    removed = 0
    for runtime in runtime_dirs():
        runtime_linked, runtime_removed = sync_flat_runtime(root, manifest, runtime)
        linked = runtime_linked
        removed += runtime_removed
    return linked, removed


def sync_default_flat_runtimes(
    root: Path, manifest: Path
) -> tuple[tuple[int, int], ...]:
    sync_managed_rules(root)
    return (
        sync_codex(root, manifest),
        sync_claude(root, manifest),
        sync_codebuddy(root, manifest, DEFAULT_CODEBUDDY_PROJECT),
        sync_gemini(root, manifest),
        sync_dsh(root, manifest),
        sync_kimi_work(root, manifest),
        sync_workbuddy(root, manifest),
        sync_grok(root, manifest),
        sync_kimi_code(root, manifest),
    )


def audit_flat_runtime(root: Path, manifest: Path, runtime: Path) -> list[str]:
    issues: list[str] = []
    desired = codebuddy_entries(root, manifest)
    if not runtime.is_dir():
        return [f"MISSING_RUNTIME {runtime}"]
    for name, target in desired.items():
        link = runtime / name
        if not link.is_symlink():
            issues.append(f"MISSING_LINK {link}")
        elif link.resolve() != target.resolve():
            issues.append(f"WRONG_LINK {link} -> {os.readlink(link)}")
    for entry in runtime.iterdir():
        if entry.is_symlink() and entry.name not in desired:
            issues.append(f"STALE_LINK {entry} -> {os.readlink(entry)}")
        elif entry.name not in desired and entry.name != ".system" and entry.name not in platform_owned(runtime):
            if entry.is_dir() and any(entry.rglob("SKILL.md")):
                issues.append(f"UNMANAGED_REAL_SKILL {entry}")
    return issues


def audit_codebuddy(root: Path, manifest: Path, project: Path) -> list[str]:
    runtime = project.expanduser().resolve() / ".codebuddy" / "skills"
    return audit_flat_runtime(root, manifest, runtime)


def source_self_links(root: Path) -> list[Path]:
    """Find links directly inside a Skill that resolve back to that Skill directory."""
    links: list[Path] = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if name not in {".git", ".backups"} and not (current_path / name).is_symlink()
        ]
        if "SKILL.md" not in files:
            continue
        for child in current_path.iterdir():
            if not child.is_symlink():
                continue
            try:
                if child.resolve() == current_path.resolve():
                    links.append(child)
            except (OSError, RuntimeError):
                continue
    return sorted(links)


def prune_source_self_links(root: Path) -> int:
    links = source_self_links(root)
    for link in links:
        skill_dir = link.parent
        if (
            not link.is_symlink()
            or not (skill_dir / "SKILL.md").is_file()
            or link.resolve() != skill_dir.resolve()
        ):
            raise ValueError(f"Refusing unsafe source-link removal: {link}")
    for link in links:
        link.unlink()
    return len(links)


def activate(root: Path, manifest: Path, relative: str) -> str:
    target = (root / relative).resolve()
    if not inside(target, root):
        raise ValueError(f"Skill path escapes source root: {relative}")
    name, _ = frontmatter(target)
    link_name = target.name
    entries = manifest_entries(manifest)
    if link_name in entries and entries[link_name] != relative:
        raise ValueError(f"Manifest link conflict: {link_name} -> {entries[link_name]}")
    entries[link_name] = str(target.relative_to(root.resolve()))
    save_manifest(manifest, entries)
    if name == "jc-skill-installer":
        bootstrap_manager_entry()
    return name


def deactivate(root: Path, manifest: Path, name: str) -> None:
    if name == "jc-skill-installer":
        raise ValueError("Cannot deactivate jc-skill-installer: it is the required cross-client management entry")
    entries = manifest_entries(manifest)
    link_name = name
    relative = entries.get(link_name)
    if relative is None:
        matches = []
        for candidate_link, candidate_relative in entries.items():
            candidate_target = (root / candidate_relative).resolve()
            try:
                declared_name, _ = frontmatter(candidate_target)
            except ValueError:
                continue
            if declared_name == name:
                matches.append((candidate_link, candidate_relative))
        if len(matches) == 1:
            link_name, relative = matches[0]
        elif len(matches) > 1:
            raise ValueError(f"Ambiguous declared Skill name: {name}")
    if relative is None:
        raise ValueError(f"Skill is not active in manifest: {name}")
    entries.pop(link_name)
    save_manifest(manifest, entries)


def export_links(root: Path, manifest: Path) -> int:
    entries: dict[str, str] = {}
    for runtime in runtime_dirs():
        for link in runtime.iterdir():
            if not link.is_symlink():
                continue
            target = link.resolve()
            if not inside(target, root):
                continue
            skill_paths(target)
            relative = str(target.relative_to(root.resolve()))
            if link.name in entries and entries[link.name] != relative:
                raise ValueError(f"Runtime name conflict: {link.name}")
            entries[link.name] = relative
    save_manifest(manifest, entries)
    return len(entries)


def bootstrap(root: Path, manifest: Path) -> int:
    bootstrap_manager_entry()
    entries = manifest_entries(manifest)
    for link_name, relative in entries.items():
        target = (root / relative).resolve()
        if not inside(target, root):
            raise ValueError(f"Manifest path escapes source root: {relative}")
        nested_skills = skill_paths(target)
        for nested_skill in nested_skills:
            frontmatter(nested_skill)
    return len(entries)


def prune_broken() -> int:
    removed = 0
    runtimes = runtime_dirs() + [
        claude_runtime_dir(),
        gemini_runtime_dir(),
        DEFAULT_CODEBUDDY_PROJECT / ".codebuddy" / "skills",
        dsh_runtime_dir(),
    ]
    for runtime in runtimes:
        if not runtime.is_dir():
            continue
        for link in runtime.iterdir():
            if link.is_symlink() and not link.exists():
                link.unlink()
                removed += 1
    return removed


def audit(root: Path, manifest: Path, channels_path: Path = DEFAULT_CHANNELS) -> list[str]:
    issues: list[str] = []
    issues.extend(audit_managed_rules(root))
    entries = manifest_entries(manifest)
    issues.extend(channel_issues(root, manifest, channels_path))
    for link in source_self_links(root):
        issues.append(f"SOURCE_SELF_LINK {link} -> {os.readlink(link)}")
    manager_target = SKILL_DIR.resolve()
    claude_link = claude_runtime_dir() / "jc-skill-installer"
    if not claude_link.is_symlink():
        issues.append(f"MISSING_LINK {claude_link}")
    elif claude_link.resolve() != manager_target:
        issues.append(f"WRONG_LINK {claude_link} -> {os.readlink(claude_link)}")
    gemini_link = gemini_runtime_dir() / "jc-skill-installer"
    if not gemini_link.is_symlink():
        issues.append(f"MISSING_LINK {gemini_link}")
    elif gemini_link.resolve() != manager_target:
        issues.append(f"WRONG_LINK {gemini_link} -> {os.readlink(gemini_link)}")
    for rule_path in [
        Path.home() / ".codex" / "AGENTS.md",
        Path.home() / ".claude" / "CLAUDE.md",
        Path.home() / ".gemini" / "GEMINI.md",
    ]:
        content = rule_path.read_text(encoding="utf-8") if rule_path.is_file() else ""
        if content.count(MANAGED_START) != 1 or content.count(MANAGED_END) != 1:
            issues.append(f"MISSING_MANAGED_RULE {rule_path}")
    declared: dict[str, tuple[str, Path]] = {}
    for link_name, relative in entries.items():
        target = (root / relative).resolve()
        if not inside(target, root):
            issues.append(f"ESCAPES_ROOT {link_name}: {relative}")
            continue
        try:
            for nested_skill in skill_paths(target):
                declared_name, _ = frontmatter(nested_skill)
                previous = declared.get(declared_name)
                if previous and previous[1] != nested_skill:
                    issues.append(
                        f"DUPLICATE_SKILL_NAME {declared_name}: "
                        f"{previous[0]} -> {previous[1]} and {link_name} -> {nested_skill}"
                    )
                else:
                    declared[declared_name] = (link_name, nested_skill)
        except ValueError as error:
            issues.append(str(error))
    for runtime in runtime_dirs():
        issues.extend(audit_flat_runtime(root, manifest, runtime))
    issues.extend(audit_flat_runtime(root, manifest, claude_runtime_dir()))
    issues.extend(audit_flat_runtime(root, manifest, gemini_runtime_dir()))
    issues.extend(audit_codebuddy(root, manifest, DEFAULT_CODEBUDDY_PROJECT))
    issues.extend(audit_flat_runtime(root, manifest, dsh_runtime_dir()))
    issues.extend(audit_kimi_work(root, manifest))
    workbuddy = workbuddy_runtime_dir()
    if workbuddy is not None:
        issues.extend(audit_flat_runtime(root, manifest, workbuddy))
        rule = Path.home() / ".workbuddy" / "WORKBUDDY.md"
        content = rule.read_text(encoding="utf-8") if rule.is_file() else ""
        if MANAGED_START not in content or MANAGED_END not in content:
            issues.append(f"MISSING_MANAGED_RULE {rule}")
    issues.extend(audit_grok(root, manifest))
    kimi_code = kimi_code_runtime_dir()
    if kimi_code is not None:
        issues.extend(audit_flat_runtime(root, manifest, kimi_code))
    deprecated = Path.home() / ".agents" / "skills"
    if deprecated.is_dir() and any(deprecated.rglob("SKILL.md")):
        issues.append(f"DEPRECATED_SKILLS_RUNTIME {deprecated}")
    return issues


def sync_and_check(root: Path, manifest: Path, channels_path: Path = DEFAULT_CHANNELS) -> tuple[tuple[int, int], ...]:
    results = sync_default_flat_runtimes(root, manifest)
    issues = audit(root, manifest, channels_path)
    if issues:
        raise ValueError("Synchronization verification failed:\n" + "\n".join(issues))
    return results


def complete_update(root: Path, manifest: Path, relative: str, channels_path: Path) -> str:
    target = (root / relative).resolve()
    if not inside(target, root) or not target.is_dir():
        raise ValueError(f"Unsafe or missing source Skill: {relative}")
    for family, channel in load_channels(channels_path).items():
        for version, path in channel["versions"].items():
            if target == (root / path).resolve() and version != channel["latest"]:
                raise ValueError(f"Cannot update archived {family}:{version}; update the latest entry instead")
    name, _ = frontmatter(target)
    if target.name != name:
        raise ValueError(f"Source directory does not match declared Skill name: {target}")
    return name


def resolve_dbs_source(root: Path, value: str) -> Path:
    source = Path(value).expanduser()
    candidates = [source, root / "dbskill" / source,
                  root / "dbskill" / "skills" / source, root / source]
    target = next((p.resolve() for p in candidates if p.is_dir()), None)
    if target is None or target == root or not inside(target, root):
        raise ValueError("DBS installer is delegated to JC management: import the candidate into the canonical repository first, then activate its relative source path")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--channels", type=Path, default=DEFAULT_CHANNELS)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("audit")
    sub.add_parser("channels")
    sub.add_parser("profiles")
    sub.add_parser("prune-broken")
    sub.add_parser("prune-source-self-links")
    sub.add_parser("export")
    sub.add_parser("bootstrap")
    sub.add_parser("rules")
    sub.add_parser("sync-rules")
    sub.add_parser("reconcile")
    sub.add_parser("sync-claude")
    sub.add_parser("sync-gemini")
    sub.add_parser("sync-dsh")
    for command in ("sync-workbuddy", "sync-grok", "sync-kimi-code"):
        sub.add_parser(command).add_argument("--dry-run", action="store_true")
    kimi_parser = sub.add_parser("sync-kimi-work")
    kimi_parser.add_argument("--dry-run", action="store_true")
    codebuddy_parser = sub.add_parser("sync-codebuddy")
    codebuddy_parser.add_argument(
        "project_root", type=Path, nargs="?", default=DEFAULT_CODEBUDDY_PROJECT
    )
    activate_parser = sub.add_parser("activate")
    activate_parser.add_argument("path")
    update_parser = sub.add_parser("update")
    update_parser.add_argument("path")
    bridge_parser = sub.add_parser("dbs-route")
    bridge_parser.add_argument("action", choices=("link", "unlink", "status"))
    bridge_parser.add_argument("source")
    deactivate_parser = sub.add_parser("deactivate")
    deactivate_parser.add_argument("name")
    latest_parser = sub.add_parser("select-latest")
    latest_parser.add_argument("family")
    promote_parser = sub.add_parser("promote")
    promote_parser.add_argument("family")
    promote_parser.add_argument("version")
    search_parser = sub.add_parser("search")
    search_parser.add_argument("query", nargs="+")
    search_parser.add_argument("--limit", type=int, default=12)
    search_parser.add_argument("--json", action="store_true")
    profile_diff_parser = sub.add_parser("profile-diff")
    profile_diff_parser.add_argument("name")
    apply_profile_parser = sub.add_parser("apply-profile")
    apply_profile_parser.add_argument("name")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    manifest = args.manifest.expanduser().resolve()
    channels_path = args.channels.expanduser().resolve()
    profiles_path = args.profiles.expanduser().resolve()
    if not root.is_dir() or root == Path.home().resolve():
        raise ValueError(f"Unsafe or missing source root: {root}")
    if args.command == "audit":
        issues = audit(root, manifest, channels_path)
        if issues:
            print("\n".join(issues))
            return 1
        print(f"OK: {len(manifest_entries(manifest))} active Skills are consistent")
    elif args.command == "rules":
        issues = audit_managed_rules(root)
        for client, path in managed_rule_targets():
            print(f"{client}: {path}")
        print("grok: inherits the Claude global rule (verified by Grok inspect during audit)")
        if issues:
            print("\n".join(issues))
            return 1
        print("OK: all installed-client management rules match the source manager")
    elif args.command == "sync-rules":
        count = sync_managed_rules(root)
        issues = audit_managed_rules(root)
        if issues:
            raise ValueError("\n".join(issues))
        print(f"Synced and verified {count} management rule files")
    elif args.command in {"update", "reconcile"}:
        name = complete_update(root, manifest, args.path, channels_path) if args.command == "update" else None
        synced = sync_and_check(root, manifest, channels_path)
        print(f"{'Updated ' + name if name else 'Reconciled active Skills'}; synced and verified {describe_sync(synced)}")
    elif args.command == "dbs-route":
        target = resolve_dbs_source(root, args.source)
        targets = skill_paths(target)
        if args.action == "status":
            issues = audit(root, manifest, channels_path)
            if issues:
                raise ValueError("\n".join(issues))
            active = codebuddy_entries(root, manifest)
            for directory in targets:
                name, _ = frontmatter(directory)
                state = "active" if name in active and active[name].resolve() == directory.resolve() else "inactive"
                print(f"{name} [{state}]: {directory}")
            print(f"OK: JC manager verified {len(manifest_entries(manifest))} active Skills across installed clients")
        else:
            changed = []
            for directory in targets:
                name, _ = frontmatter(directory)
                if args.action == "link":
                    activate(root, manifest, str(directory.relative_to(root)))
                    changed.append(name)
                elif name in manifest_entries(manifest):
                    deactivate(root, manifest, name)
                    changed.append(name)
            synced = sync_and_check(root, manifest, channels_path)
            print(f"Delegated DBS {args.action}: {len(changed)} Skills; synced and verified {describe_sync(synced)}")
    elif args.command == "channels":
        channels = load_channels(channels_path)
        if not channels:
            print("No version channels configured")
        for family, channel in sorted(channels.items()):
            versions = ", ".join(
                f"{version}={relative}" for version, relative in sorted(channel["versions"].items())
            )
            print(f"{family}: latest={channel['latest']} ({versions})")
    elif args.command == "profiles":
        profiles = load_profiles(profiles_path)
        if not profiles:
            print("No activation profiles configured")
        for name, profile in sorted(profiles.items()):
            description = profile.get("description", "")
            desired = resolve_profile(root, channels_path, profiles_path, name)
            print(f"{name}: {len(desired)} Skills - {description}")
    elif args.command in {"profile-diff", "apply-profile"}:
        desired = resolve_profile(root, channels_path, profiles_path, args.name)
        activate_paths, deactivate_paths = profile_diff(
            manifest_entries(manifest), desired
        )
        if args.command == "profile-diff":
            print(
                f"Profile {args.name}: {len(desired)} desired, "
                f"{len(activate_paths)} to activate, {len(deactivate_paths)} to deactivate"
            )
            if activate_paths:
                print("ACTIVATE")
                print("\n".join(f"  {path}" for path in activate_paths))
            if deactivate_paths:
                print("DEACTIVATE")
                print("\n".join(f"  {path}" for path in deactivate_paths))
        else:
            save_manifest(manifest, desired)
            synced = sync_and_check(root, manifest, channels_path)
            print(
                f"Applied profile {args.name}: {len(desired)} active Skills; "
                f"synced {describe_sync(synced)}"
            )
    elif args.command == "search":
        if args.limit < 1 or args.limit > 100:
            raise ValueError("Search limit must be between 1 and 100")
        records = search_catalog(root, manifest, " ".join(args.query), args.limit)
        if args.json:
            print(json.dumps(records, ensure_ascii=False, indent=2))
        elif not records:
            print("No matching Skills found")
        else:
            for record in records:
                state = "active" if record["active"] else "inactive"
                print(
                    f"{record['name']} [{state}] {record['path']}\n"
                    f"  {record['description']}"
                )
    elif args.command == "export":
        count = export_links(root, manifest)
        synced = sync_and_check(root, manifest, channels_path)
        print(
            f"Exported {count} active Skills to {manifest}; "
            f"synced {describe_sync(synced)}"
        )
    elif args.command == "bootstrap":
        count = bootstrap(root, manifest)
        synced = sync_and_check(root, manifest, channels_path)
        print(
            f"Bootstrapped {count} active Skills; "
            f"synced {describe_sync(synced)}"
        )
    elif args.command == "sync-claude":
        linked, removed = sync_claude(root, manifest)
        print(
            f"Synced {linked} active Skills to {claude_runtime_dir()} "
            f"({removed} stale links removed)"
        )
    elif args.command == "sync-gemini":
        linked, removed = sync_gemini(root, manifest)
        print(
            f"Synced {linked} active Skills to {gemini_runtime_dir()} "
            f"({removed} stale links removed)"
        )
    elif args.command == "sync-dsh":
        linked, removed = sync_dsh(root, manifest)
        print(
            f"Synced {linked} active Skills to {dsh_runtime_dir()} "
            f"({removed} stale links removed)"
        )
    elif args.command in {"sync-workbuddy", "sync-grok", "sync-kimi-code"}:
        if args.command == "sync-workbuddy" and workbuddy_runtime_dir() is None:
            raise ValueError("WorkBuddy user root not found")
        if args.command == "sync-grok" and grok_binary() is None:
            raise ValueError("Grok Build executable not found")
        if args.command == "sync-kimi-code" and kimi_code_runtime_dir() is None:
            raise ValueError("Kimi Code desktop user root not found")
        sync = {"sync-workbuddy": sync_workbuddy, "sync-grok": sync_grok,
                "sync-kimi-code": sync_kimi_code}[args.command]
        linked, removed = sync(root, manifest, args.dry_run)
        action = "Would sync" if args.dry_run else "Synced"
        print(f"{action} {linked} active Skills via {args.command} ({removed} stale links)")
    elif args.command == "sync-kimi-work":
        runtime = kimi_work_runtime_dir()
        if runtime is None:
            raise ValueError("Kimi Work root not found; set JC_KIMI_WORK_SKILLS_DIR")
        linked, removed = sync_kimi_work(root, manifest, runtime, args.dry_run)
        action = "Would sync" if args.dry_run else "Synced"
        print(f"{action} {linked} active Skills to {runtime} ({removed} managed stale links)")
    elif args.command == "sync-codebuddy":
        linked, removed = sync_codebuddy(root, manifest, args.project_root)
        print(
            f"Synced {linked} active Skills to "
            f"{args.project_root.expanduser().resolve() / '.codebuddy' / 'skills'}"
            f" ({removed} stale links removed)"
        )
    elif args.command == "prune-broken":
        print(f"Removed {prune_broken()} broken runtime symlinks")
    elif args.command == "prune-source-self-links":
        print(f"Removed {prune_source_self_links(root)} source self-links")
    elif args.command == "activate":
        name = activate(root, manifest, args.path)
        synced = sync_and_check(root, manifest, channels_path)
        print(f"Activated {name}; synced {describe_sync(synced)}")
    elif args.command == "deactivate":
        deactivate(root, manifest, args.name)
        synced = sync_and_check(root, manifest, channels_path)
        print(f"Deactivated {args.name}; synced {describe_sync(synced)}")
    elif args.command in {"select-latest", "promote"}:
        if args.command == "select-latest":
            family, version, declared_name = select_latest(
                root, manifest, channels_path, args.family
            )
            action = "Selected"
        else:
            family, version, declared_name = promote_latest(
                root, manifest, channels_path, args.family, args.version
            )
            action = "Promoted"
        synced = sync_and_check(root, manifest, channels_path)
        print(
            f"{action} {family}:{version} ({declared_name}) as latest; "
            f"synced {describe_sync(synced)}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
