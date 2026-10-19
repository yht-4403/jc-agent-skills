# 腾讯智能文档适配

## 目录

- 创建与编辑
- 原生组件映射
- 图片与复杂图
- 校验
- 已知限制

## 创建与编辑

优先使用官方腾讯文档 MCP 的实际工具 Schema。常见能力包括：

- `create_smartcanvas_by_mdx`：通过 MDX 创建智能文档；
- `smartcanvas.find`：定位 Block；
- `smartcanvas.edit`：插入、更新或删除 Block；
- `smartcanvas.read`：分页反向读取；
- `upload_image`：上传图片后取得可用于文档的图片标识；
- `create_flowchart_by_mermaid`：创建独立在线流程图。

工具名称或参数变化时以实时 `tools/list` 为准，不凭旧文档猜测。

官方网页、官方 Skill 与当前运行时可能处于不同版本，出现 `create_smartcanvas_by_markdown`、`create_smartcanvas_by_mdx`，或点号/下划线风格不同都不应靠名称猜参数。先读取当前工具描述和 MDX Reference，再构造调用。个人版与企业版同时连接时，在第一次写入前确认目标账号。

## 原生组件映射

- 高亮：`Callout`，使用 `blockColor`、`borderColor` 和单个 emoji `icon`；
- 分栏：`ColumnList`＋`Column width="...%"`；
- 强调文字：`Mark`；
- 段落对齐和背景：`Paragraph`；
- 标题：Markdown 标题或 `Heading`；
- 列表：Markdown 列表或 `BulletedList`／`NumberedList`；
- 待办：`Todo`；
- 分隔线：`Divider`；
- 图片：先上传，再用 `Image`。

MDX 必须遵循平台当前提供的规范：块组件缩进、属性引号、布尔属性、颜色 Token 和可用组件都以实时 MDX Reference 为准，未知组件退化为平台确认支持的 Markdown。

不要假设 Markdown 的 `**文字**` 在 MDX/SmartCanvas 转换后一定显示为粗体。需要稳定强调时优先使用当前规范支持的 `Mark`、标题或 Callout；发布后搜索字面 `**`，发现残留就定点修正，不把星号原样留给用户。

## 图片与复杂图

简单流程优先使用原生纵向箭头组件。复杂关系、中文行业地图和需要嵌入正文的 Mermaid 默认采用：

```text
Mermaid 源文件
→ 渲染 SVG
→ upload_image
→ Image 嵌入智能文档
```

SVG 显示异常时渲染为高分辨率 PNG。始终保留 `.mmd` 或 `.svg` 源文件，不把上传后的图片当唯一副本。不要为了“可编辑”先创建一个无法嵌入正文的独立流程图，再把链接当作正文图。

独立原生流程图适合多人协作编辑，但当前能力可能存在中文、嵌入或编辑接口限制。创建前读取实时 Schema；不能嵌入时，在正文放预览图和编辑链接，不声称它是正文原生块。

## 校验

创建或更新后：

1. 获取顶层页面；
2. 使用 `smartcanvas.read` 按 `next_token` 读到末尾；
3. 检查关键标题、开头、尾部、图片与组件；
4. 搜索字面 `**`、Mermaid 代码、Unsupported、BlockQuote 滥用、空组件和异常降级；
5. 检查活动文档链接、目标账号和权限是否正确；
6. 需要确认更新位置时用 `smartcanvas.find` 获取 Block ID。

长文不要只读取第一页就声明完整。

## 已知限制

- MDX 是富排版系统，不是自由连线画布；
- 分栏可以模拟短横向流程，但不适合复杂关系或跨端默认；
- Mermaid 代码不能假设会在智能文档正文原生渲染；
- 图片上传标识和平台内部 URL 由平台管理，不硬编码外链；
- 标准 Markdown 在不同创建入口中的渲染能力可能不同，不能只检查源稿；
- 编辑既有文档时先定位 Block，避免整体重建导致用户内容丢失。
