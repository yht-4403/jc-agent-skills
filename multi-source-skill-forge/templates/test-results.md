# 测试结果 — <entry-slug>

- **测试方式**：独立 sub-agent 盲测 / 降级自测（若是降级自测必须保留此标注，可信度低于盲测）
- **测试时间**：
- **用例数**：__ | **通过**：__ | **通过率**：__%

## 逐条判定

| id | 类型 | 判定 | 说明 |
|---|---|---|---|
| should-trigger-01 | should_trigger | PASS / FAIL | |
| should-trigger-02 | should_trigger | | |
| should-trigger-03 | should_trigger | | |
| should-not-trigger-01 | should_not_trigger | | 跨能力混淆诱饵 |
| should-not-trigger-02 | should_not_trigger | | 无关诱饵 |
| edge-01 | edge_case | | 边界反转题 |
| edge-02 | edge_case | | 低置信度用例 |

## 失败分析

### <失败用例 id>
- **实际行为**：
- **预期行为**：
- **判定：修卡 还是 修测试**
  - 若修卡：改 A2 / E / B 的哪一段，改成什么
  - 若修测试：**必须写理由**，并确认不是自我合理化
- **回炉后重测结果**：

## 结论

- 通过率 <80% 时：**必须回炉重做阶 4**，不是小修
- 回炉记录：

| 轮次 | 改动 | 通过率 |
|---|---|---|
| 1 | | |
