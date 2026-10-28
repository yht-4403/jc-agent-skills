# 移植到 Codex 及其他无渲染宿主

## 一句话结论

**语料 100% 可搬，渲染 0% 可搬。**

这套东西是两半：一半是纯文本规则（17.4KB 的 markdown），一半是宿主提供的渲染通道（`show_widget` 把 SVG/HTML 塞进对话流）。前者是资产，后者是基础设施。

| 组成 | 能否搬 | 原因 |
|---|---|---|
| 9 个模块的设计规则 | 完整搬走 | 纯字符串常量，零依赖 |
| 9 色系色值 | 完整搬走 | 硬编码 hex |
| CSS 变量 | 需适配 | 由宿主注入，脱离后不存在 |
| `show_widget` 内联渲染 | 搬不走 | Codex 无 widget 通道 |
| 流式渲染约束 | 直接失效 | Codex 不做增量 DOM diff |
| `sendPrompt()` | 必须删除 | WorkBuddy 专有 API |
| CSP 白名单 | 约束消失 | 那是宿主 WebView 的策略 |

## 三处必要适配

### 1. CSS 变量要兜底

原文大量使用 `var(--color-background-primary)` 这类变量，宿主注入。在 Codex 产出的独立 HTML 里，它们全是空值，颜色会塌成透明。

用 `assets/host-tokens.css` 顶上——它按原文语义定义了完整一套浅色/深色变量，外加 `.sr-only`。

### 2. 删掉 `sendPrompt()`

原文的节点模板长这样：

```html
<g class="node c-blue" onclick="sendPrompt('...')">
```

移植后 `sendPrompt` 不存在，点击会报错。要么整条 `onclick` 删掉，要么换成普通锚点或折叠交互。

### 3. 流式约束转成「首屏可用」原则

原文要求「`<script>` 放最后、`<style>` 控制在 15 行内、避免渐变幻影因为流式 diff 会闪」。Codex 里不流式，这些具体约束失效，但背后的意图仍然成立：**代码顺序要保证内容先出现、装饰后加载**。保留这个习惯，别保留理由。

## 落地方式

### 方案 A：AGENTS.md + references 目录（推荐）

```
your-repo/
├── AGENTS.md
└── .agents/
    └── visualizer/
        ├── 00-core.md
        ├── 01-palette.md
        ├── 02-svg-setup.md
        ├── 04-diagram.md
        ├── 06-chartjs.md
        └── host-tokens.css
```

`AGENTS.md` 里只放摘要和索引，别把 17KB 全塞进去（会吃掉大量上下文）：

```markdown
## 可视化规范

生成 SVG / HTML 图表前，先读 .agents/visualizer/00-core.md 与 01-palette.md。
画流程图或结构图时追加 02-svg-setup.md 与 04-diagram.md。
画数据图表时追加 06-chartjs.md。

硬约束（不可违反）：
- viewBox 固定 0 0 680 H，H = 最底部元素 + 20
- 边框 0.5px，圆角 12px
- 字重只有 400 / 500，字号不小于 11px
- 一张图最多 2 个色系，横向最多 4 个盒子
- 连线 path 必须 fill="none"
- 盒内 text 必须 dominant-baseline="central"
- 禁止渐变、投影、模糊、emoji
- 外层容器透明

产出方式：直接写 .html 文件到 output/，用浏览器打开查看。
```

### 方案 B：压成单文件系统提示

如果只有一次性的项目、不想建目录，取 `00-core` + `01-palette` + `02-svg-setup` 三份（约 6KB），合并成一个 `visualizer.md`，作为系统提示或项目说明的一部分。够用，但拿不到 chart / map / art 的细节。

### 方案 C：做成 MCP server

把 `VisualizerGuidelines.build(modules)` 原样重写成 MCP tool，返回同样拼接的 markdown。这样任何支持 MCP 的客户端都能按需取模块，上下文利用率最高。工作量约 100 行，但你得自己实现渲染端，否则拿到的还是「该怎么画」而不是图。

## 渲染通道的三个替代

Codex 没有内联渲染，只能落地成文件：

| 替代 | 做法 | 适合 | 代价 |
|---|---|---|---|
| 写 `.html` | 生成自包含单页，`open` 打开 | 交互图、多图页、需要精确排版 | 要手动开浏览器 |
| 写 `.svg` | 直接落 SVG 文件 | 单张静态图，可嵌入文档 | 不能交互 |
| 降级 Mermaid | 在 md 里写代码块 | 文档、README、要能改 | 失去像素控制 |

**降级不是妥协，是选了另一个控制权模型。** 具体怎么选见 `09-carrier-routing.md`。

## 移植检查清单

- [ ] `assets/host-tokens.css` 已就位，或在页面 `:root` 里手写了一套等价变量
- [ ] 所有 `onclick="sendPrompt(...)"` 已清除
- [ ] CDN 依赖是否离线可用？Codex 环境可能断网，`cdnjs` 加载失败图就空白
- [ ] 产出路径明确（`output/` 还是仓库根），别让 Agent 猜
- [ ] `680` 这个魔数在提示里强调了——不强调就会被改成 `width="100%"` 随手缩放

## 一个反直觉的观察

这套指南真正稀缺的不是那 9 个色系，而是**它把所有约束都写成了可验证的断言**：`H = 最底部元素 + 20`、`rect_width = max(title×7, subtitle×6) + 24`、`≤4 个盒子因为 600÷4=150`。

换成「注意留白」「保持简洁」这类措辞，模型就无法自检。**能被算出对错，才会被真正执行。** 移植时如果只能保住一样东西，保住这个。
