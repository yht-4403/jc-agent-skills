#!/usr/bin/env python3
"""Netscape 书签 HTML → Chromium Bookmarks JSON。

浏览器「导出书签」得到的是 Netscape HTML，层级靠 <DL>/<H3> 嵌套表达；
Chromium 的 Bookmarks 是 JSON，两者不能直接互换。本脚本保留完整层级，
书签栏映射到 roots.bookmark_bar，游离在顶层的网址并入 roots.other。

用法：
    python netscape2chromium.py bookmarks.html bookmarks.json
"""
import json
import os
import sys
import uuid
from html.parser import HTMLParser


class NetscapeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {"type": "folder", "name": "", "children": [], "date_added": "0"}
        self.stack = [self.root]
        self.pending = None          # 待建文件夹的 (name, attrs)
        self.in_h3 = False
        self.h3_text = []
        self.h3_attrs = {}
        self.in_a = False
        self.a_text = []
        self.a_attrs = {}

    @property
    def cur(self):
        return self.stack[-1]

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "dl":
            if self.pending:
                name, at = self.pending
                node = {
                    "type": "folder",
                    "name": name,
                    "children": [],
                    "date_added": at.get("add_date", "0"),
                    "date_modified": at.get("last_modified", "0"),
                    "guid": str(uuid.uuid4()),
                    "id": str(uuid.uuid4().int % 10**15),
                }
                if at.get("personal_toolbar_folder") == "true":
                    node["_toolbar"] = True
                self.cur["children"].append(node)
                self.stack.append(node)
                self.pending = None
            else:
                self.stack.append(self.cur)
        elif tag == "h3":
            self.in_h3 = True
            self.h3_text = []
            self.h3_attrs = a
        elif tag == "a":
            self.in_a = True
            self.a_text = []
            self.a_attrs = a

    def handle_endtag(self, tag):
        if tag == "dl":
            if len(self.stack) > 1:
                self.stack.pop()
        elif tag == "h3":
            self.in_h3 = False
            self.pending = ("".join(self.h3_text).strip(), self.h3_attrs)
        elif tag == "a":
            self.in_a = False
            href = self.a_attrs.get("href")
            if href:
                self.cur["children"].append({
                    "type": "url",
                    "name": "".join(self.a_text).strip() or href,
                    "url": href,
                    "date_added": self.a_attrs.get("add_date", "0"),
                    "guid": str(uuid.uuid4()),
                    "id": str(uuid.uuid4().int % 10**15),
                })

    def handle_data(self, data):
        if self.in_h3:
            self.h3_text.append(data)
        elif self.in_a:
            self.a_text.append(data)


def convert(html_path, out_path):
    raw = open(html_path, encoding="utf-8", errors="replace").read()
    p = NetscapeParser()
    p.feed(raw)
    p.close()

    top = p.root["children"]
    toolbar = next((n for n in top if n.get("_toolbar")), None)
    if toolbar is None:
        toolbar = next((n for n in top if n["type"] == "folder"), None)
    rest = [n for n in top if n is not toolbar]

    def clean(n):
        n.pop("_toolbar", None)
        for c in n.get("children", []):
            clean(c)
        return n

    if toolbar is None:
        toolbar = {"type": "folder", "name": "书签栏", "children": [], "date_added": "0",
                   "date_modified": "0", "guid": str(uuid.uuid4()),
                   "id": str(uuid.uuid4().int % 10**15)}
    toolbar["name"] = "书签栏"

    other = {"type": "folder", "name": "其他书签", "children": rest,
             "date_added": "0", "date_modified": "0",
             "guid": str(uuid.uuid4()), "id": str(uuid.uuid4().int % 10**15)}

    data = {
        "checksum": "",
        "roots": {
            "bookmark_bar": clean(toolbar),
            "other": clean(other),
            "synced": {"type": "folder", "name": "移动设备书签", "children": [],
                       "date_added": "0", "date_modified": "0",
                       "guid": str(uuid.uuid4()), "id": str(uuid.uuid4().int % 10**15)},
        },
        "version": 1,
    }
    json.dump(data, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def walk(n):
        urls, folders = 0, 0
        for c in n.get("children", []):
            if c["type"] == "url":
                urls += 1
            else:
                folders += 1
                u, f = walk(c)
                urls += u
                folders += f
        return urls, folders

    urls, folders = walk(data["roots"]["bookmark_bar"])
    print(f"转换完成：{urls} 条书签 / {folders} 个文件夹 → {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("用法：python netscape2chromium.py <bookmarks.html> [out.json]")
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(src)), "bookmarks.json")
    convert(src, dst)
