#!/usr/bin/env python3
"""Dump today's Grok user turns for empty-invoke harvest. No token handling."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SKIP_PREFIXES = ("<user_info>", "<system-reminder>", "<system_reminder>")
SECRET_RE = re.compile(
    r"(?i)(token|api[_-]?key|bearer|authorization)\s*[:=]\s*\S+"
)


def grok_home() -> Path:
    return Path(os.environ.get("GROK_HOME", Path.home() / ".grok")).expanduser()


def local_today(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name)).date()


def parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def flatten_user_text(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text") or "")
    return "\n".join(parts)


def clean_text(text: str) -> str:
    text = text.strip()
    if not text or text.startswith(SKIP_PREFIXES):
        return ""
    # drop trailing runtime_info / pull_request_linking blobs
    for marker in ("<runtime_info>", "<pull_request_linking>"):
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx].rstrip()
    text = SECRET_RE.sub(r"\1: [redacted]", text)
    return text.strip()


def iter_user_turns(chat_path: Path):
    if not chat_path.exists():
        return
    for line in chat_path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "user" or obj.get("synthetic_reason"):
            continue
        text = clean_text(flatten_user_text(obj.get("content")))
        if text:
            yield text


def harvest(days: int, tz_name: str, limit_sessions: int) -> list[dict]:
    start = datetime.combine(local_today(tz_name), datetime.min.time(), tzinfo=ZoneInfo(tz_name))
    if days > 1:
        start = start - timedelta(days=days - 1)
    root = grok_home() / "sessions"
    sessions = []
    if not root.exists():
        return []
    for summary in root.glob("**/summary.json"):
        try:
            info = json.loads(summary.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        ts = parse_ts(info.get("updated_at") or info.get("last_active_at") or "")
        if ts is None or ts < start:
            continue
        sessions.append((ts, summary.parent, info))
    sessions.sort(key=lambda x: x[0], reverse=True)
    out = []
    for ts, folder, info in sessions[:limit_sessions]:
        turns = list(iter_user_turns(folder / "chat_history.jsonl"))
        if not turns:
            continue
        out.append(
            {
                "id": folder.name,
                "title": info.get("generated_title") or "",
                "updated_at": info.get("updated_at"),
                "cwd": info.get("git_root_dir") or folder.parent.name,
                "user_turns": turns,
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--tz", default="Asia/Shanghai")
    parser.add_argument("--limit-sessions", type=int, default=30)
    args = parser.parse_args()
    payload = harvest(args.days, args.tz, args.limit_sessions)
    json.dump({"days": args.days, "sessions": payload}, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
