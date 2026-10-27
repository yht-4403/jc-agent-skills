# 原生箭头与关系表达

## 目录

- 选择规则
- 跨端默认：纵向箭头流程
- 桌面短内容：横向箭头链
- 简单分支
- 必须使用图示的情况

## 选择规则

先判断关系拓扑，再选择表达：

- 单一主线、阶段推进：原生纵向箭头流程；
- 三个以内短节点、主要桌面阅读：可用横向箭头链；
- 一个上游分成多个结果：上游高亮块＋向下箭头＋下方分栏；
- 多个判断、交叉连线、回路、并行泳道：Mermaid、SVG 或平台画板；
- 只是步骤清单且箭头没有新增含义：直接使用有序列表。

## 跨端默认：纵向箭头流程

纵向流程由“全宽节点＋居中向下箭头”重复组成。它牺牲少量桌面横向密度，换取手机和电脑完全一致的阅读顺序。

腾讯 MDX 示例：

```mdx
<Callout icon="🎯" blockColor="light_blue" borderColor="blue">
    <Heading level="4">
        ① 对齐需求
    </Heading>
    <BulletedList>
        确认业务目标与边界
    </BulletedList>
</Callout>

<Paragraph textAlign="center">
    <Mark bold color="blue">↓</Mark>
</Paragraph>

<Callout icon="🔎" blockColor="light_green" borderColor="green">
    <Heading level="4">
        ② 执行与验证
    </Heading>
    <BulletedList>
        完成关键动作并验证结果
    </BulletedList>
</Callout>
```

飞书 XML 示例：

```xml
<callout emoji="🎯" background-color="light-blue" border-color="blue">
  <h4>① 对齐需求</h4>
  <ul><li>确认业务目标与边界</li></ul>
</callout>
<p align="center"><b><span text-color="blue">↓</span></b></p>
<callout emoji="🔎" background-color="light-green" border-color="green">
  <h4>② 执行与验证</h4>
  <ul><li>完成关键动作并验证结果</li></ul>
</callout>
```

每个节点控制在一个小标题和一至三条短说明。更长内容放在流程后解释，不把节点写成小作文。

## 桌面短内容：横向箭头链

横向链使用“内容栏＋窄箭头栏”交替排列，例如三节点可用：

```text
30% 节点 → 5% 箭头 → 30% 节点 → 5% 箭头 → 30% 节点
```

只在以下条件同时满足时使用：

- 节点不超过三个；
- 每个节点内容很短；
- 文档主要在电脑查看；
- 平台已验证分栏不会在手机端错序。

四个以上节点或主要跨端阅读时，改用纵向流程。不要把七栏箭头链当默认样式。

## 简单分支

原生组件没有坐标和连线系统，只能表达视觉分组：

1. 用全宽高亮块表示上游；
2. 用居中 `↓` 表示进入下一层；
3. 用两栏或三栏表示互斥结果、角色或后续路径；
4. 在每栏标题中写清条件，避免只靠位置猜测关系。

如果读者必须依靠连接线才能判断每个条件通向哪里，停止模拟，改用真正图示。

## 必须使用图示的情况

- 条件分支超过一层；
- 存在回路、重试或反馈；
- 多个角色并行交互；
- 节点之间有多对多关系；
- 连线本身包含重要条件；
- 需要表达空间、层级或网络拓扑。

此时优先选择平台可编辑画板；平台能力不足时使用 Mermaid→SVG，并保留源文件。SVG 不稳定时回退高清 PNG。
