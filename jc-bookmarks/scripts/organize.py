#!/usr/bin/env python3
"""收藏夹结构整理：顶层换名 → 条目搬迁 → 改名 → 重新排序。

以一份已经转换好的 `bookmarks.json` 为基线做**增量修改**，不是每次从原始 HTML 重跑。
这样反复调整结构时，前面的分类、去重、清死链成果不会丢。

四张配置表决定一切，按自己的库改完再跑：

    TOP_ORDER   顶层顺序（同时决定哪些名字算顶层）
    TOP_RENAME  顶层改名，旧名 → 新名
    MOVES       条目搬迁，(url 片段, 目标路径)；前缀 = 精确匹配，单元素目标 = 平铺
    RENAMES     条目改名，旧名 → 新名

下面的 BRANDS / THEMES / DESIGN_TYPES 是排序用的分组表，同样按需调整。
脚本可以反复跑（幂等），搬过的条目不会二次搬动。
"""
import json
from urllib.parse import urlsplit

from pypinyin import lazy_pinyin

SRC = "bookmarks.json"

# ---------------------------------------------------------------- 结构
# ── 配置区（示例：一个前端/产品背景的收藏夹）────────────────────
TOP_ORDER = ["AI", "代理与账号", "橙子 CV", "工作",
             "开发", "文档资料", "日常工具"]

TOP_RENAME = {
    "开发与工具": "开发",
    "内容与资料": "文档资料",
    "生活": "日常工具",
    "生活杂项": "日常工具",
}

SUB_ORDER = {
    "AI": ["官方", "工具", "中转与 API", "代充"],
    "代理与账号": ["机场", "账号与充值"],
    "橙子 CV": ["竞品与市场", "产品与运营"],
    "工作": ["内部系统", "幼儿项目", "数据与爬取"],
    "开发": ["前端美学", "云与建站", "开源仓库", "学习面试"],
    "文档资料": ["创作工具", "资讯与社区"],
}

# ---------------------------------------------------------------- 搬迁
# (url 片段, 目标路径)；前缀 = 表示精确匹配，单元素目标 = 直接平铺在顶层下
MOVES = [
    ("=https://www.bilibili.com/", ["文档资料", "资讯与社区"]),
    ("bilibili.com/video", ["文档资料"]),
    ("youtube.com", ["文档资料", "资讯与社区"]),
    ("cupfox.love", ["文档资料", "资讯与社区"]),
    ("kookapp.cn", ["文档资料", "资讯与社区"]),
    ("fabiaoqing.com", ["文档资料", "资讯与社区"]),
    ("3daimtrainer.com", ["文档资料", "资讯与社区"]),
    ("lifekline.cn", ["文档资料", "资讯与社区"]),
    ("yuque.com/awescnb", ["开发", "云与建站"]),
    ("upwork.com", ["橙子 CV", "竞品与市场"]),
    ("linkedin.com", ["橙子 CV", "竞品与市场"]),
]

RENAMES = {
    "B站 - Autogen 自动发小红书": "自媒体 · Autogen 自动发小红书",
    "B站 - Coze 采集小红书教程": "YouTube - Coze 采集小红书教程",   # 之前误标成 B 站
}

# ---------------------------------------------------------------- 排序
# 厂商分组表：顺序 = 显示顺序，按使用权重排，不按字母排
BRANDS = [
    ("自有", ["chengzicv.com"]),
    ("字节", ["feishu.cn", "larksuite.com", "volcengine.com", "doubao.com", "coze.com",
             "coze.cn", "jimeng", "capcut.com", "oceanengine.com", "bytedance.com", "douyin.com"]),
    ("腾讯", ["qq.com", "weixin.qq.com", "weixin.com", "tencent.com", "tencent.cn", "tapd.cn"]),
    ("阿里", ["aliyun.com", "alipay.com", "taobao.com", "tmall.com", "1688.com", "dingtalk.com",
             "qianwen.com", "tongyi", "dashscope", "modelscope.cn", "alibaba.com"]),
    ("百度", ["baidu.com", "baidupcs.com"]),
    ("智谱", ["z.ai", "bigmodel.cn", "zhipu"]),
    ("月之暗面", ["moonshot.cn", "kimi.com"]),
    ("DeepSeek", ["deepseek.com"]),
    ("硅基流动", ["siliconflow.cn"]),
    ("秘塔", ["metaso.cn"]),
    ("MiniMax", ["minimax.io", "hailuoai.com"]),
    ("360", ["n.cn", "360.com"]),
    ("OpenAI", ["openai.com", "chatgpt.com"]),
    ("Anthropic", ["anthropic.com", "claude.ai"]),
    ("Google", ["google.com", "gemini.google", "notebooklm.google"]),
    ("xAI", ["x.ai", "grok.com"]),
    ("Perplexity", ["perplexity.ai"]),
    ("开源社区", ["github.com", "gitee.com", "gitlab", "huggingface.co", "npmjs.com"]),
    ("技术社区", ["csdn.net", "cnblogs.com", "juejin.cn", "stackoverflow.com", "linux.do",
              "v2ex.com", "segmentfault.com", "oschina.net", "zhihu.com"]),
    ("内容平台", ["xiaohongshu.com", "bilibili.com", "youtube.com", "weibo.com", "x.com",
              "kuaishou.com", "douyin.com"]),
    ("求职招聘", ["zhipin.com", "nowcoder.com", "mokahr.com", "zhiyeapp.com", "liepin.com",
              "51job.com", "shixiseng.com"]),
    ("语雀文档", ["yuque.com"]),
    ("金山办公", ["wps.cn", "kdocs.cn"]),
]

# 资料区主题顺序：改这里就等于改平铺资料的分组顺序
THEMES = ["产品经理", "运营", "求职", "自媒体", "AI", "论文",
          "Web3", "管理", "阅读", "健康", "理财", "成长", "工具"]

DESIGN_TYPES = ["组件", "模板", "图标", "配色", "动效", "规范", "灵感", "官网"]


def py_key(s):
    return "".join(lazy_pinyin(s)).lower()


def brand_of(url):
    host = url.split("//")[-1].split("/")[0].split(":")[0].lower()
    if host.startswith("www."):
        host = host[4:]
    for i, (_, keys) in enumerate(BRANDS):
        for k in keys:
            if host == k or host.endswith("." + k):
                return i
    return 999


def sort_key(node):
    n = node.get("name", "")
    if " · " in n:
        prefix = n.split(" · ", 1)[0]
        if prefix in THEMES:
            return (THEMES.index(prefix), 0, py_key(n))
        if prefix in DESIGN_TYPES:
            return (100 + DESIGN_TYPES.index(prefix), 0, py_key(n))
    return (900 + brand_of(node.get("url", "")), "", py_key(n))


# ---------------------------------------------------------------- 执行
def walk(node, parent=None):
    yield node, parent
    for c in node.get("children", []):
        yield from walk(c, node)


def find_top(root, name):
    for c in root["children"]:
        if c["type"] == "folder" and c["name"] == name:
            return c
    raise KeyError(name)


def main():
    data = json.load(open(SRC))
    root = data["roots"]["bookmark_bar"]

    # 1) 顶层换名
    for c in root["children"]:
        c["name"] = TOP_RENAME.get(c["name"], c["name"])

    # 2) 搬迁
    moved = []
    for frag, target in MOVES:
        exact = frag.startswith("=")
        needle = frag[1:] if exact else frag
        for node, parent in list(walk(root)):
            if node.get("type") != "url" or parent is None:
                continue
            url = node["url"]
            hit = (url.rstrip("/") == needle.rstrip("/")) if exact else (needle in url)
            if not hit:
                continue
            dest = find_top(root, target[0])
            if len(target) > 1:
                dest = next(c for c in dest["children"]
                            if c["type"] == "folder" and c["name"] == target[1])
            if parent is dest:
                continue
            parent["children"].remove(node)
            dest["children"].append(node)
            moved.append((node["name"], " > ".join(target)))

    # 3) 改名
    renamed = []
    for node, _ in walk(root):
        if node.get("type") != "url":
            continue
        new = RENAMES.get(node["name"])
        if new:
            renamed.append((node["name"], new))
            node["name"] = new

    # 4) 重排：顶层顺序、子夹顺序、夹内文件夹在前 + 网址按 key
    root["children"].sort(key=lambda c: TOP_ORDER.index(c["name"])
                          if c["name"] in TOP_ORDER else 99)
    for top in root["children"]:
        subs = [c for c in top["children"] if c["type"] == "folder"]
        urls = [c for c in top["children"] if c["type"] == "url"]
        order = SUB_ORDER.get(top["name"], [])
        subs.sort(key=lambda c: order.index(c["name"]) if c["name"] in order else 99)
        for s in subs:
            s["children"].sort(key=sort_key)
        urls.sort(key=sort_key)
        top["children"] = subs + urls

    json.dump(data, open(SRC, "w"), ensure_ascii=False, indent=2)

    total = sum(1 for n, _ in walk(root) if n.get("type") == "url")
    print(f"条目 {total}")
    print(f"搬迁 {len(moved)} 条：")
    for n, t in moved:
        print(f"   {n[:40]} → {t}")
    print(f"改名 {len(renamed)} 条：")
    for a, b in renamed:
        print(f"   {a[:40]} → {b}")
    print("\n结构：")
    for top in root["children"]:
        subs = [c for c in top["children"] if c["type"] == "folder"]
        flat = len([c for c in top["children"] if c["type"] == "url"])
        detail = " / ".join(f"{s['name']}{len(s['children'])}" for s in subs)
        tail = f" + 平铺 {flat}" if flat else ""
        print(f"  {top['name']:8s} {detail}{tail}")


if __name__ == "__main__":
    main()
