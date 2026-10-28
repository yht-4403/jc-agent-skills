# Scenario Playbooks（场景执行剧本）

这个文件是 reference（参考文件）。当 skill 判断出用户属于哪种 redesign（重设计）场景后，再读取对应部分。

## 1. Greenfield（从零开始）

定义：用户想从零做一个新页面、新流程或新界面，没有参考界面。

推荐顺序：

```text
document（记录设计系统） -> shape（设计定型） -> craft（从零设计并构建） -> audit（技术审计） -> harden（生产加固） -> adapt（适配） -> polish（最终打磨） -> extract（抽取沉淀）
```

流程：

1. 创建 living plan（持续维护的计划）。
2. 加载 product context（产品上下文）和 design context（设计上下文）。
3. 用 `shape`（设计定型）澄清用户、页面承诺、内容层级和页面类型。
4. 用 `craft`（从零设计并构建）完成第一版实现。
5. 完成前用 `audit`（技术审计）和 `harden`（生产加固）检查。
6. 只有出现可复用模式时才用 `extract`（抽取沉淀）。

避免：

- 一开始就用 `live`（实时可视化迭代）。
- 在用户主路径没清楚前，先堆装饰性区块。
- 把 product tool page（产品工具页）做成 marketing hero（营销首屏）。

## 2. Greenfield With References（参考竞品从零开始）

定义：用户想从零做新页面、新流程或新界面，并提供了竞品 URL、截图或设计参考。

推荐顺序：

```text
reference capture（记录参考） -> pattern extraction（模式提取） -> shape（设计定型） -> craft（从零设计并构建） -> critique（设计评审） -> audit（技术审计） -> polish（最终打磨）
```

流程：

1. 把每个参考来源记录到计划文档。
2. 先查看参考，再做设计决策。
3. 提取 pattern（模式），不要复制 pixels（像素级视觉）。
4. 写一个 borrow / avoid / original direction（借鉴 / 避免 / 原创方向）表。
5. 用 `shape`（设计定型）综合成新的设计方向。
6. 用 `craft`（从零设计并构建）实现。
7. 用 `critique`（设计评审）检查原创性和 AI-slop（AI 味）风险。

避免：

- 直接复制竞品布局、文案或品牌资产。
- 让竞品的 register（页面类型）覆盖用户自己的产品上下文。
- 不检查 performance（性能）和 reduced-motion fallback（减少动效兜底），就照搬竞品动效。

## 3. Existing Page Redesign（重构已有页面）

定义：用户已有当前页面，想优化或重做它，没有外部参考。

推荐顺序：

```text
document（记录设计系统） -> baseline screenshot（基线截图） -> critique（设计评审） -> audit（技术审计） -> shape if needed（需要时设计定型） -> targeted commands（针对性命令） -> harden（生产加固） -> polish（最终打磨）
```

针对性命令选择：

- 太乱、太满：`distill`（提纯）。
- 层级差：`layout`（布局调整）。
- 字体弱：`typeset`（字体排版）。
- 品牌页太普通：`bolder`（增强冲击力）或 `colorize`（色彩系统化）。
- 太吵或太像 AI：`quieter`（降噪）。
- 文案不清楚：`clarify`（文案澄清）。
- 状态不完整：`harden`（生产加固）。
- 动效弱：`animate`（动效）。
- 页面慢：`optimize`（性能优化）。

流程：

1. 编辑前先记录当前行为和约束。
2. 检查 route entry（路由入口）、component ownership（组件归属）和 state dependencies（状态依赖）。
3. 除非计划文档明确写了，否则保持现有工作链路不被破坏。
4. 每次只改一个 section（区块）或 flow（流程）。
5. 每一批完成后做验证。

避免：

- 没理解状态和 API 依赖就整页替换。
- 只为了视觉好看就跨 feature（业务域）移动文件。
- 没检查响应式就把视觉改动标记完成。

## 4. Existing Page Redesign With References（参考竞品重构已有页面）

定义：用户已有当前页面，并希望参考竞品或设计参考来重构。

推荐顺序：

```text
baseline screenshot（基线截图） -> reference capture（记录参考） -> critique current（评审当前页） -> extract reference patterns（提取参考模式） -> shape delta（定义变化方向） -> implement batches（分批实现） -> audit（技术审计） -> polish（最终打磨）
```

流程：

1. 截取当前页面 baseline（基线）。
2. 截取或记录竞品/参考页面。
3. 比较当前页和参考页：
   - 参考页解决了什么问题？
   - 哪些 pattern（模式）适合用户自己的产品？
   - 哪些 pattern 会偏离品牌或带来风险？
4. 把参考洞察转成 todo。
5. 按阶段实现，不要从上到下复制竞品。
6. 重新对照用户自己的 `PRODUCT.md` 和 `DESIGN.md`。

避免：

- 把目标页面改成竞品克隆。
- 未判断品牌适配，就照搬竞品颜色、字体或承诺。
- 因为竞品看起来精致，就默认它的交互适合当前产品。

## 跨场景检查点

每一种场景都要检查：

- register（页面类型）是否明确：brand surface（品牌型页面）、product surface（产品型页面）或 mixed（混合）。
- primary user path（用户主路径）是否明确。
- AI-slop risks（AI 味风险）是否列出。
- mobile behavior（移动端表现）是否考虑。
- loading（加载）、empty（空）、error（错误）和 long-content states（长内容状态）是否考虑。
- verification commands（验证命令）是否记录。
- plan（计划）里的 next action（下一步）在上下文压缩后仍然可执行。

## 诊断先行流程

当用户不知道该提什么问题，或只说“帮我优化”“不够好”“你先分析一轮”时，先用这个流程：

```text
critique（设计评审） + audit（技术审计）
-> diagnosis matrix（诊断矩阵）
-> 选择最高优先级问题
-> 转成 todo
-> 再进入对应命令组合
```

诊断矩阵固定看 8 类：

1. Structure（结构）：页面顺序、主路径、信息架构。
2. Layout（布局）：空间、对齐、密度、视觉节奏。
3. Typography（字体排版）：标题、正文、行长、中文可读性。
4. Color（色彩）：品牌色、对比度、状态色、装饰色。
5. Copy（文案）：按钮、标题、错误、空状态是否具体。
6. Motion（动效）：反馈、过渡、加载、减少动效兜底。
7. States（状态）：加载、空、错误、长内容、真实数据。
8. AI slop（AI 味）：渐变文字、玻璃拟态、重复卡片、空泛 SaaS 感。

诊断输出不要太长。给用户 1 到 3 条路径即可：

```text
优先路径 A：先去 AI 味和精简
优先路径 B：先修布局和排版
优先路径 C：先补动效和真实状态
```

## Impeccable 命令组合

### First Diagnosis（先诊断一轮）

```text
critique（设计评审） -> audit（技术审计） -> shape if direction unclear（方向不清楚时设计定型） -> select targeted bundle（选择专项组合）
```

适合：用户说不清问题、页面整体不舒服、需要 AI 先判断哪里最值得改。

### AI Slop Removal（去除 AI 味）

```text
critique（设计评审） -> distill（提纯） -> quieter（降噪） -> typeset（字体排版） -> layout（布局调整） -> colorize（色彩系统化） -> polish（最终打磨）
```

### Motion Upgrade（动效升级）

```text
shape if needed（需要时设计定型） -> animate（动效） -> audit（技术审计） -> optimize（性能优化） -> adapt（适配） -> polish（最终打磨）
```

只有高价值品牌时刻才用 `overdrive`（高阶动效）。

### Product Tool Hardening（产品工具页加固）

```text
audit（技术审计） -> layout（布局调整） -> clarify（文案澄清） -> harden（生产加固） -> adapt（适配） -> optimize（性能优化） -> polish（最终打磨）
```

### Brand Homepage Rebuild（品牌首页重构）

```text
document（记录设计系统） -> critique（设计评审） -> shape（设计定型） -> distill（提纯） -> typeset（字体排版） -> colorize（色彩系统化） -> live（实时可视化迭代） -> harden（生产加固） -> polish（最终打磨） -> extract（抽取沉淀）
```

### Existing Mature Site Refactor（成熟网站重构）

```text
document（记录设计系统） -> baseline（建立基线） -> critique（设计评审） -> audit（技术审计） -> batch implementation（分批实现） -> harden（生产加固） -> regression check（回归检查） -> extract（抽取沉淀） -> document（更新设计系统）
```
