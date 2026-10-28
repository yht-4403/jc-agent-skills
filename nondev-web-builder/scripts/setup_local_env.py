#!/usr/bin/env python3
"""Create the single local secret file used by nondev-web-builder projects."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
IGNORE_BLOCK = """# BEGIN: nondev-web-builder local secrets
.env.local
.env.*.local
# END: nondev-web-builder local secrets
"""
HEADER = """# Local plaintext secrets. Do not share or commit this file.
# Paste each value after the equals sign.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare .env.local, .env.example, and .gitignore safely."
    )
    parser.add_argument("--project", required=True, help="Absolute project root")
    parser.add_argument(
        "--key", action="append", default=[], help="Required variable name; repeat as needed"
    )
    return parser.parse_args()


def validate_project(raw: str) -> Path:
    project = Path(raw).expanduser()
    if not project.is_absolute():
        raise SystemExit("--project must be an absolute path")
    project = project.resolve()
    if not project.is_dir():
        raise SystemExit(f"Project directory does not exist: {project}")
    if project == Path(project.anchor):
        raise SystemExit("Refusing to use a filesystem root as the project")
    return project


def validate_keys(raw_keys: list[str]) -> list[str]:
    keys: list[str] = []
    for key in raw_keys:
        normalized = key.strip()
        if not KEY_PATTERN.fullmatch(normalized):
            raise SystemExit(
                f"Invalid key name {normalized!r}; use uppercase letters, digits, and underscores"
            )
        if normalized not in keys:
            keys.append(normalized)
    return keys


def existing_keys(text: str) -> set[str]:
    found: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name = stripped.split("=", 1)[0].removeprefix("export ").strip()
        if KEY_PATTERN.fullmatch(name):
            found.add(name)
    return found


def append_missing(path: Path, keys: list[str], include_header: bool) -> list[str]:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = [key for key in keys if key not in existing_keys(current)]
    if not path.exists() or missing:
        chunks: list[str] = []
        if not current and include_header:
            chunks.append(HEADER.rstrip())
        if current:
            chunks.append(current.rstrip())
        chunks.extend(f"{key}=" for key in missing)
        path.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
    return missing


def update_gitignore(path: Path) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if "# BEGIN: nondev-web-builder local secrets" in current:
        return False
    prefix = current.rstrip()
    updated = f"{prefix}\n\n{IGNORE_BLOCK}" if prefix else IGNORE_BLOCK
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    args = parse_args()
    project = validate_project(args.project)
    keys = validate_keys(args.key)

    local_path = project / ".env.local"
    example_path = project / ".env.example"
    ignore_path = project / ".gitignore"

    local_added = append_missing(local_path, keys, include_header=True)
    os.chmod(local_path, 0o600)
    example_added = append_missing(example_path, keys, include_header=False)
    ignore_changed = update_gitignore(ignore_path)

    print(f"Prepared local secrets for: {project}")
    print(f"Local file: {local_path} (mode 600)")
    print(f"Example file: {example_path}")
    print(f"Keys added locally: {', '.join(local_added) if local_added else 'none'}")
    print(f"Keys added to example: {', '.join(example_added) if example_added else 'none'}")
    print(f"Git ignore updated: {'yes' if ignore_changed else 'already configured'}")
    print("No secret values were read or printed.")


if __name__ == "__main__":
    main()
