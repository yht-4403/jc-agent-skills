---
name: code-chain-study-comments
description: Trace a complete feature code path and produce beginner-friendly study comments. Use when the user wants to learn code by following one feature from UI/page/event through frontend state, API/service calls, backend routing/controllers/handlers, services, repositories/mappers/SQL, external systems, and back to rendering. Also use when asked to add or draft dense learning comments for React, Next.js, Vue, Python, FastAPI, Go, Gin, Java, Spring, or mixed frontend/backend code; especially when the user says they do not understand the syntax and wants detailed annotations for learning rather than production comments.
disable-model-invocation: true
---

# Code Chain Study Comments

## Core Rule

Separate learning annotations from production code.

- Default to a chat walkthrough or a study document.
- Only write dense comments into source files when the user explicitly asks for a learning worktree/commented copy.
- If the user explicitly says the current checkout is only for learning, or project instructions say learning comments may be added directly to production source, use **Learning-in-place mode**: write dense learning comments directly into the existing source files without creating a separate worktree.
- Do not commit or push learning-comment changes unless the user explicitly requests it.
- In production code, keep only comments that explain non-obvious business rules, design decisions, edge cases, or operational risks.
- The production-code restraint does not apply to a learning-only checkout after the user has explicitly allowed dense in-place comments; still label comments clearly and avoid unrelated refactors.

## Workflow

1. Identify the feature entry point from the user's description: route, page, button, API path, cron job, worker task, or domain action.
2. Read local project instructions before changing anything: repository `AGENTS.md`, `CLAUDE.md`, and relevant docs when present.
3. Build an evidence-backed chain map:
   - UI route/page/component
   - event handler or lifecycle/effect
   - state/store and parameter construction
   - API client/service wrapper
   - backend router/controller/handler
   - backend service/business layer
   - repository/mapper/SQL/database/external integration
   - response DTO/schema and frontend rendering
4. Use `rg`/file reads to verify each link. Do not invent missing links.
5. Keep a compact chain map internally. For Architecture density or an explicit overview-only request, present the map first. For Study and Dense beginner modes with inspectable code, start from one representative original artifact, highlight it, then show the compact map and return to the artifact.
6. Label comments by purpose when useful:
   - `[语法]` for language/framework syntax
   - `[链路]` for where data came from and where it goes next
   - `[工程判断]` for whether the design is reasonable
   - `[注意]` for pitfalls, edge cases, or debugging clues
7. Preserve the same chain name and step number across files, for example `[学生列表加载链路 3/8]`.
8. Choose and state the annotation density before editing:
   - **Architecture density**: block-level comments only, for experienced readers.
   - **Study density**: comments before important statements plus comments on non-obvious expressions.
   - **Dense beginner density**: line-by-line or clause-by-clause explanations for syntax, data flow, state changes, async behavior, null checks, destructuring, framework calls, and edge cases.
9. If the user says "彻底学习", "看不懂", "注释密度不够", "加大量注释", "源码学习", or similar, default to **Dense beginner density** for the selected chain.
10. In Dense beginner density, do not stop at a header comment above a large block. Add comments inside the block next to the statements that carry syntax, control flow, data shape, side effects, async behavior, or cross-file handoffs.

## Artifact-first Walkthrough

For Study and Dense beginner walkthroughs, read `../jc-plain-explainer/references/artifact-first-understanding.md` by default whenever inspectable code or runtime evidence exists. Do not wait for the user to say “真实体感”, request actual API input/output, or name the supporting Skill. Skip the full loop only for Architecture density, an explicit overview-only request, or when no safe artifact is available.

In artifact-first mode, do not open with a cleaned architecture diagram and postpone the evidence. Use this order:

```text
one testable claim
→ one original code/request/response/log artifact
→ highlight 1–2 decisive details
→ compact chain map
→ return to the same artifact and identify each mapped step
→ one reproducible action, concrete tradeoff, or transfer question
```

Prefer code and output actually read or executed in the target repository. If the upstream call, database write, or external response was simulated, label it explicitly and state which part was genuinely executed. Redact credentials and personal data without removing the fields needed to understand the protocol.

## Source Link Rules for Study Documents

When creating a persistent study document inside the same repository as the code:

- Prefer repository-relative Markdown links with GitHub/IDE line anchors:
  - Good: `[useChatFunctions.ts](../client/src/hooks/Chat/useChatFunctions.ts#L221)`
  - Good: `[request.js](../api/server/controllers/agents/request.js#L153)`
- Do not use absolute-path-plus-colon links in repository Markdown:
  - Bad: `[useChatFunctions.ts](/Users/project/repo/client/src/hooks/Chat/useChatFunctions.ts:221)`
  - Many IDEs treat `useChatFunctions.ts:221` as the literal file name and fail to open it.
- If the study document lives in a nested docs directory, compute the relative path from that document to the source file.
- In chat responses, absolute local file links with `:line` are acceptable when the host application supports them; do not copy that format into repository Markdown unless the project explicitly requires it.
- When maintaining an index/TODO document for a learning project, record this link style so later documents stay consistent.

## Annotation Depth

Use dense beginner-level comments for languages the user is learning:

- React/Next/Vue/TypeScript: explain `const`, function components, props, hooks, state setters, `useEffect`, dependency arrays, cleanup functions, async functions, `await`, `Promise.all`, destructuring, optional chaining, ternary expressions, route navigation, API calls, and how state changes affect UI rendering.
- Python/FastAPI: explain `def`, type hints, `Annotated`, `Depends`, `Query`, decorators, Pydantic models, aliases, `async`/`await`, `try`/`except`, `raise`, dataclasses, SQLAlchemy sessions, repository/service separation, and return types.
- Go/Gin: explain `package`, imports, `func`, method receivers, pointers, `gin.Context`, `:=`, `if v := ...; condition`, `value, err` patterns, `return`, interfaces, struct literals, JSON/db tags, context, repository/service separation, and SQL parameter binding.
- Java/Spring: use lighter syntax comments because the user is more familiar with Java. Focus on annotations, Controller/Service/Mapper boundaries, validation, transactionality, DTO/VO conversion, exception mapping, naming, nesting, and whether the code is practical engineering rather than over-designed.

When the user asks for "完整案例", "拆一条链路", "加大量注释学习", or similar, read `references/comment-templates.md` and follow its patterns.

Dense source comments should look like the templates: not just one high-level JSDoc above a function, but repeated `[语法]`, `[链路]`, `[注意]`, and `[工程判断]` comments around the concrete statements a beginner would otherwise have to decode.

Minimum density for **Dense beginner density**:

- Function entry: explain who calls it, what parameters mean, and what object/state it eventually produces.
- Parameter destructuring/defaults: explain destructuring, default values, optional fields, and why null/undefined matters.
- State setters and cache updates: explain which UI re-renders or downstream effects they trigger.
- Async calls and promises: explain what is awaited, what can fail, and what happens before/after the await.
- Branches and early returns: explain the business or safety reason for returning.
- Object construction: explain important fields, not just the object as a whole.
- Cross-file handoff: include the next file/function/API path the reader should follow.

## Output Modes

Choose the least invasive mode unless the user specifies otherwise:

- Chat mode: paste a complete annotated walkthrough in the conversation.
- Study document mode: create or update a markdown learning document when the user wants a persistent artifact.
- Learning-in-place mode: when the user says the checkout is for learning or project instructions allow it, add dense learning comments directly to the existing source files. Do not create a worktree for this mode.
- Learning worktree mode: create/use a dedicated worktree or branch, add dense source comments there, and keep it out of production branches.

For worktree mode, follow the repository's git/worktree rules before creating branches or editing files. Confirm current repository and branch with the required git checks if the project instructions require them.

## Quality Review

After the walkthrough, include a short engineering read:

- Is the code reasonably layered?
- Are names clear?
- Is there avoidable nesting or cleverness?
- Are there hidden coupling points?
- Where should a beginner start debugging?

Keep the review grounded in file paths and line references.
