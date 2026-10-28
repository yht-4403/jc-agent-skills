# 载体分流：什么时候用 Mermaid，什么时候用 SVG

这份文档解决一个具体问题：`wb-visualizer-guide`（渲染图）和 `jc-markdown-visual-writer-latest`（文本文档图）看起来都在讲「画图」，规则却互相打架。到底是冲突，还是分工？

结论：**是分工。所有冲突都能还原成「谁掌握渲染控制权」这一个变量。**

## 根因：控制权归属

| | Mermaid | SVG / HTML |
|---|---|---|
| 你负责 | 描述关系（谁连谁、什么类型） | 每一个坐标 |
| 渲染器负责 | 布局、连线、避让、换行 | 什么都不管 |
| 精度上限 | 渲染器的审美上限 | 你的算术上限 |
| 代价 | 样式受限于 classDef 的 CSS 子集 | 每个节点都要手算 x/y |

所以这不是「粗糙 vs 精细」，是**交出控制权 vs 保留控制权**。

交出控制权换来的是可移植：GitHub、飞书、Obsidian、Typora 都能渲染 Mermaid；SVG 在这些地方要么显示成代码，要么被安全策略拦掉。

## 判定表

| 产出载体 | 格式 | 遵循 | 典型场景 |
|---|---|---|---|
| 对话内联图 | SVG / HTML | 本 skill（`00`–`08`） | 讲解概念、对比方案、实时演示 |
| 独立 HTML 页面 | HTML + CSS | 本 skill + `assets/host-tokens.css` | 学习手册、汇报页、看板 |
| Markdown 文档 / README | Mermaid / ASCII / 表格 | `jc-markdown-visual-writer-latest` | 技术方案、评审文档、知识库 |
| PPT / Word | 原生形状或导图 | 两者都不直接适用 | 见 office 相关 skill |

判定顺序只有一步：**这张图会离开当前对话吗？** 会 → 先想 Mermaid；不会 → 直接 SVG。

## 冲突裁决表

八条硬冲突，逐条给裁决。裁决依据统一是「按载体」，不是「谁更对」。

| 议题 | Visualizer | jc-markdown | 裁决 |
|---|---|---|---|
| Emoji | 明令禁止 | 允许少量作视觉锚点 | 按载体：widget 全禁；md 文档可少量 |
| Mermaid | 除 `erDiagram` 外不用 | 主力格式 | 按载体，不互斥 |
| 色系数 | ≤2 个 ramp | 7 个语义角色按需 | widget ≤2；文档允许 3-5 个语义色 |
| 字重 | 仅 400 / 500 | 允许 700 强调 | widget 严格；文档 700 可保留 |
| 字号下限 | ≥11px | 未规定 | 两者都遵守 ≥11px |
| 节点数 | 4-5 | 4-8 | widget 更严，文档可到 8 |
| 表达顺序 | stepper `● ○ ○` | 圈号 `①②③` | 按载体。widget 的 stepper 可交互，圈号在静态渲染里更省地方 |
| 表格 | 不放 widget，走正文 | 鼓励用表格 | 按载体 |

唯一的真冲突是 emoji。其余七条都是加了「按载体」就消解的伪冲突。

## 7 个语义角色 → 9 个色系

jc-markdown 的语义色表（`references/mermaid-patterns.md` 第 59-65 行）有 7 个角色、每组三值 `fill / stroke / text`。本 skill 的 9 色系是「7 阶 × 9 系」，同样有 fill / stroke / text 的对应位（50 / 600 / 800）。

结构完全同构，可以 1:1 映射：

| 语义角色 | 色系 | fill (50) | stroke (600) | text (800) |
|---|---|---|---|---|
| 中性 / 默认 | `c-gray` | `#F1EFE8` | `#5F5E5A` | `#444441` |
| 主流程 / 动作 | `c-blue` | `#E6F1FB` | `#185FA5` | `#0C447C` |
| 判断 / 等待 / 待确认 | `c-amber` | `#FAEEDA` | `#BA7517` | `#633806` |
| 成功 / 完成 / 产出 | `c-green` | `#EAF3DE` | `#639922` | `#27500A` |
| 失败 / 风险 / 边界 | `c-red` | `#FCEBEB` | `#A32D2D` | `#791F1F` |
| AI / 系统 / 中间层 | `c-purple` | `#EEEDFE` | `#534AB7` | `#3C3489` |
| 外部系统 / 数据库 | `c-coral` | `#FAECE7` | `#D85A30` | `#712B13` |

剩下 `c-teal` 和 `c-pink` 未分配，作为备用（例如 teal = 缓存/队列，pink = 用户/角色）。**一张图里最多再动用一个备用色。**

### 可直接粘贴的 classDef 块

```mermaid
classDef neutral  fill:#F1EFE8,stroke:#5F5E5A,color:#444441;
classDef action   fill:#E6F1FB,stroke:#185FA5,color:#0C447C;
classDef decision fill:#FAEEDA,stroke:#BA7517,color:#633806,stroke-width:1.5px;
classDef success  fill:#EAF3DE,stroke:#639922,color:#27500A;
classDef error    fill:#FCEBEB,stroke:#A32D2D,color:#791F1F;
classDef ai       fill:#EEEDFE,stroke:#534AB7,color:#3C3489;
classDef external fill:#FAECE7,stroke:#D85A30,color:#712B13;
linkStyle default stroke:#B4B2A9,stroke-width:1.5px;
```

相较 jc 现行色表，这套值有三处变化，替换时注意：

- 整体色相没变，但饱和度普遍提高一档（`#F8FAFC` → `#F1EFE8`，冷灰变暖灰）
- `decision` 的描边从「fill 同色」改成实描边 `#BA7517`，判断节点因此能立起来
- 连线从冷灰 `#C9D1D9` 改暖灰 `#B4B2A9`，和九色系的底色背景不再打架

两个可选项：

- jc 原文部分示例用了 `font-weight:700`。对齐本系统的话改 500；如果文档字号偏小、对比度不够，保留 700 也是合理妥协，但要整篇统一。
- `linkStyle default` 用 gray 200 阶 `#B4B2A9`，比 jc 现在的 `#C9D1D9` 暖一档，和 9 色系的底色更搭。

## 从 Mermaid 升级到 SVG 的信号

出现以下任一条，就别再跟 Mermaid 较劲了：

1. 需要交互：滑块、切换、stepper、hover 高亮
2. 需要精确对齐：三列对比、指标卡阵列、图文并排
3. 需要在图里嵌真实数据：数值标签、进度条、迷你柱状图
4. 渲染器不支持你要的语法（不同平台的 Mermaid 版本差异很大）
5. 同一页里已有 SVG 组件，Mermaid 的风格融不进去

## 从 SVG 降级回 Mermaid 的信号

1. 这张图要贴到 README / 飞书 / issue 里
2. 用户需要自己改内容和结构
3. 需要文本 diff、需要 code review 时能看见改动
4. 只是表达拓扑关系，不需要视觉精度
5. 你已经为「让两个盒子对齐」调了超过 3 次坐标

最后一条最实用：**当你在跟坐标搏斗，说明载体选错了。**

## 关于现有配色不一致的说明

`jc-markdown-visual-writer-latest/references/mermaid-patterns.md` 里目前有三代色值并存：

- 第 59-65 行的统一语义表（`#F8FAFC` / `#F2F6FF` / `#FFF9E9` 等）
- 第 96-101 行的一组变体（`#FFF2EE` / `#EDF8EF` 等，stroke 常与 fill 相同）
- 第 130-237 行混入的 Material 色系（`#e1f5fe` / `#01579b` / `#fff9c4` / `#f9a825`）

这不是错误，是迭代留下的沉积层。如果要统一到本系统的 9 色系，建议只改「统一语义表」那一处，其余历史示例保留——它们是不同年代的正确示例，全量替换反而会让旧文档对不上。
