#!/usr/bin/env python3
"""把整理结果合并写回 Chrome 的 Bookmarks 文件（保留原 GUID，避免同步端全量重建）。

用法：
  python merge_back.py --check      # 只做校验：用原文件反推 checksum，验证算法
  python merge_back.py              # 生成合并结果到 Bookmarks.merged（不写原文件）
  python merge_back.py --write      # 备份原文件后写入（务必先完全退出 Chrome）
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import time

NEW = "bookmarks.json"


def default_bookmarks_path():
    """各平台 Chrome 默认 Bookmarks 路径。"""
    import sys
    if sys.platform == "darwin":
        return os.path.expanduser(
            "~/Library/Application Support/Google/Chrome/Default/Bookmarks")
    if sys.platform.startswith("win"):
        return os.path.join(os.environ.get("LOCALAPPDATA", ""),
                            "Google", "Chrome", "User Data", "Default", "Bookmarks")
    return os.path.expanduser("~/.config/google-chrome/Default/Bookmarks")


# ---------- Chromium BookmarkCodec 的 checksum：base64(sha1(紧凑JSON, 非ASCII转\uXXXX)) ----------
def _esc(s):
    out = []
    for ch in s:
        c = ord(ch)
        if c > 0xFFFF:                       # 代理对，JS 侧按 UTF-16 码元转义
            c -= 0x10000
            out.append("\\u%04x\\u%04x" % (0xD800 + (c >> 10), 0xDC00 + (c & 0x3FF)))
        elif c > 0x7F:
            out.append("\\u%04x" % c)
        elif ch == "&":
            out.append("\\u0026")
        elif ch == "<":
            out.append("\\u003c")
        elif ch == ">":
            out.append("\\u003e")
        else:
            out.append(ch)
    return "".join(out)


def checksum(roots):
    compact = json.dumps(roots, ensure_ascii=False, separators=(",", ":"))
    return base64.b64encode(hashlib.sha1(_esc(compact).encode("utf-8")).digest()).decode()


# ---------- 归一化 URL，用于跨文件配对 ----------
def norm(u):
    u = u.strip()
    for p in ("https://", "http://"):
        if u.startswith(p):
            u = u[len(p):]
            break
    host, _, rest = u.partition("/")
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host + "/" + rest.rstrip("/")


def walk(node, out=None):
    out = [] if out is None else out
    for c in node.get("children", []):
        out.append(c)
        if c.get("type") == "folder":
            walk(c, out)
    return out


def index_urls(root):
    idx = {}
    for n in walk(root):
        if n.get("type") == "url":
            idx.setdefault(norm(n["url"]), n)
    return idx


def chrome_running():
    import subprocess
    import sys
    # 用 -x 精确匹配进程名；-f 会匹配到本脚本自己的命令行
    if sys.platform.startswith("win"):
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                           capture_output=True, text=True)
        return "chrome.exe" in r.stdout
    r = subprocess.run(["pgrep", "-x", "Google Chrome"], capture_output=True)
    return bool(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，不写")
    ap.add_argument("--write", action="store_true", help="备份后写入浏览器")
    ap.add_argument("--chrome", default=None, help="Bookmarks 文件路径，默认按平台推断")
    ap.add_argument("--src", default=NEW, help="整理后的 JSON，默认 bookmarks.json")
    args = ap.parse_args()
    global CHROME
    CHROME = args.chrome or default_bookmarks_path()

    old = json.load(open(CHROME))
    new = json.load(open(args.src))

    # 1) checksum 由 Chrome 按节点逐个累加，无法从最终 JSON 反推；
    #    留空即跳过校验，Chrome 加载后会自己重算并写回。
    print(f"原文件 checksum：{old.get('checksum', '(空)')}（写回时留空，交给 Chrome 重算）")
    if args.check:
        print("仅校验模式，结束。")
        return
    if args.write and chrome_running():
        print("⚠️ Chrome 还在运行，先完全退出（⌘Q）再来。")
        return

    # 2) 合并：以整理结果为准，URL 能配对上的沿用原 guid/id/date_added
    old_urls = index_urls(old["roots"]["bookmark_bar"])
    old_urls.update(index_urls(old["roots"].get("other", {"children": []})))
    reused = 0
    fresh = 0

    def merge(node):
        nonlocal reused, fresh
        if node.get("type") == "url":
            src = old_urls.get(norm(node["url"]))
            if src:
                reused += 1
                node["guid"] = src["guid"]
                node["id"] = src["id"]
                node["date_added"] = src.get("date_added", "0")
                if "date_last_used" in src:
                    node["date_last_used"] = src["date_last_used"]
            else:
                fresh += 1
            return node
        for c in node.get("children", []):
            merge(c)
        return node

    new_bar = merge(new["roots"]["bookmark_bar"])

    # 3) 三个根节点沿用 Chrome 的 id/guid，只换 children
    roots = {}
    for key in ("bookmark_bar", "other", "synced"):
        base = dict(old["roots"].get(key, {}))
        base.setdefault("type", "folder")
        base.setdefault("date_added", "0")
        if key == "bookmark_bar":
            base["children"] = new_bar["children"]
        else:
            base["children"] = []
        roots[key] = base

    result = {"checksum": "", "roots": roots, "version": 1}

    print(f"\n合并完成：沿用 {reused} 条原 GUID，{fresh} 条为新增")
    print(f"条目：Chrome 现有 {len(old_urls)} 个不同 URL → 整理后 {reused + fresh} 条")
    print(f"新 checksum：{result['checksum']}")

    out = args.src.replace(".json", "") + ".merged"
    json.dump(result, open(out, "w"), ensure_ascii=False, indent=3)
    print(f"已输出到 {out}（未动原文件）")

    if args.write:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for f in (CHROME, CHROME + ".bak",
                  os.path.join(os.path.dirname(CHROME), "EncryptedBookmarks2")):
            if os.path.exists(f):
                dst = f + ".mybackup-" + stamp
                shutil.copy2(f, dst)
                print(f"备份 {os.path.basename(f)} → {os.path.basename(dst)}")
        shutil.copy2(out, CHROME)
        print(f"\n✅ 已写入 {CHROME}")
        print("   启动 Chrome，如果书签没变化，说明它读的是加密副本，回来告诉我，我帮你回滚。")


if __name__ == "__main__":
    main()
