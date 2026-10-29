---
name: jc-design-teardown
description: Use when the user asks for 前端设计拆解, 前端技术拆解, 竞品拆解, competitor website analysis, UI/UX visual study, screenshot-backed teaching docs, style extraction, color/spacing/shadow/font/motion breakdowns, Markdown research docs, or prompts for frontend AI reuse.
disable-model-invocation: true
---

# Frontend Design Teardown（前端设计拆解）

## Purpose

Create a screenshot-backed frontend teardown and teaching document for a competitor or reference page. “前端设计拆解” means breaking a page into frames, layout, colors, typography, motion, components, and reusable frontend patterns. The goal is to extract reusable UI patterns and learning notes, not to clone the site.

## Use With

- Use `impeccable-redesign-orchestrator` too when the teardown will feed a long-running redesign or prototype.
- Use `playwright-skill` or browser automation when screenshots, computed styles, scrolling behavior, or responsive checks are needed.
- In `/Users/cv-project`, follow `AGENTS.md` and put Markdown research docs under `/Users/cv-project/docs/竞品调研/`.

## Workflow

1. Confirm the target URL, page or sections, what the user likes, and what must not be copied.
2. Open the page in a browser and inspect it by sections, not just as a full-page screenshot.
3. Capture local screenshots for the meaningful blocks:
   - hero / first viewport
   - navigation
   - product demo or key conversion section
   - proof, testimonial, case, or trust section
   - motion, marquee, carousel, sticky, before/after, or other interaction
   - one or two close-up details worth teaching
4. Extract concrete visual values where possible:
   - background, text, accent, border colors
   - card surfaces, radius, shadow, opacity, backdrop
   - font family, size, weight, line-height, letter spacing
   - layout width, grid/flex behavior, spacing, aspect ratio
   - button states, focus/hover states
   - animation method, duration, easing, pause/reduced-motion behavior
5. Write a Markdown teaching doc with embedded local screenshots.
6. Update any active redesign plan with the research doc path and next action.

## Markdown Structure

Use this structure unless the user requests another format:

````md
# <Competitor> <Page> 前端视觉拆解

> 来源：<URL>，采集时间：YYYY-MM-DD。本文只拆解可复用的视觉、布局和前端实现模式，不复制竞品内容、品牌资产、文案或业务承诺。

## 0. 结论先说

## 1. 样式快照

| 设计 token | 采样值 | 作用 | 我的项目建议 |
| --- | --- | --- | --- |

## 2. <截图区块标题>

![截图说明](./local-screenshot.png)

### 观察

### 前端知识点

### 给前端 AI 的描述模板

```text
...
```

### 我的项目怎么借
````

For every screenshot section, include:

- **观察**: why the block feels polished.
- **前端知识点**: CSS, React, Tailwind, accessibility, performance, and motion concepts.
- **给前端 AI 的描述模板**: reusable prompt wording for a future frontend AI request.
- **我的项目怎么借**: how to adapt the pattern without copying.

## Naming

In `/Users/cv-project`, use:

```text
/Users/cv-project/docs/竞品调研/YYYY-MM-DD-NNN-<竞品名><页面名>视觉拆解-调研记录.md
/Users/cv-project/docs/竞品调研/YYYY-MM-DD-NNN-<竞品名><页面名>视觉拆解-01-<区块名>.png
```

If the topic already has related files, reuse the same `NNN` when appropriate. Keep screenshots beside the Markdown so relative image links render.

## Safety And Originality

- Do not copy competitor copy, images, logos, screenshots, pricing, claims, or brand assets into the user's product.
- Do not present competitor screenshots as production assets. They are research artifacts only.
- Prefer pattern language: structure, rhythm, spacing, hierarchy, proof mechanics, motion behavior, and component anatomy.
- Call out which parts are safe to borrow and which are brand-specific or legally risky.
- If using real customer screenshots later, require authorization, anonymization, and sensitive-data masking.

## Good Final Response

Keep the final response short:

- Link the Markdown doc.
- Mention the screenshot count and extracted style artifacts.
- Say whether production code changed.
- State the next recommended step, usually a hidden prototype page before production rewrite.
