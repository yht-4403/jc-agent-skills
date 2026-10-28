---
name: domain-skill-loop
description: 为长篇书籍、课程、报告集合或岗位知识库的领域 Skill 工程运行有界批处理循环：领取文本块、调用 Worker 抽取、机械校验、独立复核、持久化状态、失败返工，并在样本/覆盖/发布质量门停止。适用于用户说“全量拆完”“继续下一批”“不要每批都问我”“用 Loop/Goal 跑这套资料”，或需要跨多轮可靠处理十几万字以上资料。依赖 domain-skill-factory 已初始化的工程；不要把本 Skill 当成无限重试或单次摘要工具。
---

# 领域 Skill 批处理 Loop

把长任务从“人不断写下一条提示”变成可恢复的控制循环：

`观察状态 → 领取批次 → Worker 执行 → 机械验证 → 独立复核 → 更新状态 → 继续/返工/停在质量门`

## 前置检查

1. 读取同级 `$domain-skill-factory`；它定义资料、原子、场景和发布契约，本 Skill 只负责调度。
2. 确认工程已有 `corpus/chunks.jsonl` 和 `state/chunk-status.jsonl`。若没有，先用工厂 `prepare` 与 `sync-status`。
3. 读取 [Loop 模型](references/loop-model.md)；需要实际执行批次时再读 [Worker 与 Reviewer 契约](references/worker-review-contract.md)。

## 初始化

```bash
python3 scripts/loop.py init \
  --project <领域工程路径> \
  --goal "完成该资料范围的全量原子化与 Skill 发布" \
  --batch-size 5 \
  --max-retries 2 \
  --max-batches 100
```

默认人工门为 `sample,80,100`：首批复核后、一级来源完整复核达到 80% 后、抽取达到 100% 后暂停。初始化会接管工程里已有的 `in_progress` 块，不删除现有原子、场景或状态。

## 运行一轮

用户说“继续这个 Loop”时：

1. 运行 `status`，以外部状态文件为准，不凭对话记忆判断进度。
2. 运行 `advance`：
   - 返回 `claim`：已领取新批次，进入 Worker；
   - 返回 `work`：处理当前 `in_progress` 批次；
   - 返回 `review`：启动独立 Reviewer；
   - 返回 `gate`：暂停并向用户报告质量门；
   - 返回 `synthesize`：全量抽取已复核，进入路线/场景/Skill 合成；
   - 返回 `complete` 或 `stopped`：不得继续领取。
3. Worker 严格按工厂的原子抽取协议处理当前批次，只追加/修正当前批次相关原子。
4. 运行 `submit --batch-id ... --worker ... --note ...`。脚本先执行工厂的原子校验；失败则不得进入复核。
5. 使用新上下文或子代理作为 Reviewer。Reviewer 不读取 Worker 的自评，只读原文块、原子记录和契约。
6. Reviewer 通过时运行：

```bash
python3 scripts/loop.py review --project <工程> --batch-id <批次> \
  --result pass --reviewer <身份> --note <复核结论>
```

Reviewer 不通过时使用 `--result fail`；批次退回 `in_progress`。超过重试上限自动停止，不无限烧 Token。

## 在一次调用中持续运行

用户明确说“持续跑到质量门/不要每批询问”时，重复“运行一轮”，直到出现以下任一终止状态：

- `gate`：必须由用户确认；
- `stopped`：重试、批次数或结构错误触发保护；
- `synthesize`：抽取完成，切换到领域合成；
- `complete`：发布校验通过；
- 工具权限、资料或关键信息阻断。

不要因为一轮成功就结束，也不要越过人工门。

## 确认质量门

```bash
python3 scripts/loop.py ack-gate --project <工程> \
  --gate sample --reviewer <确认人> --note <确认意见>
```

支持 `sample`、`80`、`100`。确认只允许 Loop 继续，不等于内容质量自动合格。

## 合成与发布

100% 抽取门确认后，按工厂协议完成路线图、场景卡、References、路由/执行 Skills 与评测；然后运行：

```bash
python3 scripts/loop.py release-check --project <工程>
```

只有工厂 `validate-project` 通过，Loop 才标记 `complete`。

## Goal 模式

Goal 与 Loop 配合使用：

- Goal 保存外层终点和长期持续意图；
- Loop 保存批次状态、验证证据、返工次数和停止条件；
- Skill 规定每一步怎么做；
- scripts 做确定性校验。

仅当用户明确要求创建 Goal、全量完成或持续推进时创建 Goal。Goal 的完成条件应写成可验证指标，例如“全部目标块 reviewed，路线/场景/Skills/评测生成且 release-check 通过”，而不是“读完这本书”。

## 用户调用方式

详细示例见 [调用手册](references/invocation.md)。常用说法：

- `用 $domain-skill-loop 初始化这本书，每批 5 块。`
- `用 $domain-skill-loop 继续广智销售工程，跑到下一个质量门。`
- `用 Goal + $domain-skill-loop 全量处理这批投放资料，样本门停一下，其余自动推进。`
- `查看这个 Loop 当前覆盖率、批次和停止原因。`

## 不可违反

- Worker 不能复核自己的批次；没有独立 Reviewer 时停在 `review`。
- 不允许 pending 直接变 reviewed。
- 不允许以“有一条原子”代表整块完整抽取。
- 不允许在证据校验失败、来源串线或短引不匹配时继续。
- 不允许用自动循环越过付费资料、合规或发布审批边界。
- 不允许把 `in_progress`、`extracted` 或原子触达率描述为完整覆盖率。
