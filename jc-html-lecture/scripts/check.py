#!/usr/bin/env python3
"""check.py — 生成完页面后跑一遍，把「肉眼看不出来、打开才崩」的问题挡在前面。

用法：
  python3 check.py 页面.html              # 检查（允许 ./assets 引用）
  python3 check.py 页面.html --single     # 检查「单文件」形态：不允许残留外链资源
  python3 check.py 页面.html --quiet      # 只输出问题，通过时不打印

退出码 0 = 通过，1 = 有问题。
"""
import argparse
import html.parser
import os
import re
import sys

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class Balance(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        self.stack.append((tag, self.getpos()))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append("多余的 </%s>（第 %d 行）" % (tag, self.getpos()[0]))
            return
        if self.stack[-1][0] != tag:
            open_tag, pos = self.stack[-1]
            self.errors.append(
                "</%s> 与未闭合的 <%s>（第 %d 行开的）不匹配，位置第 %d 行"
                % (tag, open_tag, pos[0], self.getpos()[0])
            )
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break
        else:
            self.stack.pop()


def strip_embedded(s):
    """把 <script>/<style> 的内容清空，只留标签与正文。
    内联后的 JS 注释里可能写着 <script src=...>，不剥掉会误报。"""
    s = re.sub(r'(<script\b[^>]*>).*?(</script\s*>)', r'\1\2', s, flags=re.S | re.I)
    s = re.sub(r'(<style\b[^>]*>).*?(</style\s*>)', r'\1\2', s, flags=re.S | re.I)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--single", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    p = os.path.abspath(args.html)
    if not os.path.exists(p):
        sys.exit("找不到文件：%s" % p)
    s = open(p, encoding="utf-8").read()
    base = os.path.dirname(p)
    problems, notes = [], []
    plain = strip_embedded(s)

    # 1 结构
    b = Balance()
    b.feed(s)
    for t, pos in b.stack:
        problems.append("<%s> 没有闭合（第 %d 行）" % (t, pos[0]))
    problems.extend(b.errors[:8])

    # 2 标注接入
    has_css = bool(re.search(r'href="[^"]*jc-note\.css"', plain)) or ("jcn-drawer" in s)
    has_js = "data-jc-note" in plain
    if not (has_css and has_js):
        problems.append("缺少标注运行时：需要 jc-note.css 和带 data-jc-note 的 script")
    m = re.search(r'data-doc-id\s*=\s*"([^"]*)"', plain)
    if m:
        if not m.group(1).strip():
            problems.append("data-doc-id 是空的")
    elif has_js:
        problems.append("data-jc-note 的 script 上没有 data-doc-id（标记会存在 pathname 下）")

    # 3 外链资源（在剥离脚本内容的版本上查，避免把注释里的示例当引用）
    refs = re.findall(r'(?:href|src)\s*=\s*"([^"]+\.(?:css|js))"', plain, re.I)
    local = [r for r in refs if not r.startswith(("http", "//", "data:"))]
    for r in local:
        target = os.path.normpath(os.path.join(base, r.split("?")[0]))
        if not os.path.exists(target):
            problems.append("引用了不存在的文件：%s" % r)
    if args.single and local:
        problems.append("单文件形态下仍有外链资源：%s（跑 inline.py）" % ", ".join(local))

    # 4 已知会翻车的写法
    # text/plain 代码块是 jc-code.js 的数据源，没引它就不会渲染
    has_plain_code = bool(re.search(r'<script[^>]*type\s*=\s*"text/plain"', plain, re.I))
    # 老页面可能自带一段渲染脚本（选择器 script.src），一样能跑，不必强行迁移
    has_renderer = ("jc-code.js" in plain) or ("script.src" in s)
    if not args.single and has_plain_code and not has_renderer:
        problems.append("用了 text/plain 代码块，但没有渲染器（引 jc-code.js 或自带 script.src 选择器），代码不会显示")
    if re.search(r"@keyframes[^{]*\{[^}]*opacity\s*:\s*0[^}]*\}", plain, re.I):
        notes.append("有从 opacity:0 开始的动画；浮层用它会在低帧率环境停在透明帧")
    inline_styles = len(re.findall(r'\sstyle\s*=\s*"', plain))
    if inline_styles > 40:
        notes.append("内联 style 有 %d 处，考虑收进类，便于统一改" % inline_styles)

    # 5 规模
    kb = len(s.encode()) / 1024
    sections = len(re.findall(r'<section class="chapter"', plain))
    if kb > 90:
        notes.append("页面 %.0f KB、%d 节，建议把靠后的章节拆成附录页" % (kb, sections))

    if not args.quiet:
        print("文件：%s" % os.path.basename(p))
        print("体积：%.1f KB　节数：%d　标注：%s" % (
            kb, sections, "已接入" if (has_css and has_js) else "未接入"))

    if problems:
        print("\n必须修：")
        for x in problems:
            print("  ✗ " + x)
    if notes:
        print("\n建议看：")
        for x in notes:
            print("  · " + x)
    if not problems and not notes and not args.quiet:
        print("\n通过。")
    elif not problems and not args.quiet:
        print("\n没有阻塞问题。")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
