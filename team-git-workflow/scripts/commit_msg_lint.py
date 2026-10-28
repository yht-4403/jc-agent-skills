#!/usr/bin/env python3
"""Validate a team Conventional Commit message draft."""

from __future__ import annotations

import re
import sys
from pathlib import Path


HEADER_RE = re.compile(
    r"^(feat|fix|refactor|perf|test|docs|chore|build|ci|style|revert)"
    r"(\([A-Za-z0-9_.-]+\))?: .+"
)
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
BAD_WORDS = {
    "wip",
    "temp",
    "misc",
    "update",
    "updates",
    "fix bug",
    "修改",
    "调整代码",
}


def load_message(argv: list[str]) -> str:
    if len(argv) > 1:
        return Path(argv[1]).read_text(encoding="utf-8")
    return sys.stdin.read()


def main() -> int:
    message = load_message(sys.argv).strip("\n")
    if not message.strip():
        print("[fail] Commit message must not be empty.")
        return 1

    lines = message.splitlines()
    header = lines[0].strip()
    failures: list[str] = []
    warnings: list[str] = []

    if header.lower().startswith("merge "):
        failures.append("Daily task commits must not use merge-commit messages. Allow merge commits only for intentional release/hotfix boundaries.")

    if not HEADER_RE.match(header):
        failures.append("Header must match: type(scope): clear summary")

    if len(header) > 80:
        warnings.append("Header is over 80 characters; shorten it for readable Git history.")

    lowered = header.lower()
    if any(word in lowered for word in BAD_WORDS):
        warnings.append("Header looks vague; describe the behavior or risk instead of the editing process.")

    if not CJK_RE.search(header):
        warnings.append("Header has no Chinese characters. This is fine for English projects; Chinese teams usually prefer a Chinese summary.")

    if len(lines) > 1 and lines[1].strip():
        failures.append("Header and body must be separated by a blank line.")

    body_lines = [line for line in lines[2:] if line.strip()]
    if body_lines and not all(line.startswith("- ") for line in body_lines):
        warnings.append("Body lines should normally start with '- '.")

    for failure in failures:
        print(f"[fail] {failure}")
    for warning in warnings:
        print(f"[warn] {warning}")

    if failures:
        return 1

    print("[ok] Commit message matches the team Git workflow baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
