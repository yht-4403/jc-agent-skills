# verified — 阶 3 产出

> 入选单元池。每条都要写全四重验证的**硬证据**，不接受"看着挺有用"。

## 摘要

| 指标 | 数量 |
|---|---|
| 候选总数 | |
| 四重验证通过 | |
| 　A 级（跨源一致） | |
| 　B 级（单源多域） | |
| 　C 级（单源单域） | |
| 晋升为独立入口 | |
| 保留为 hub 内能力卡 | |
| 画像归档（archived） | |
| 知识验证淘汰（rejected） | |
| 争议卡 | |

**通过率**：__%（健康区间：方法论密集材料 30–50%，散文类 5–10%）
**A 级占比**：__%（多源项目健康区间 15–35%）

---

## <id> · <标题>

```yaml
id: f01
title: <标题>
type: framework | principle | counter-example | term
sources: [src-a, src-b]

V1_independent:
  passed: true
  axis: cross-source+domain        # cross-source | cross-domain | both
  evidence:
    - source_id: src-a
      location: <章节/页码/时间戳>
      quote: "<≤150 字>"
      context: <这处用在什么场景>
      independent: true
    - source_id: src-b
      location:
      quote: "<≤150 字>"
      context:
      independent: true            # 若为转引，写 false 并注明沿引关系
  independence_note: "<为什么这两处是独立的，不是同一案例的换词重述；若有转引关系在此说明>"

V2_predictive_power:
  passed: true
  novel_question: "<材料中没有直接讨论过的场景>"
  derived_answer: "<用该方法推导出的输出>"
  why_not_common_sense: "<为什么这不是'努力一点/保持理性'这类常识>"

V3_exclusivity:
  passed: true
  ordinary_answer: "<聪明但没读过的人会怎么答>"
  source_answer: "<材料给出的特定术语/顺序/框架/反直觉排序>"
  why_distinctive: "<差异点>"

V4_freshness_actionability:
  passed: true
  freshness: evergreen             # evergreen | decade | volatile
  freshness_note: "<若为 decade/volatile，写清适用窗口>"
  steps_check: "<3 步以内的执行路径，每步有客观完成标准>"

triangulation:                     # 来源 ≥2 时必填
  - source_id: src-a
    location:
    stance: 支持 | 反对 | 部分
    evidence: "<≤100 字>"
  - source_id: src-b
    location:
    stance:
    evidence:
  conclusion: "<A 级 / B 级 / C 级；一致的部分与不一致的部分分别是什么>"
  conflict_ref: conflicts/<id>.md  # 有分歧时填，无则留空

profile_fit:
  why_useful_for_user: "<解决画像中的哪个真实问题>"
  layperson_use: "<普通人如何用 1–2 步跑起来>"
  priority_for_profile: core       # core | merged | archived

promotion:
  independent_intent: true
  independent_contract: true
  independent_runtime: true
  reuse_or_evaluable: true
  destination: promoted            # promoted | router
  reason: "<一句话理由>"

confidence: A                      # A | B | C
→ 进入阶 4
```

---

## 争议卡清单

| id | 分歧点 | 涉及来源 | 类型 | 影响哪些能力卡 |
|---|---|---|---|---|
| | | | 立场相反 / 边界不同 / 归因不同 | |

（无实质分歧时明确写"经逐条对比，来源之间无实质分歧"）

---

## 归档与淘汰

| id | 标题 | 去向 | 原因 |
|---|---|---|---|
| | | rejected / archived-for-profile | 挂在哪一项、为什么 |

> `archived-for-profile` 不是知识验证失败 —— 只是对**当前这个使用者**低相关，换画像可重新提升。
