# Question Guide（如何把模糊需求变成好问题）

这个文件解决一个核心问题：用户不一定懂前端，也不一定知道该说 layout（布局）、typeset（字体排版）、animate（动效）还是 quieter（降噪）。AI 要先帮用户诊断，而不是要求用户先会提专业需求。

## 默认原则

用户说不清楚时，不要追问太多。先看页面，再给判断。

推荐顺序：

```text
用户自然语言描述
-> AI 诊断 6 到 8 个维度
-> AI 总结最高优先级问题
-> AI 给 1 到 3 条优化路径
-> 用户选，或 AI 按最稳路径先做第一批
```

## 用户可以怎么说

这些都是足够好的需求，不需要用户懂术语：

```text
使用 $impeccable-redesign-orchestrator，帮我先分析这个首页哪里最不合理。
```

```text
使用 $impeccable-redesign-orchestrator，我觉得这个页面有 AI 味，但说不清，你先诊断再给重构 todo。
```

```text
使用 $impeccable-redesign-orchestrator，这个页面动效不顺，先分析哪些状态最值得补动效。
```

```text
使用 $impeccable-redesign-orchestrator，我想让页面更精简，但不知道该删什么，你先评估信息优先级。
```

```text
使用 $impeccable-redesign-orchestrator，参考这个竞品，不要照抄，先告诉我可以借鉴哪些模式。
```

## AI 应该如何反问

最多问 1 到 3 个问题，而且只问会影响方向的问题。

好问题：

- “这个页面主要目标是让用户点击开始，还是让用户建立信任？”
- “你更想先改首屏，还是先改完整转化路径？”
- “参考竞品时，你希望借鉴信息结构、视觉风格，还是动效节奏？”

差问题：

- “你想要什么风格？”太空。
- “你喜欢什么颜色？”太早。
- “你要不要更现代一点？”不可执行。
- “你想怎么排版？”用户未必知道。

如果能从项目上下文和页面目标推断，就不要问。

## 诊断输出模板

当用户要求“先分析一轮”时，用这个格式：

```text
我先不急着改，先按 8 个维度诊断：

1. 结构：
2. 布局：
3. 字体排版：
4. 色彩：
5. 文案：
6. 动效：
7. 真实状态：
8. AI 味：

最高优先级问题是：
- P1：
- P2：
- P3：

建议执行路径：
路径 A：...
路径 B：...
路径 C：...

我建议先走路径 A，因为...
如果你同意，我会把它写进计划文档，并执行第一批 todo。
```

## 常见模糊感受怎么翻译成命令

| 用户说法 | AI 应该理解成 | 推荐命令组合 |
| --- | --- | --- |
| 看起来很乱 | 信息层级和布局问题 | `critique -> layout -> distill -> polish` |
| 不够高级 | 可能是排版、间距、色彩和证据不足 | `critique -> typeset -> layout -> colorize -> polish` |
| 很 AI | AI slop 问题 | `critique -> distill -> quieter -> typeset -> polish` |
| 太花了 | 视觉噪声过多 | `quieter -> layout -> polish` |
| 太普通 | 品牌页缺少记忆点 | `shape -> bolder -> colorize -> polish` |
| 字看起来不舒服 | 字体排版问题 | `typeset -> audit -> polish` |
| 首屏不吸引人 | 页面承诺、证据和视觉焦点问题 | `critique -> shape -> layout -> typeset -> colorize` |
| 动效不顺 | 状态反馈和 motion 问题 | `animate -> audit -> optimize -> polish` |
| 页面很慢 | 性能问题 | `audit -> optimize -> polish` |
| 手机端不好用 | 响应式和触控问题 | `adapt -> harden -> audit` |
| 不知道该删什么 | 信息优先级问题 | `distill -> clarify -> layout` |
| 竞品比我好 | 需要参考拆解，不是照抄 | `reference capture -> pattern extraction -> shape -> targeted commands` |

## 面向 CVProject 的默认诊断问题

如果目标是 CVProject 首页，默认先判断：

- 首页有没有证明“上传简历 -> 粘贴 JD -> 匹配和优化 -> 排版 -> 导出”这条链路？
- 首屏是在建立信任，还是只是在说泛 AI 能力？
- CTA（行动按钮）是否只有一个清晰主路径？
- 是否存在泛 SaaS 模板感：大数字、重复卡片、渐变、玻璃拟态、空泛文案？
- 中文标题是否具体、可信、有动作感？
- 移动端是否能快速理解下一步？

如果目标是 CVProject 简历优化页，默认先判断：

- 用户是否知道当前处于上传、解析、优化、编辑、导出的哪一步？
- 复杂功能是否有主次，还是全部同权重？
- 错误、空状态、长文本、AI 返回异常是否有清晰处理？
- 工具栏和编辑区是否支持高频重复操作？
- 动效是否服务于状态理解，而不是装饰？

## 如何写入计划文档

诊断完成后，要把结论写进计划文档：

```md
## Diagnosis（诊断）

- Date:
- Target:
- Main issue:
- Recommended path:

### Findings

| Dimension | Finding | Priority | Command |
| --- | --- | --- | --- |
| Layout |  | P1 | layout |
| AI slop |  | P1 | quieter |

### Selected Path

- Path:
- Reason:
- First todo:
```

这样下一轮上下文压缩后，AI 也能知道为什么先做这一批。
