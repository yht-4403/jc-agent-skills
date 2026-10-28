# Operating Contract: 销售通话复盘

## 输入
建议输入：通话材料、会议目标、角色与上下文、组织标准。可选输入包括CRM字段、会议记录、邮件、公开账户信息、组织制度和历史基准。所有材料应保留来源、时间、所有者及核验状态。

## 证据状态
仅使用：`customer_confirmed`、`observable_behavior`、`seller_report`、`external_fact`、`model_inference`、`hypothesis`、`unknown`、`counterevidence`、`conflict`、`stale`。未知不等于否定，活动不等于进展，头衔不等于权力。

## 数据模式
`context`、`goal`、`evidence[]`、`counterevidence[]`、`unknowns[]`、`assumptions[]`、`options[]`、`recommended_action`、`customer_success_evidence`、`risks[]`、`approval_required[]`、`reevaluation_trigger`。

## 输出字段
证据片段、做得好的行为、升级时刻、替代表达、练习计划。结论必须能追溯到证据；估算必须展示公式、区间与假设；话术必须允许按真实语气改写；方法论字段不得被当作客户事实。

## 质量检查
- 是否产生了客户侧结果，而不只是卖方待办？
- 是否把事实、推断和未知分开？
- 是否识别至少一个反证或失效条件？
- 是否避免伪精确、固定赢率和万能脚本？
- 是否给出停止、退出、升级或重评条件？
- 是否遵守隐私、合规、授权及人工确认边界？

## 失败与降级
材料不足时只输出受限假设和验证问题；来源冲突时并列呈现；缺少组织口径时不自行发明评分、阶段门槛或预测分类；简单交易不强制使用复杂框架。

## 飞轮写入
- 完成后写入：通话复盘摘要+表现评分+改进点+下次练习重点
- 写入方式：followup.create
- 用户确认：否
