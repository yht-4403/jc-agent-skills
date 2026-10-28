# Commit Message Standard

## Format

Use Conventional Commits with a clear human summary:

```text
type(scope): 中文一句话概括

- 说明核心行为变化
- 说明关键风险处理或兼容逻辑
- 说明验证方式
```

Small changes can omit the body. Add a body when the change spans multiple files, affects shared behavior, changes data/config/deploy behavior, or has production risk.

## Types

| Type | Use for |
| --- | --- |
| `feat` | New user-visible or API-visible behavior |
| `fix` | Bug fix |
| `refactor` | Internal change without behavior change |
| `perf` | Performance improvement |
| `test` | Test-only change |
| `docs` | Documentation-only change |
| `chore` | Maintenance, scripts, repository housekeeping |
| `build` | Build system, package config, dependencies |
| `ci` | CI/CD configuration |
| `style` | Formatting-only change |
| `revert` | Revert a previous commit |

## Scope

Use a short module, package, or business-domain scope:

```text
feat(resume-editor): 新增自动保存状态提示
fix(auth): 修复刷新 token 过期判断
docs(git): 补充线性合并流程
chore(deps): 升级前端依赖锁文件
```

Omit scope only when the change is truly repository-wide.

## Quality Bar

- One commit expresses one meaningful reviewable unit.
- Do not mix unrelated cleanup, formatting, or experiments into a feature commit.
- Avoid vague headers such as `wip`, `temp`, `misc`, `update`, `fix bug`, `修改`, or `调整代码`.
- Describe behavior and risk, not just file edits.
- Keep the first line short enough to scan in Git history.
- Use Chinese by default for Chinese-speaking teams or Chinese project history; use English only when local history and project docs are English.
- Mention validation in the body when the change is not trivial.

## Examples

Good:

```text
feat(resume-export): 增加导出水印配置

- 新增导出参数解析和默认水印文案
- 保持旧模板无水印的兼容路径
- 运行 PDF 服务导出 smoke test
```

Good:

```text
fix(auth): 修复短信登录重复提交

- 增加验证码提交中的按钮禁用状态
- 后端保持幂等校验，避免重复创建会话
```

Bad:

```text
fix: update
```

Bad for daily work:

```text
Merge branch 'dev' into 'main'
```

Only accept a merge commit message when the merge is an intentional release/hotfix boundary.
