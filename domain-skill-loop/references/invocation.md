# 调用手册

## 第一次处理一本书

```text
先用 $domain-skill-factory 把这本书初始化成领域工程；
再用 $domain-skill-loop 初始化批处理，每批 5 块，首批完成后停在样本门。
```

## 已有工程继续处理

```text
用 $domain-skill-loop 继续 /绝对路径/knowledge-engineering，
自动跑到下一个质量门，遇到复核失败最多返工两次。
```

## 配合 Goal

```text
创建 Goal：把这批行业资料构建成可发布的领域 Skills。
使用 $domain-skill-loop 每批 6 块持续推进；
完成条件是全部目标块 reviewed，路线、场景、Skills 和评测生成，release-check 通过。
```

## 查询状态

```text
用 $domain-skill-loop 查看这个工程现在完成了多少、当前批次、重试次数、下一步和停止原因。
```

## 人工门确认

```text
样本原子的粒度和证据没问题，确认 sample 门，继续到 80% 门。
```

## 不推荐的调用

- “一直循环，永远别停”：没有可验证终点。
- “把整本书总结完”：没有定义原子、场景和覆盖标准。
- “所有门都自动通过”：取消了 Loop 最重要的验证控制。
- “一个 Agent 自己做自己审”：容易产生一致性假阳性。
