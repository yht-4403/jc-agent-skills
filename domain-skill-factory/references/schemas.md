# 数据契约

数据结构只负责让来源、原子、场景和 Skill 能互相找到。不要把可选字段变成写作模板。

所有 JSONL 使用 UTF-8，每行一个 JSON 对象。稳定 ID 发布后不因文案修改而改变。

## 来源

`corpus/sources.jsonl` 保留来源 ID、路径、哈希、规模、层级、类型、标题和许可。易变资料增加采集日期和有效期。

来源层级：

- `primary`：原书、课程原稿、逐字稿或原始数据；
- `secondary`：摘要、拆解稿和评论；
- `external`：论文、标准、法规和外部报告。

## 文本块

`corpus/chunks.jsonl` 保留 chunk ID、source ID、顺序、标题、原始行号、字符数和本地块路径。

块状态写入 `state/chunk-status.jsonl`：pending、in_progress、extracted、reviewed、skipped。只有 reviewed 计入完整覆盖。

## 知识原子

基础结构：

```json
{
  "atom_id": "ATM-000001",
  "statement": "完整、可理解的知识陈述",
  "atom_type": "principle",
  "conditions": ["必要条件或适用范围"],
  "stage_ids": ["STG-01"],
  "scene_ids": ["SCN-001"],
  "evidence": {
    "source_id": "SRC-...",
    "chunk_id": "CHK-...",
    "quote": "最短充分证据",
    "line_start": 1,
    "line_end": 2
  },
  "confidence": 0.9,
  "status": "verified"
}
```

需要时可增加 title、explanation、examples、counterexamples、observable_signals、next_action、related_atom_ids 等字段。它们用于保存重要上下文，不是每条原子的必填项。

## 场景

`scenes/scenes.jsonl` 的最小结构：

```json
{
  "scene_id": "SCN-001",
  "name": "用户会说的具体问题",
  "stage_id": "STG-01",
  "trigger": ["典型信号"],
  "goal": "这个场景要解决什么",
  "required_inputs": ["会改变判断的信息"],
  "decisions": ["主要判断分支"],
  "workflow": ["大体处理过程"],
  "pitfalls": ["常见误用"],
  "output_contract": ["大体输出"],
  "atom_ids": ["ATM-000001"],
  "skill": "example-skill"
}
```

如果该场景需要训练或长期复盘，可以再增加 practice、feedback、success_criteria、next_routes；如果只需要完成一个明确产物，不必强加这些字段。

## 评测

`evals/cases.jsonl` 至少保留：case_id、用户请求、预期 Skill、预期场景、必须询问或包含的内容、不能出现的内容、是否需要证据和风险级别。

实际产物、失败后续和预期修正可以按测试目的增加，不要求每条案例形状完全相同。

## 关系

`atoms/relations.jsonl` 可使用 supports、explains、contradicts、depends-on、example-of、updates。只有关系确实有助于检索、冲突处理或增量更新时才记录。
