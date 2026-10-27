# 标注运行时：实现要点

只在**要改 `assets/jc-note.js`** 时读这一页。生成页面不需要。

## 数据

`localStorage` key：`jc-note:{doc-id}`，值是数组：

```js
{ id, text, note, section, sectionTitle, occ, ts }
```

- `text` 保存 `Range.toString()` 的原文，**可能含段落之间的换行与缩进**，不要 trim。
- `occ` 是这段文字在本节里第几次出现（从 0 起），用于同文多处时定位。
- `section` 是 `section[id]` 的 id，恢复时只在那一节里找。

## 跨段划线

选中跨多个段落时，不能用一个 `<mark>` 包住整段内容（块级元素塞进行内元素会让排版崩）。做法是**每个文本节点一个 mark，共享 `data-jc-id`**。

1. `textNodesInRange(range)`：以 `range.commonAncestorContainer` 为根遍历文本节点，用 `compareBoundaryPoints` 判断与选区是否相交。
2. `wrapRange(range, id)`：先算出每个节点的 `[start, end]`，**从后往前**逐个 `extractContents` + `insertNode`。倒序是为了让前面的偏移不被切割影响。
3. 删除、定位一律 `querySelectorAll('mark.jcn-mark[data-jc-id="…"]')`，**不能用 `getElementById`**（跨段时 id 会重复，且 HTML 里重复 id 非法）。
4. `unwrap` 之后必须 `parentNode.normalize()`，否则反复标记会留下大量空文本节点。

## 恢复：空白宽容匹配

`collectText` 会跳过纯空白节点，所以拼出来的全文里没有段落间的换行；而保存的 `text` 里有。直接 `indexOf` 必然找不到，表现是「刷新后高亮消失」。

解法：把 needle 按 `\s+` 切段，用 `\s*` 连成正则，在全文里按 `occ` 取第 n 次匹配，再把这个字符区间映射回文本节点（映射时 clamp 到节点长度，因为匹配可能跨过被跳过的空白）。

`occ` 的统计也要用同一套 `looseCount`，否则两边的计数口径不一致。

## 就地评论框

点「不懂」→ 立即生成标记 → 在选区位置弹 `.jcn-composer`。

- 位置：取 `range.getClientRects()` 的**最后一个**矩形（跨段时是最后一行），优先放上方，`top < 10` 时放下方，左右 clamp 在视口内。
- 保存：输入即存（防抖 400ms），回车 / 点勾 / 点外部都会收起并落库。
- 同步：抽屉里同一条的 textarea 直接改 `value`，不要 `render()` 重绘（会丢滚动位置）。
- **不要加 `opacity: 0` 起始的淡入动画**。低帧率或 headless 环境下动画不推进，浮层会停在半透明帧，看起来像渲染坏了。`.jcn-drawer` 的 `transform` transition 在截图里也会卡住，做隔离测试时注入 `transition:none!important`。

## 内联时的坑

`inline.py` 把 JS 内联进 `<script>` 前，必须把源码里的 `</script` 替换成 `<\/script`。注释里出现这四个字同样致命：浏览器会在那里结束脚本，后面的代码变成正文，整页崩。

内联后要保留 `<script>` 上的 `data-jc-note` / `data-doc-id` / `data-doc-title`：`jc-note.js` 靠 `querySelector('script[data-jc-note]')` 认领自己，属性丢了运行时直接不启动。

CSS 里的 `</style>` 无法转义，遇到只能改写法；`url()` 指向本地文件时要单独处理，脚本只会报警告。
