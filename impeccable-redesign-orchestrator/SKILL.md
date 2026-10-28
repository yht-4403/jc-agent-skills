---
name: impeccable-redesign-orchestrator
description: Use when the user wants a long-running frontend redesign or rebuild process with Impeccable, especially homepage redesigns, page redesigns, greenfield UI creation, competitor-inspired redesigns, or multi-hour iterative UI work that must maintain a persistent todo plan document across context windows. This skill orchestrates Impeccable commands, project design context, competitor references, browser validation, and a living implementation checklist.
metadata:
  short-description: Orchestrate long-running Impeccable redesigns
---

# Impeccable Redesign Orchestrator（Impeccable 长周期前端重构编排器）

## 这个 skill 的结构怎么理解

一个 skill（技能）通常由三层组成：

- `frontmatter`（文件顶部 `---` 之间的元信息）：给 Codex / Claude 判断“什么时候应该自动启用这个 skill”。这里建议保留英文，因为模型检索和触发更稳定。
- `SKILL.md` 正文：给 AI 执行任务时看的核心流程。这里可以写中文，模型能理解。
- `references/` 参考文件：把比较长、不是每次都要读的内容拆出去，需要时再加载，避免上下文太大。

这个 skill 的作用不是替代 Impeccable（前端设计 Skill），而是在长时间前端重构中负责“编排流程”：维护 todo 文档、记录每次迭代、读取竞品参考、调用 Impeccable 的设计方法，并确保跨上下文也能继续做。

## 设计理念：诊断先行，而不是逼用户说专业术语

用户通常不会准确说出“我要做 layout（布局调整）还是 typeset（字体排版）”。所以这个 skill 的默认工作方式是：

```text
用户用自然语言描述不满意
-> AI 先做 design diagnosis（设计诊断）
-> AI 判断问题属于哪一类
-> AI 给出 1 到 3 条可选优化路径
-> 用户确认或 AI 按最稳路径执行
```

除非用户已经明确点名某个命令，否则不要要求用户先懂 Impeccable 的所有命令。AI 应该主动把模糊需求翻译成可执行任务。

当用户表达“我也说不清哪里不好”“帮我看看这个页面”“整体有点怪”“有 AI 味”“不够高级”“动效不顺”“布局乱”时，先读取：

```text
references/question-guide.md
```

然后输出一个简短诊断，格式是：

```text
我先按 6 个维度看：结构、排版、色彩、文案、动效、真实状态。
初步判断最该处理的是：...
建议执行顺序：...
如果你同意，我先做第 1 批 todo。
```

## 什么时候使用

当用户提出下面这些需求时，使用这个 skill：

- 重构或重做 homepage（首页）、landing page（落地页）、product page（产品页）、app page（应用页）、dashboard（仪表盘）、editor（编辑器）、onboarding flow（新手引导流程）或整个前端。
- 从零开始设计一个页面，不管有没有参考图。
- 基于已有页面做 redesign（重设计），不管有没有竞品参考。
- 用户提到 Impeccable、`impeccable`、`inceptive`（用户可能误写，实际指 Impeccable），或者想把 Impeccable 命令放进一个长期重构流程。
- 任务预计持续很久，需要维护 todo list（任务清单）、execution log（执行日志）和 resumable plan（可续跑计划）。
- 用户说自己“不懂前端”“不知道怎么提需求”“帮我先分析一轮”“你先判断问题在哪里”。

如果只是一个很小的视觉微调，优先使用原本的 Impeccable skill，不需要启用这个长周期编排器。

## 最重要的工作规则

任何长周期 redesign（重设计）开始写代码前，都必须先有一个 living plan document（持续维护的计划文档）。

这个计划文档是跨上下文交接的唯一状态源。它必须记录：

- scenario type（场景类型）。
- target route or page（目标路由或页面）。
- source context（项目上下文）和 competitor references（竞品参考）。
- design direction（设计方向）和 constraints（约束）。
- stable todo IDs（稳定任务编号）。
- current phase（当前阶段）。
- completed and verified tasks（已完成并验证的任务）。
- iteration log（迭代日志）。
- next action（下一步）。

不要在没有真正实现和验证的情况下把 todo 勾掉。

## 第一步：判断场景

先把用户需求分到四种场景之一：

1. **Greenfield（从零开始）**：从零做新页面或新 UI，没有参考界面。
2. **Greenfield with references（参考竞品从零开始）**：从零做新页面，但用户给了竞品页面、截图、图片或设计参考。
3. **Existing page redesign（重构已有页面）**：优化或重做当前已有页面，没有外部参考。
4. **Existing page redesign with references（参考竞品重构已有页面）**：基于竞品页面或截图，重构当前已有页面。

如果场景不清楚，就根据用户的话做一个最稳妥的推断，并把这个 assumption（假设）写进计划文档。

开始或恢复重构时，读取：

```text
references/scenario-playbooks.md
```

## 需求不清楚时怎么引导

不要一上来问很多问题。优先用页面证据做诊断，再问最多 1 到 3 个真正会影响方向的问题。

默认先问自己：

- 这是 brand surface（品牌型页面）还是 product surface（产品型页面）？
- 用户主路径是什么？
- 当前最大问题是看不懂、太乱、太丑、太像 AI、太慢、还是状态不完整？
- 是需要 critique（设计评审）、audit（技术审计），还是直接进入某个专项优化？

如果用户只是说“帮我优化一下”，先给出诊断菜单，不要直接改：

```text
我可以先做一轮诊断，把问题分成：
1. layout（布局）
2. typeset（字体排版）
3. distill（精简）
4. quieter（去 AI 味/降噪）
5. animate（动效）
6. harden（真实状态加固）
我会给出优先级，然后你确认执行哪一批。
```

更详细的提问和诊断模板见：

```text
references/question-guide.md
```

## 计划文档放在哪里

优先遵守用户项目自己的文档规则。

在 `/Users/cv-project` 中，创建或更新：

```text
/Users/cv-project/docs/团队协作/YYYY-MM-DD-NNN-<主题>Impeccable重构-实施计划.md
```

如果同一个页面或同一个重构主题已经有计划文档，优先复用旧文档，不要新开一份。

其他项目默认规则：

- 优先放到项目已有 `docs` 目录。
- 如果没有约定，创建 `docs/redesign/YYYY-MM-DD-<topic>-impeccable-redesign-plan.md`。
- 如果没有 `docs` 目录，且位置不明确，只问用户一次；如果能合理判断，就创建最小必要目录。

创建新计划或修复不完整计划时，读取：

```text
references/plan-template.md
```

## 上下文加载规则

改代码前，只加载和当前任务有关的上下文：

- 项目说明：`AGENTS.md`、`CLAUDE.md`、README，以及更靠近目标文件的局部说明。
- 产品上下文：`PRODUCT.md`。
- 设计上下文：`DESIGN.md` 和 `DESIGN.json`，如果存在就读。
- 已有 Impeccable skill 说明，如果当前环境能读到。
- 如果是 CVProject 前端任务，还要读 harness 前端规范和完成前检查清单。
- 如果涉及简历编辑器、预览、AI 优化、布局、导出或 PDF 相关 UI，还要读简历领域和安全规则。

如果这些上下文已经在当前对话里读过，并且相关文件没有变化，就不要重复读取。

## 竞品和参考资料处理规则

当用户提供 competitor URLs（竞品链接）、screenshots（截图）或 reference pages（参考页面）时：

- 把来源 URL、截图路径或资料名记录到计划文档。
- 提取 reusable patterns（可复用模式），不要做 visual cloning（视觉克隆）。
- 写清楚 borrow（借鉴什么）、avoid（避免什么）和 why（为什么）。
- 如果需要访问网页，先看参考资料，再做设计决策。
- 如果竞品内容有版权或强品牌属性，只总结模式，做原创实现。

建议提取这些维度：

- Information architecture（信息架构）。
- First-screen promise（首屏承诺）。
- Trust evidence（信任证据）。
- CTA hierarchy（行动按钮层级）。
- Visual rhythm（视觉节奏）。
- Motion behavior（动效行为）。
- Form flow（表单流程）。
- Mobile behavior（移动端表现）。
- Empty, loading, and error states（空状态、加载状态、错误状态）。

## Impeccable 命令路由

根据问题选择 Impeccable 命令：

- `document`（记录设计系统）：当前 design system（设计系统）缺失、过期，或重构后发生变化。
- `shape`（设计定型）：方向不清楚、页面策略不清楚，或需要综合竞品参考。
- `craft`（从零设计并构建）：新页面或大型新区块从零开始。
- `critique`（设计评审）：已有 UI 需要设计评审或 AI-slop（AI 味）检测。
- `audit`（技术审计）：需要检查 accessibility（无障碍）、responsive（响应式）、performance（性能）、theming（主题）或 anti-patterns（反模式）。
- `layout`（布局调整）：层级、间距、密度、栅格或视觉节奏有问题。
- `typeset`（字体排版）：字体、中文可读性、标题、行长或字体层级弱。
- `colorize`（色彩系统化）：页面太中性，缺少品牌信号。
- `quieter`（降噪）：页面太吵、太 AI、太玻璃拟态、太霓虹、渐变太多或装饰太多。
- `bolder`（增强冲击力）：品牌页太安全、太普通、没记忆点。
- `distill`（提纯）：内容臃肿、重复，或太多同权重按钮。
- `clarify`（文案澄清）：UX copy（界面文案）、标签、空状态、错误提示或按钮文案不清楚。
- `animate`（动效）：状态变化需要更有意义的 motion（动效）。
- `overdrive`（高阶动效）：只用于值得投入复杂动效的关键品牌时刻。
- `adapt`（适配）：移动端、平板、打印或其他使用场景表现弱。
- `harden`（生产加固）：长文本、边界情况、错误、国际化、加载、空状态或真实数据条件缺失。
- `onboard`（新手引导）：首次使用流程、激活路径或空状态需要引导。
- `optimize`（性能优化）：交互、动画、包体积、LCP、INP、CLS 或渲染性能弱。
- `polish`（最终打磨）：主要工作已完成，只剩最后质量细节。
- `extract`（抽取沉淀）：重复组件、token（设计变量）、pattern（模式）或设计原语需要合并。
- `live`（实时可视化迭代）：浏览器里某一个可见元素或区块需要生成视觉变体。

不同场景的推荐命令顺序见：

```text
references/scenario-playbooks.md
```

如果用户没有明确点名命令，优先用 `critique`（设计评审）和 `audit`（技术审计）做第一轮诊断，再选择专项命令。只有当用户明确说“动效”“排版”“布局”“精简”“去 AI 味”时，才直接进入对应专项。

## 每次工作时的执行循环

每一轮工作都按这个顺序执行：

1. 找到或创建 living plan document（持续维护的计划文档）。
2. 阅读 current state（当前状态）、todo list（任务清单）、decisions（决策）和 next action（下一步）。
3. 重新确认用户最新请求，如果优先级变化，就更新计划文档。
4. 如果用户的问题不够具体，先做 design diagnosis（设计诊断），把问题翻译成 todo。
5. 选择一小批适合当前上下文窗口完成的 todo。
6. 先检查代码和 UI，再编辑。
7. 按项目已有模式实现这一批任务。
8. 运行相关验证。
9. 更新计划文档：勾选完成项、补验证证据、记录决策、写清下一步。
10. 最终回复用户：改了什么、验证了什么、计划文档在哪里、还剩什么。

如果上下文快不够了，要提前停止实现，先更新计划文档。一个过期的计划文档比没写完的代码更危险。

## Todo 写法规则

Todo 必须稳定、具体、有编号：

```text
- [ ] P1-T03 Rewrite homepage hero CTA hierarchy
- [ ] P2-T01 Replace repeated feature cards with proof-led sections
- [ ] P4-T04 Verify mobile layout at 390px and 768px
```

编号含义：

- `P0`：context and baseline（上下文和基线）。
- `P1`：strategy and content（策略和内容）。
- `P2`：structure and implementation（结构和实现）。
- `P3`：motion and interaction（动效和交互）。
- `P4`：hardening, responsive, and validation（加固、响应式和验证）。
- `P5`：extraction and documentation（抽取沉淀和文档）。

只有真正完成并经过合理验证后，才把 `[ ]` 改成 `[x]`。不要发明新的 checkbox 状态。当前正在做的任务写到 `Current focus`。

## 质量门槛

声称某个阶段完成前，至少考虑：

- 可行时，用浏览器检查改过的路由。
- UI 有变化时，检查 desktop（桌面端）和 mobile（移动端）。
- 检查基础 accessibility（无障碍）：focus（焦点）、contrast（对比度）、labels（标签）、keyboard paths（键盘路径）。
- 相关时检查 loading（加载）、empty（空）、error（错误）和 long-content（长内容）状态。
- 根据项目运行 build（构建）、lint（代码检查）、tests（测试）和 architecture checks（架构检查）。
- 把命令结果写进计划文档；没跑的检查要说明原因。

CVProject 前端通常需要运行：

```text
bash /Users/cv-project/harness/脚本/check-frontend-architecture.sh
npm run build
```

如果是 UI 任务，还需要 browser validation（浏览器验证），除非用户明确只要规划。

## CVProject 默认规则

当工作目录是 `/Users/cv-project/chengzicv-frontend` 时：

- 首页、校园大使、邀请页、协议页、隐私页、关于页，通常是 `brand surface`（品牌型页面）。
- 简历起始、简历选择、简历优化、简历匹配、简历预览、编辑器、个人中心、转移、定价结算、内部分析，通常是 `product surface`（产品型页面）。
- 业务页面放在 `src/features/<business>`。
- 简历 UI 放在 `src/features/resume`。
- 纯简历模型、patch（补丁）、布局、渲染逻辑放在 `src/domains/resume`。
- AI workflows（AI 工作流）放在 `src/ai`。
- 应用装配放在 `src/app`。
- 不要把业务代码移到 `src/components` 或根 `src/pages`。

## 最终回复要求

每一轮工作结束时，回复里要包含：

- 计划文档路径。
- 完成的 todo ID。
- 运行了哪些验证，以及结果。
- 下一步还要做什么。
- 是否有 blocker（阻塞）或 assumption（假设）。

最终回复要短。详细过程留在计划文档里。
