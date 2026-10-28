# STATE — <项目名>

> 断点续跑用。每次进入会话先读本文件，确认当前处在哪一阶、下一步做什么。
> **每次阶段推进后立即更新。**

## 当前状态

```yaml
project: <slug>
depth: full                       # fast | full
output_mode: mix                  # hub | split | mix
current_phase: 3                  # 0|1|2|3|4|5|6|7
status: in_progress               # in_progress | blocked | done
last_updated: <YYYY-MM-DD>
```

## 阶段进度

| 阶 | 名称 | 状态 | 产出 | 备注 |
|---|---|---|---|---|
| 0 | 定盘 | ✅ done | CHARTER.md | 入口预算 6 |
| 1 | 通读 | ✅ done | OVERVIEW.md | 批判段 4 条 |
| 2 | 抽丝 | 🔄 in_progress | candidates/*.md | framework/principle 全量；case/ce/glossary 检索式 |
| 3 | 三角 | ⬜ pending | verified.md | |
| 4 | 立卡 | ⬜ pending | .forge/ | |
| 5 | 织网 | ⬜ pending | GLOSSARY.md | |
| 6 | 试炼 | ⬜ pending | test-prompts.json | |
| 7 | 出炉 | ⬜ pending | dist/ + DIGEST.md | |

## 待用户确认的点

| 时机 | 内容 | 状态 |
|---|---|---|
| 开工前 | 三问（材料/画像/入口数）+ 深度 | ✅ 已确认 |
| 阶 1 后 | OVERVIEW 骨架 + 批判段 | ✅ 已确认 |
| 阶 3 后 | 入选名单 + 置信度分布 | ⬜ 待确认 |
| 阶 7 前 | 编译形态 + 入口清单 | ⬜ 待确认 |

## 覆盖率记录（阶 2）

> 采用检索式的 extractor，必须记录覆盖率对比结果。

| extractor | 策略 | 相对全量基线漏检数 | 结论 |
|---|---|---|---|
| framework | 全量 | — | 基线 |
| principle | 全量 | — | 基线 |
| case | 检索式 | 0 | 通过 |
| counter-example | 检索式 | 0 | 通过 |
| glossary | 检索式 | | |

## 下一步

> <一句话说明下一次接手时该做什么>

## 遗留问题

- <证据不足、需要更多材料才能定论的点>
- <需要用户补充的信息>

## 变更日志

| 时间 | 变更 | 原因 |
|---|---|---|
| | | |
