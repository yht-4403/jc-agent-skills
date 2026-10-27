#!/usr/bin/env python3
"""Upload Markji cards. Token from MAIMEMO_TOKEN, then Skill .env."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://open.maimemo.com/open"
SKILL_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = SKILL_ROOT / ".env"


def token_from_dotenv(name: str) -> str:
    if not ENV_PATH.is_file():
        return ""
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() != name:
            continue
        return value.strip().strip("'").strip('"')
    return ""


def resolve_token(env_name: str) -> str:
    return os.environ.get(env_name, "").strip() or token_from_dotenv(env_name)


def api(token: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw[:2000]}
        return exc.code, payload


def load_cards(path: str) -> list[dict]:
    obj = json.loads(open(path, encoding="utf-8").read())
    if isinstance(obj, dict) and "cards" in obj:
        obj = obj["cards"]
    if not isinstance(obj, list):
        raise SystemExit("JSON must be a list of {content} or {cards: [...]}")
    out = []
    for item in obj:
        if isinstance(item, str):
            out.append({"content": item})
        elif isinstance(item, dict) and item.get("content"):
            out.append({"content": item["content"]})
        else:
            raise SystemExit("each card needs content")
    return out


def find_deck(token: str, name: str) -> dict:
    code, payload = api(token, "GET", "/api/v1/markji/decks?limit=20&offset=0")
    if code == 403:
        raise SystemExit("403 记忆卡开放接口未开通，不要改走背单词")
    if code != 200 or not payload.get("success"):
        raise SystemExit(f"list decks failed {code} {payload.get('errors')}")
    decks = (payload.get("data") or {}).get("decks") or []
    matches = [d for d in decks if d.get("name") == name]
    if not matches:
        names = ", ".join(d.get("name") or "?" for d in decks) or "无"
        raise SystemExit(f"找不到牌组 {name!r}。现有：{names}")
    return matches[0]


def first_chapter(token: str, deck_id: str) -> str:
    code, payload = api(token, "GET", f"/api/v1/markji/decks/{deck_id}/chapters?with_cards=true")
    if code != 200 or not payload.get("success"):
        raise SystemExit(f"list chapters failed {code} {payload.get('errors')}")
    chapters = (payload.get("data") or {}).get("chapters") or []
    if not chapters:
        raise SystemExit("该牌组没有章节，请在 App 里先建一个章节")
    return chapters[0]["id"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck", default="英语")
    parser.add_argument("--file", required=True)
    parser.add_argument("--token-env", default="MAIMEMO_TOKEN")
    args = parser.parse_args()

    token = resolve_token(args.token_env)
    if not token:
        raise SystemExit(f"缺少 {args.token_env}：请设环境变量，或写入 {ENV_PATH}")

    cards = load_cards(args.file)
    deck = find_deck(token, args.deck)
    chapter_id = first_chapter(token, deck["id"])
    created = []
    for card in cards:
        body = {"card": {"content": card["content"], "grammar_version": 3}}
        path = f"/api/v1/markji/decks/{deck['id']}/chapters/{chapter_id}/cards"
        code, payload = api(token, "POST", path, body)
        if code not in (200, 201) or not payload.get("success", True):
            raise SystemExit(f"create failed {code} {payload.get('errors')}")
        info = (payload.get("data") or {}).get("card") or {}
        created.append(
            {
                "id": info.get("id"),
                "front": card["content"].split("\n---", 1)[0].strip(),
            }
        )
    json.dump(
        {"deck": deck.get("name"), "count": len(created), "cards": created},
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
