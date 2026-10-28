# Living Redesign Plan Template（持续维护的重构计划模板）

这个文件是 reference（参考文件），不是每次都必须完整加载。只有在创建新的长期重构计划，或者修复旧计划结构时才读它。

## 为什么要有这个模板

长周期 UI 重构最容易失败的地方不是“某一页写不出来”，而是上下文丢失：今天做到哪里、为什么这么改、哪些已验证、下一步是什么。如果没有一个 living plan（持续维护的计划），下一轮 AI 很容易重新分析、重复劳动，甚至覆盖前面决策。

所以这个模板要求每次迭代都更新：

- 当前阶段。
- 当前焦点任务。
- 已完成 todo。
- 决策原因。
- 验证结果。
- 下一步。

## 模板正文

```md
# <页面或项目> Impeccable 重构实施计划

> 本文档是长周期前端重构的状态源。每次迭代前先读它，每次迭代后更新它。

## 0. Run State（运行状态）

- Last updated（最后更新）: YYYY-MM-DD HH:mm
- Current phase（当前阶段）: P0 / P1 / P2 / P3 / P4 / P5
- Current focus（当前焦点）: P1-T01
- Target project（目标项目）:
- Target route/page（目标路由或页面）:
- Scenario（场景）:
- Register（页面属性）: brand surface / product surface / mixed
- Owner（负责人）:
- Branch（分支）:

## 1. Objective（目标）

一句话说明这次重构要达成什么。

## 2. Source Context（来源上下文）

### Project Context（项目上下文）

- PRODUCT.md（产品上下文）:
- DESIGN.md（设计系统）:
- Relevant AGENTS / harness（相关规范）:
- Existing code entry（现有代码入口）:
- Existing route（现有路由）:

### Competitor / Reference Context（竞品或参考资料）

| Source（来源） | Type（类型） | What to borrow（借鉴什么） | What to avoid（避免什么） | Notes（备注） |
| --- | --- | --- | --- | --- |
|  | URL / screenshot / artifact |  |  |  |

## 3. Scenario Classification（场景分类）

- Scenario（场景）:
- Why this scenario（为什么这样分类）:
- Assumptions（假设）:
- Non-goals（不做什么）:

## 4. Design Direction（设计方向）

- Surface type（页面类型）:
- User mood and physical scene（用户情绪和使用场景）:
- Color strategy（色彩策略）:
- Typography strategy（字体排版策略）:
- Layout strategy（布局策略）:
- Motion strategy（动效策略）:
- Proof / trust strategy（证明和信任策略）:
- AI-slop risks to avoid（要避免的 AI 味）:

## 5. Todo List（任务清单）

### P0 - Context and Baseline（上下文和基线）

- [ ] P0-T01 Read project instructions and design context（读取项目规范和设计上下文）
- [ ] P0-T02 Capture current route screenshots（截取当前路由截图）
- [ ] P0-T03 Inspect current code ownership and route entry（检查当前代码归属和路由入口）
- [ ] P0-T04 Record baseline risks and constraints（记录基线风险和约束）

### P1 - Strategy and Content（策略和内容）

- [ ] P1-T01 Define page promise and primary user path（定义页面承诺和用户主路径）
- [ ] P1-T02 Map information architecture（梳理信息架构）
- [ ] P1-T03 Rewrite key UX copy and CTA hierarchy（重写关键界面文案和行动按钮层级）
- [ ] P1-T04 Decide proof, trust, or product evidence blocks（确定证明、信任或产品证据区块）

### P2 - Structure and Implementation（结构和实现）

- [ ] P2-T01 Implement primary layout changes（实现主要布局变化）
- [ ] P2-T02 Implement section/component changes（实现区块或组件变化）
- [ ] P2-T03 Align responsive structure（对齐响应式结构）
- [ ] P2-T04 Remove or consolidate repeated patterns（移除或合并重复模式）

### P3 - Motion and Interaction（动效和交互）

- [ ] P3-T01 Define purposeful motion states（定义有意义的动效状态）
- [ ] P3-T02 Implement loading, transition, hover, focus, or success states（实现加载、过渡、悬停、聚焦或成功状态）
- [ ] P3-T03 Add reduced-motion fallback（加入减少动效兜底）

### P4 - Hardening and Verification（加固和验证）

- [ ] P4-T01 Cover loading, empty, error, and long-content states（覆盖加载、空、错误和长内容状态）
- [ ] P4-T02 Verify mobile and desktop（验证移动端和桌面端）
- [ ] P4-T03 Run architecture check（运行架构检查）
- [ ] P4-T04 Run build, lint, or relevant tests（运行构建、代码检查或相关测试）
- [ ] P4-T05 Record remaining risk（记录剩余风险）

### P5 - Extraction and Documentation（抽取沉淀和文档）

- [ ] P5-T01 Extract repeated tokens/components/patterns（抽取重复设计变量、组件或模式）
- [ ] P5-T02 Update DESIGN.md or design notes（更新设计系统或设计记录）
- [ ] P5-T03 Update this plan with final status（更新本计划的最终状态）

## 6. Decisions（决策记录）

| Date（日期） | Decision（决策） | Reason（原因） | Impact（影响） |
| --- | --- | --- | --- |
|  |  |  |  |

## 7. Iteration Log（迭代日志）

### YYYY-MM-DD HH:mm

- Completed（已完成）:
- Changed files（修改文件）:
- Verification（验证）:
- New risks（新增风险）:
- Next action（下一步）:

## 8. Verification Log（验证日志）

| Date（日期） | Check（检查） | Result（结果） | Notes（备注） |
| --- | --- | --- | --- |
|  |  |  |  |

## 9. Open Questions（待确认问题）

- [ ] 

## 10. Final Acceptance（最终验收）

- [ ] Page meets objective（页面达成目标）
- [ ] Brand/product register is correct（品牌型或产品型判断正确）
- [ ] No obvious AI slop remains（没有明显 AI 味）
- [ ] Responsive behavior verified（响应式已验证）
- [ ] Accessibility basics verified（无障碍基础已验证）
- [ ] Project checks pass or exceptions documented（项目检查通过，或例外已记录）
- [ ] Design system extraction considered（已考虑设计系统抽取）
```

## 计划维护规则

- 保留历史，不要覆盖旧的 iteration log（迭代日志），只追加新日志。
- 只有实现并经过合理验证后，才能把 `[ ]` 改成 `[x]`。
- 工作开始后，不要随意改旧 todo ID。需要新增任务时，新增 ID。
- 如果用户优先级变化，写进 Decisions（决策记录）。
- 如果下一位 AI 要继续，`Current focus`（当前焦点）和 `Next action`（下一步）必须具体。
