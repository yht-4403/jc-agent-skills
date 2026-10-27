#!/usr/bin/env python3
"""处理「待整理」收件箱：给每条新书签提出目标路径，产出一份确认清单。

日常维护跟首次整理是两件事：
    首次整理 = 561 条重排，走 organize.py + merge_back.py 全量写回
    日常维护 = 几条到几十条，只需回答「这条该去哪」

所以这个脚本**不搬动、不改名**，只输出清单：
目标路径由 ROUTES 规则表判定，命名留给人或模型（那是判断活，不适合自动化）。

用法：
    python triage.py                          # 读 bookmarks.json
    python triage.py --chrome                 # 直接读浏览器里的 Bookmarks
    python triage.py --out 待整理清单.md
    python triage.py --apply                  # 确认后搬动（会改写 --src 指向的 json）

少于 20 条时，最省事的路径是照清单在浏览器里手动拖，别走全库导出导入
——全库导入是追加语义，很容易变成两套。
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import urlsplit

# AI 相关词：用词边界，避免 detail / mail 这类误命中
AI_RE = re.compile(
    r"\bai\b|\bai[-· ]|智能体|\bagent\b|大模型|\bllm\b|prompt|aigc|"
    r"chatgpt|claude|gemini|grok|openai|midjourney|comfyui|stable diffusion")

# ---------------------------------------------------------------- 规则
# 顺序即优先级，first match wins。先写特例，再写通用。
# 每项：(关键词元组, 目标路径, 为什么)
ROUTES = [
    # 代码仓库：铁律，一律进开源仓库
    (("github.com", "gitee.com", "gitlab.com"), ["开发", "开源仓库"], "代码仓库"),
    # 代理与账号
    (("机场", "订阅", "v2ray", "clash", "ssr", "trojan", "节点", "加速器",
      "住宅ip", "住宅 ip", "ip代理", "ip 代理", "proxy"), ["代理与账号", "机场"], "代理/机场"),
    (("接码", "sms", "虚拟卡", "vcc", "发卡", "卡密", "账号商城", "成品号",
      "apple id", "esim", "giffgaff"), ["代理与账号", "账号与充值"], "账号/卡/接码"),
    # 求职与简历（项目相关）
    (("简历", "面试", "招聘", "offer", "ats", "求职", "秋招", "校招", "内推"),
     ["橙子 CV", "竞品与市场"], "简历/面试产品"),
    (("部署", "运维", "备案", "域名", "服务器", "cdn", "dns"), ["橙子 CV", "产品与运营"], "自家产品运维"),
    # 前端美学
    (("组件", "图标", "icon", "配色", "字体", "动效", "animation", "design system",
      "设计规范", "ui kit", "模板", "template", "theme"), ["开发", "前端美学"], "设计资源"),
    # 开发与工具
    (("云服务", "控制台", "console", "server", "hosting", "wordpress", "建站", "seo"),
     ["开发", "云与建站"], "云服务/建站"),
    (("教程", "文档", "docs", "guide", "面试题", "八股", "课程", "learn"),
     ["开发", "学习面试"], "学习资料"),
    # 文档资料
    (("feishu.cn", "larksuite", "yuque.com", "notion.so", "docs.qq.com",
      "doc.weixin.qq.com", "mp.weixin.qq.com"), ["文档资料"], "文档（平铺，加主题前缀）"),
    (("资讯", "社区", "博客", "blog", "news", "论坛", "bilibili.com", "youtube.com",
      "xiaohongshu", "zhihu.com"), ["文档资料", "资讯与社区"], "资讯/社区"),
]

# 判断「官方」用的厂商域名，与 organize.py 保持一致
OFFICIAL_HOSTS = [
    "openai.com", "chatgpt.com", "anthropic.com", "claude.ai", "gemini.google.com",
    "notebooklm.google.com", "grok.com", "deepseek.com", "moonshot.cn", "kimi.com",
    "qianwen.com", "aliyun.com", "volcengine.com", "doubao.com", "yuanbao.tencent.com",
    "ima.qq.com", "z.ai", "bigmodel.cn", "siliconflow.cn", "metaso.cn", "bot.n.cn",
    "huggingface.co", "modelscope.cn", "perplexity.ai", "minimax.io", "hailuoai.com",
]

INBOX_DEFAULT = "待整理"


def host_of(url):
    h = urlsplit(url).netloc.lower().split(":")[0]
    return h[4:] if h.startswith("www.") else h


def is_official(url):
    h = host_of(url)
    return any(h == o or h.endswith("." + o) for o in OFFICIAL_HOSTS)


def route(item):
    """返回 (目标路径, 理由)；判不出来返回 (None, None)。"""
    url = item.get("url", "")
    text = (item.get("name", "") + " " + url).lower()

    # 厂商自己的域名 → 官方，优先于关键词（否则 openai.com 的 API 文档会被判成「中转」）
    if is_official(url):
        return ["AI", "官方"], "厂商自有域名"

    # 代充按「卖的是不是 AI 服务」二分：这条边界比「站点叫什么」稳定
    if any(k in text for k in ("代充", "充值", "账号商城", "成品号", "会员")):
        if AI_RE.search(text):
            return ["AI", "代充"], "卖 AI 服务账号"
        return ["代理与账号", "账号与充值"], "卖通用账号/卡"

    for keys, target, why in ROUTES:
        if any(k in text for k in keys):
            return list(target), why

    # AI 兜底：前面对不上具体用途，但又明显是 AI 产品 → 当工具放
    if AI_RE.search(text):
        return ["AI", "工具"], "AI 产品/服务"
    return None, None


def find_inbox(node, name):
    if node.get("type") == "folder" and node.get("name") == name:
        return node
    for c in node.get("children", []):
        if c.get("type") == "folder":
            hit = find_inbox(c, name)
            if hit:
                return hit
    return None


def walk_collect(node, path=""):
    """收集所有 (父节点, 节点, 路径)。"""
    out = []
    for c in node.get("children", []):
        if c.get("type") == "folder":
            out.append((node, c, path))
            out += walk_collect(c, path + " > " + c["name"] if path else c["name"])
        else:
            out.append((node, c, path))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="bookmarks.json")
    ap.add_argument("--chrome", action="store_true", help="直接读浏览器 Bookmarks")
    ap.add_argument("--inbox", default=INBOX_DEFAULT)
    ap.add_argument("--out", default=None, help="清单输出路径")
    ap.add_argument("--apply", action="store_true", help="按判定结果搬动")
    args = ap.parse_args()

    if args.chrome:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from merge_back import default_bookmarks_path
        src = default_bookmarks_path()
        data = json.load(open(src))
    else:
        src = args.src
        data = json.load(open(src))

    root = data["roots"]["bookmark_bar"]
    inbox = find_inbox(root, args.inbox)
    if not inbox:
        print(f"没找到「{args.inbox}」文件夹，先检查名字（--inbox 可指定）。")
        return

    items = [c for c in inbox.get("children", []) if c.get("type") == "url"]
    if not items:
        print(f"「{args.inbox}」是空的，没有待处理项。")
        return

    ok, unknown = [], []
    for it in items:
        target, why = route(it)
        (ok if target else unknown).append((it, target, why))

    lines = [f"# {args.inbox} 处理清单\n",
             f"共 {len(items)} 条：可判定 {len(ok)}，需人工判断 {len(unknown)}\n",
             "## 可判定\n",
             "| # | 当前标题 | 目标 | 依据 |", "|---|---|---|---|"]
    for i, (it, target, why) in enumerate(ok, 1):
        lines.append(f"| {i} | {it['name'][:44]} | {' > '.join(target)} | {why} |")

    if unknown:
        lines += ["\n## 需人工判断\n", "| # | 当前标题 | URL |", "|---|---|---|"]
        for i, (it, _, _) in enumerate(unknown, 1):
            lines.append(f"| {i} | {it['name'][:44]} | {it.get('url','')[:60]} |")

    if len(items) <= 20:
        lines.append("\n> 20 条以内，建议照此表在浏览器书签管理器里手动拖动，"
                     "比全库导出导入更安全。")
    else:
        lines.append("\n> 超过 20 条，可以 `--apply` 批量搬动，再走 merge_back 写回。")

    text = "\n".join(lines) + "\n"
    out = args.out or f"{args.inbox}清单.md"
    open(out, "w").write(text)
    print(text)
    print(f"清单已写到 {out}")

    if not args.apply:
        return

    # 直接改浏览器文件时，必须先退出 Chrome，否则内存里的旧数据会覆盖回来
    if args.chrome:
        from merge_back import chrome_running
        if chrome_running():
            print("\n⚠️ Chrome 还在运行，写进去会被它覆盖。先完全退出（⌘Q），"
                  "或者去掉 --chrome 改用 --src 操作副本。")
            return
        import shutil, time
        bak = src + ".triage-" + time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(src, bak)
        print(f"\n已备份 {os.path.basename(bak)}")

    moved = 0
    for it, target, _ in ok:
        dest = next((c for c in root["children"] if c["name"] == target[0]), None)
        if not dest:
            print(f"跳过（找不到顶层 {target[0]}）: {it['name'][:30]}")
            continue
        if len(target) > 1:
            dest = next((c for c in dest["children"]
                         if c.get("type") == "folder" and c["name"] == target[1]), None)
            if not dest:
                print(f"跳过（找不到子夹 {target}）: {it['name'][:30]}")
                continue
        inbox["children"].remove(it)
        dest["children"].append(it)
        moved += 1

    if args.chrome:
        data["checksum"] = ""      # 浏览器会自己重算，留着旧值反而校验失败
    json.dump(data, open(src, "w"), ensure_ascii=False, indent=3)
    print(f"\n已搬动 {moved} 条，写回 {src}（剩下的留在「{args.inbox}」）")
    if args.chrome:
        print("启动 Chrome 确认结果；条目数变多说明同步把云端旧数据合并回来了。")


if __name__ == "__main__":
    main()
