#!/usr/bin/env python3
"""inline.py — 把页面里对 ./assets/ 的引用换成内联，产出可直接分享的单文件 HTML。

为什么需要它：
  页面生成时用 <link>/<script src> 引用，省掉每次重复写 36KB 资产代码；
  交付时跑一次这个脚本，文件就变成自包含，单独发给别人、换个目录、双击打开都不会丢功能。

用法：
  python3 inline.py 页面.html                 # 产出 页面-单文件.html
  python3 inline.py 页面.html -o 交付.html
  python3 inline.py 页面.html --dry-run       # 只报告，不写文件

保留的：<script> 上的 data-* 属性（jc-note 靠 data-jc-note 认领自己）。
不处理的：外链 http(s)、data: URI、<img> 图片（只报警告，避免把页面撑成几 MB）。
"""
import argparse
import os
import re
import sys

LINK_RE = re.compile(r'<link\b[^>]*\bhref\s*=\s*"([^"]+\.css)"[^>]*>', re.I)
SCRIPT_RE = re.compile(r'<script\b([^>]*)\bsrc\s*=\s*"([^"]+\.js)"([^>]*)>\s*</script>', re.I)
IMG_RE = re.compile(r'<(?:img|image|use|source)\b[^>]*\b(?:src|href)\s*=\s*"([^"]+)"', re.I)
CSS_URL_RE = re.compile(r'url\(\s*[\'"]?(?!data:|https?:|//)([^\'")]+)', re.I)


def is_remote(u):
    return u.startswith(("http://", "https://", "//", "data:", "blob:"))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def resolve(base, href):
    clean = href.split("?")[0].split("#")[0]
    return os.path.normpath(os.path.join(base, clean))


def merge_attrs(a, b):
    """把两段属性字符串拼起来，去掉多余空格。"""
    return (a + " " + b).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("-o", "--out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-source", action="store_true", help="内联后保留一行注释标明来源")
    args = ap.parse_args()

    src_path = os.path.abspath(args.html)
    if not os.path.exists(src_path):
        sys.exit("找不到文件：%s" % src_path)
    base = os.path.dirname(src_path)
    html = read(src_path)

    done, missing, warns = [], [], []

    def css_sub(m):
        href = m.group(1)
        if is_remote(href):
            return m.group(0)
        p = resolve(base, href)
        if not os.path.exists(p):
            missing.append(href)
            return m.group(0)
        css = read(p)
        if "</style" in css.lower():
            warns.append("%s 里含 </style>，内联会截断样式表，需先改掉" % href)
        for u in CSS_URL_RE.findall(css):
            warns.append("CSS 里还有相对资源 %s，需手动内联或改绝对路径" % u)
        note = "\n/* inlined: %s */" % href if args.keep_source else ""
        done.append((href, len(css), "css"))
        return "<style>%s\n%s\n</style>" % (note, css.rstrip())

    def js_sub(m):
        pre, src, post = m.group(1), m.group(2), m.group(3)
        if is_remote(src):
            return m.group(0)
        p = resolve(base, src)
        if not os.path.exists(p):
            missing.append(src)
            return m.group(0)
        js = read(p)
        # 关键：注释或字符串里只要出现 </script，内联后浏览器会在那里截断脚本，
        # 后面的代码变成正文，整页崩。JS 里 <\/script 与 </script 等价。
        js = js.replace("</script", "<\\/script")
        attrs = merge_attrs(pre, post)
        done.append((src, len(js), "js"))
        return "<script%s>\n%s\n</script>" % ((" " + attrs) if attrs else "", js.rstrip())

    html = LINK_RE.sub(css_sub, html)
    html = SCRIPT_RE.sub(js_sub, html)

    # 残留图片资源：不自动内联，提示用户
    for u in IMG_RE.findall(html):
        if not is_remote(u) and not u.startswith("#"):
            if os.path.exists(resolve(base, u)):
                warns.append("<img> 仍引用本地文件 %s（未内联，文件会变大）" % u)
            else:
                missing.append(u)

    if args.out:
        out_path = os.path.abspath(args.out)
    else:
        stem, ext = os.path.splitext(src_path)
        out_path = stem + "-单文件" + (ext or ".html")

    print("内联清单：")
    if not done:
        print("  （没有找到 ./assets/ 引用，页面可能已经是单文件）")
    for href, size, kind in done:
        print("  %-34s %7.1f KB  %s" % (href, size / 1024, kind))
    if missing:
        print("\n找不到的资源：")
        for u in dict.fromkeys(missing):
            print("  ! " + u)
    if warns:
        print("\n注意：")
        for w in dict.fromkeys(warns):
            print("  · " + w)

    before, after = len(read(src_path).encode()), len(html.encode())
    print("\n体积：%.1f KB → %.1f KB" % (before / 1024, after / 1024))

    if args.dry_run:
        print("（dry-run，未写文件）")
        return 0 if not missing else 1

    if not done:
        print("没有可内联的内容，未写文件。")
        return 0

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("已写出：%s" % out_path)
    print("验证：双击打开，看右下角「标注」按钮是否在、选中文字能否标记。")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
