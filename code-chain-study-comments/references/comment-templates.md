# Learning Comment Templates

Use these templates when producing dense study comments. Adapt wording to the actual code; do not paste comments that do not match the verified chain.

## Density Self-Check

For Dense beginner density, the result is not sufficient if it only adds one JSDoc block above a function or one comment above a large object.

Before finishing, check that the annotated block includes comments for:

- Who calls this function/block and what user action starts it.
- Parameter destructuring, default values, optional values, and null/undefined checks.
- Important state setters, cache writes, navigation, or downstream effects.
- Async calls, promises, retries, cleanup, abort, or error handling.
- Object fields that carry important data across files.
- The next file/function/API path in the code chain.
- At least one `[注意]` or `[工程判断]` when the block has a pitfall, hidden coupling, or design tradeoff.

If most important lines still require a beginner to infer the syntax or data movement alone, add more inline comments before the specific statements.

## React / TypeScript

```tsx
// [学生列表加载链路 1/8：页面副作用入口]
// [语法] const 定义一个变量；这里变量保存的是一个函数。
// [语法] async 表示函数内部可以使用 await，通常用于请求接口等异步操作。
// [链路] 这个函数由 useEffect 调用，用来同时加载列表和统计。
const loadStudentsAndStats = async () => {
  // [语法] setLoading 是状态更新函数。
  // [链路] 设为 true 后，表格组件通常会显示加载态。
  setLoading(true)

  try {
    // [语法] Promise.all 会并发执行多个 Promise。
    // [链路] 第一个结果是学生列表，第二个结果是统计数据。
    const [studentsRes, statsRes] = await Promise.all([
      studentService.getCRMStudents(queryParams),
      studentService.getCRMStudentStats(queryParams),
    ])

    // [注意] 如果组件已经卸载，不再更新页面状态。
    if (!active) {
      return
    }

    // [语法] ?. 是可选链，避免 studentsRes 或 data 不存在时报错。
    // [语法] condition ? a : b 是三元表达式。
    // [链路] 后端返回的 data.list 会进入表格数据源。
    const list = Array.isArray(studentsRes?.data?.list) ? studentsRes.data.list : []
    setCRMStudents(list)
  } finally {
    if (active) {
      setLoading(false)
    }
  }
}
```

For React code, also explain:

- Which user action or route causes the code to run.
- Which state changes trigger re-rendering.
- Which dependency array entries make `useEffect` rerun.
- Where an event handler navigates next.
- Which child component receives the data as props.

## Python / FastAPI

```python
# [任务监控链路 2/6：依赖注入]
# [语法] def 定义函数；括号里是参数列表。
def get_task_monitor_service(
    # [语法] Annotated 表示“类型 + 额外框架说明”。
    # [语法] Session 是 SQLAlchemy 数据库会话类型。
    # [语法] Depends(get_db_session) 表示 FastAPI 自动调用 get_db_session，
    #        并把返回值放进 session 参数，前端不需要传这个参数。
    session: Annotated[Session, Depends(get_db_session)],
) -> TaskMonitorService:
    # [语法] -> TaskMonitorService 是返回值类型提示。
    # [链路] settings 用于构造 Redis 探测器等平台依赖。
    settings = get_settings()

    # [工程判断] API 层不直接查数据库，而是创建 service + repository，
    # 这样 HTTP 入口、业务逻辑、数据访问职责比较清楚。
    return TaskMonitorService(
        TaskMonitorRepository(session),
        redis_probe=build_redis_probe(settings),
    )
```

```python
# [任务监控链路 3/6：HTTP 接口]
# [语法] @router.get 是装饰器，类似 Spring 的 @GetMapping。
# [链路] 当前端请求 GET /ops/task-monitor/tasks 时，FastAPI 会调用下面的 list_tasks。
@router.get("/tasks", response_model=TaskMonitorTaskListResponse)
def list_tasks(
    # [链路] service 由 FastAPI 依赖注入，不来自请求参数。
    service: Annotated[TaskMonitorService, Depends(get_task_monitor_service)],
    # [语法] Query(alias="type") 表示前端传 ?type=xxx，Python 里变量叫 task_type。
    task_type: Annotated[str, Query(alias="type")],
    # [语法] str | None 表示可以是字符串，也可以是 None。
    status: str | None = None,
) -> TaskMonitorTaskListResponse:
    try:
        return service.list_tasks(task_type=task_type, status=status)
    except ValueError as error:
        # [链路] 把业务层错误转换成 HTTP 400，前端能得到稳定错误码。
        if str(error) == "TASK_TYPE_NOT_SUPPORTED":
            raise HTTPException(status_code=400, detail="TASK_TYPE_NOT_SUPPORTED") from error
        raise
```

For Python code, also explain:

- Decorators and what framework calls the function.
- Type hints versus runtime behavior.
- Keyword arguments.
- Why aliases translate Python `snake_case` to frontend `camelCase`.
- Where validation happens and where business logic starts.

## Go / Gin

```go
// [学生列表加载链路 5/8：HTTP 参数解析]
// [语法] func 定义函数。
// [语法] (h *StudentHandler) 是方法接收者，表示 List 属于 StudentHandler。
// [语法] *StudentHandler 是指针，避免复制整个 handler，并能访问同一个 svc。
// [链路] Gin 路由 GET /api/crm/students 会调用这个方法。
func (h *StudentHandler) List(c *gin.Context) {
    // [语法] := 是短变量声明，创建 pageNum 并赋值 1。
    // [链路] 默认查第 1 页。
    pageNum := 1

    // [语法] c.Query("pageNum") 从 URL query 里取 pageNum。
    // [语法] if v := ...; v != "" 是 Go 的 if 初始化语句。
    if v := c.Query("pageNum"); v != "" {
        // [语法] Go 常用 value, err 返回错误，而不是 try/catch。
        // [注意] 只有转换成功并且大于 0 时才覆盖默认页码。
        if n, err := strconv.Atoi(v); err == nil && n > 0 {
            pageNum = n
        }
    }

    // [链路] 解析 keyword、teacherId、isActivated 等公共筛选条件。
    commonFilters, err := parseCommonStudentFilters(c)
    if err != nil {
        response.Fail(c, domain.ErrCodeValidation, err.Error())
        return
    }

    // [语法] service.ListStudentsParams{...} 是结构体字面量。
    // [工程判断] handler 只组装参数，不直接写 SQL；业务编排交给 service。
    result, err := h.svc.ListStudents(c.Request.Context(), service.ListStudentsParams{
        PageNum: pageNum,
        Keyword: commonFilters.Keyword,
    })
    if err != nil {
        response.Fail(c, domain.ErrCodeInternal, "查询学生列表失败: "+err.Error())
        return
    }

    // [链路] 返回分页响应，前端会从 data.list / total / pageSize 中取数据。
    response.Page(c, result.List, result.Total, result.PageNum, result.PageSize)
}
```

For Go code, also explain:

- Which interface owns the method and which struct implements it.
- How `err` propagates upward.
- Why pointer fields such as `*bool` distinguish "not passed" from `false`.
- How SQL args are bound; warn if string formatting is used unsafely.
- Which JSON tags shape the frontend response.

## Chain Map Template

```text
[功能名链路]
1. 用户入口：<route/page/button>
2. 前端组件：<file:function>
3. 状态/参数：<store/helper>
4. API 封装：<service method + HTTP path>
5. 后端路由：<router mapping>
6. Handler/Controller：<parse/validate request>
7. Service：<business orchestration>
8. Repository/Mapper/SQL：<tables/external systems>
9. 返回渲染：<state setter/component props>
```

## Engineering Read Template

```text
工程判断：
- 分层：Controller/Handler 是否只负责 HTTP，Service 是否承接业务，Repository 是否负责数据访问。
- 命名：变量名是否表达业务含义，是否有缩写或误导。
- 嵌套：是否可以早返回减少层级。
- 口径：列表、统计、导出/复制等接口是否复用同一筛选条件。
- 风险：异步竞态、空值、分页上限、SQL 注入、错误码稳定性。
```
