# jc-agent-skills

27 个 Agent Skill，各自管一类具体问题。不用懂原理，按你遇到的问题选一套，复制提示词发给你的 AI，它自己装好。

![27 个技能按问题分成的八套](assets/repo-map.svg)

## 按问题选一套

### AI 说话假、回复一大段看不懂：易读输出套

- [`jc-no-ai-flavor-latest`](jc-no-ai-flavor-latest/)：AI 回复又长又假、看着累，所以做了它。管结论先行、篇幅和文味，目标是 30 秒看懂一条回复。
- [`jc-markdown-visual-writer-latest`](jc-markdown-visual-writer-latest/)：纯文字看不懂、想先看图，所以做了它。用 Mermaid 把流程和结构画出来。

这套是其他几套的底座，建议第一个装。

```text
克隆 https://github.com/yht-4403/jc-agent-skills ，把 jc-no-ai-flavor-latest、jc-markdown-visual-writer-latest 这两个目录复制到我当前平台的 skills 目录（WorkBuddy 是 ~/.workbuddy/skills/，Claude Code 是 ~/.claude/skills/，Codex 是 ~/.codex/skills/）。装完告诉我每个管什么，从下一条回复起按 jc-no-ai-flavor-latest 的规则输出。
```

验证：随便问个复杂问题，看它是不是先给结论、段落变短。

### 做产品先理体验流程：产品体验套

我们的理念：先把用户体验流程梳理清楚，所有流程想明白了，再进入详细开发和决策。

- [`about-face-4`](about-face-4/)：Cooper 的目标导向设计，动手前把目标、场景、体验流程想清楚。
- [`shape-dev-requirements`](shape-dev-requirements/)：开发对接前，把业务背景、目标和关键约束问透。
- [`jc-frontend-uiux`](jc-frontend-uiux/)：进入设计后，先定设计预算，生成后照清单自查。
- [`jc-frontend-workflow`](jc-frontend-workflow/)：整体重设计时，先出独立原型，再分批迁入正式代码。

```text
克隆 https://github.com/yht-4403/jc-agent-skills ，把 about-face-4、shape-dev-requirements、jc-frontend-uiux、jc-frontend-workflow 这四个目录复制到我当前平台的 skills 目录（WorkBuddy 是 ~/.workbuddy/skills/，Claude Code 是 ~/.claude/skills/，Codex 是 ~/.codex/skills/）。装完告诉我每个管什么。
```

验证：让它做一个页面，看它是不是先问目标和用户流程，而不是直接甩代码。

### 复杂机制听不懂：通俗讲解套

- [`jc-plain-explainer`](jc-plain-explainer/)：问机制原理时 AI 净说术语，所以做了它。它用一个具体例子带你走完一遍真实过程。
- [`jc-html-lecture`](jc-html-lecture/)：听完想留一份能标注、能补充的讲解页，所以做了它。

先装易读输出套。

```text
克隆 https://github.com/yht-4403/jc-agent-skills ，把 jc-plain-explainer、jc-html-lecture 这两个目录复制到我当前平台的 skills 目录（WorkBuddy 是 ~/.workbuddy/skills/，Claude Code 是 ~/.claude/skills/，Codex 是 ~/.codex/skills/）。装完告诉我每个管什么，之后我问机制原理时按它们的规则讲。
```

验证：问一个一直觉得抽象的机制，比如「HTTPS 握手」，看它是不是用具体例子讲。

### 要系统学一个陌生领域：学习套

- [`jc-learning-map`](jc-learning-map/)：面对陌生领域不知道从哪下手，所以做了它。先给你画一张知识地图，标出卡点和第一步。
- [`jc-learning`](jc-learning/)：地图有了想逐个深入，所以做了它。

```text
克隆 https://github.com/yht-4403/jc-agent-skills ，把 jc-learning、jc-learning-map 这两个目录复制到我当前平台的 skills 目录（WorkBuddy 是 ~/.workbuddy/skills/，Claude Code 是 ~/.claude/skills/，Codex 是 ~/.codex/skills/）。装完告诉我每个管什么。
```

验证：让它给一个陌生领域画学习地图，看是不是先出全景再讲细节。

### 写文案、发内容：写作套

- [`jc-voice`](jc-voice/)：AI 写的东西不像你写的，所以做了它。仓库里是脱敏示例，把手写原文换进 references/ 才有完整效果。
- [`jc-site-copy`](jc-site-copy/)：官网、落地页文案写出来没重点，所以做了它。
- [`jc-knowledge-capture`](jc-knowledge-capture/)：对话和灵感散在各处，想整理成能回顾的文档，所以做了它。
- [`jc-daily-thought-social-publisher-v5`](jc-daily-thought-social-publisher-v5/)：长文想改成社媒能发的短文，所以做了它。

```text
克隆 https://github.com/yht-4403/jc-agent-skills ，把 jc-voice、jc-site-copy、jc-knowledge-capture、jc-daily-thought-social-publisher-v5 这四个目录复制到我当前平台的 skills 目录（WorkBuddy 是 ~/.workbuddy/skills/，Claude Code 是 ~/.claude/skills/，Codex 是 ~/.codex/skills/）。装完告诉我每个管什么、什么时候触发。
```

### 日报周报、工作对接：工作套

- [`jc-report`](jc-report/)：周报写出来全是技术细节、领导看不懂，所以做了它。
- [`jc-work-coordination`](jc-work-coordination/)：情况说明发出去对方不知道要干嘛，所以做了它。
- [`jc-decision-grade`](jc-decision-grade/)：方案讨论半天没人敢拍板，所以做了它。
- [`jc-project-loop`](jc-project-loop/)：长项目跨好几次对话，每次都从头讲，所以做了它。

先装易读输出套。

```text
克隆 https://github.com/yht-4403/jc-agent-skills ，把 jc-report、jc-work-coordination、jc-decision-grade、jc-project-loop 这四个目录复制到我当前平台的 skills 目录（WorkBuddy 是 ~/.workbuddy/skills/，Claude Code 是 ~/.claude/skills/，Codex 是 ~/.codex/skills/）。装完告诉我每个管什么。
```

验证：把一周的工作流水发给它出周报，看有没有测试计数、错误码这类不该出现的细节。

### 调研公司、整理录音、给复杂问题找答案：调研套

- [`jc-find-standard-answer`](jc-find-standard-answer/)：遇到一个复杂问题，想知道这个领域历史上最好是怎么解的，所以做了它。先挖可信理论，再对照成功、失败和反例，给出带条件的标准答案。
- [`jc-company-research`](jc-company-research/)：调研一家公司越查越散，所以做了它。先定这次调研支撑什么输出，再倒推查多深。
- [`jc-audio-transcriber`](jc-audio-transcriber/)：一堆录音想变成能搜的文字，所以做了它。依赖本地 ASR 工具链，装前看它 SKILL.md 里的环境要求。

```text
克隆 https://github.com/yht-4403/jc-agent-skills ，把 jc-find-standard-answer、jc-company-research、jc-audio-transcriber 这三个目录复制到我当前平台的 skills 目录（WorkBuddy 是 ~/.workbuddy/skills/，Claude Code 是 ~/.claude/skills/，Codex 是 ~/.codex/skills/）。装完告诉我每个管什么、需要什么环境。
```

### 想自己写 skill：技能工程套

- [`jc-skills-creator`](jc-skills-creator/)：想写 skill 但不知道值不值得写、怎么写，所以做了它。
- [`jc-skill-installer`](jc-skill-installer/)：skill 多了管不过来，所以做了它。

```text
克隆 https://github.com/yht-4403/jc-agent-skills ，把 jc-skills-creator、jc-skill-installer 这两个目录复制到我当前平台的 skills 目录（WorkBuddy 是 ~/.workbuddy/skills/，Claude Code 是 ~/.claude/skills/，Codex 是 ~/.codex/skills/）。装完告诉我每个管什么。
```

### 单件工具

这几个单独装就有用：

- [`jc-bookmarks`](jc-bookmarks/)：浏览器收藏夹攒了几千条没法用，所以做了它。
- [`jc-english-chunk-cards`](jc-english-chunk-cards/)：学英语不想背单词书，想把日常语料做成卡片，所以做了它。
- [`jc-quiet-ad`](jc-quiet-ad/)：想做不像广告的品牌广告，所以做了它。
- [`jc-client-howto-guide`](jc-client-howto-guide/)：产品交付了客户不会用，所以做了它。
- [`jc-concept-deconstruct`](jc-concept-deconstruct/)：读完文章、课程想拆成能用的概念，所以做了它。
- [`jc-rich-doc-publisher`](jc-rich-doc-publisher/)：文章要发给客户或对外展示，想一键变成飞书、腾讯文档里排版好看的格式，所以做了它。依赖飞书 CLI 和腾讯文档 MCP，装前需要这两个工具。

## 想全装

```text
克隆 https://github.com/yht-4403/jc-agent-skills ，把仓库里 jc- 开头的技能目录全部复制（或软链）到我当前平台的 skills 目录（WorkBuddy 是 ~/.workbuddy/skills/，Claude Code 是 ~/.claude/skills/，Codex 是 ~/.codex/skills/）。装完列出装了哪些、各自什么时候触发。
```

## 附录：本地还收集了什么

除了上面 27 个 jc 系 skill，本地库还收了约 200 个。按类整理，本体都在仓库里，点链接就能看：

| 类别 | 解决什么 | 数量 | 代表 |
| --- | --- | --- | --- |
| [gingiris 增长实战手册](gingiris-skills/) | 增长全链路 SOP：UGC 矩阵、用户访谈、SEO/GEO、KOL 投放、Product Hunt 发布、GTM | 61 | gingiris-ugc-matrix、gingiris-user-interview |
| [dbskill 内容方法论](dbskill/) | 内容创作、传播、拆解的成套打法 | 35 | dbs、dbs-deconstruct |
| [Matt Pocock 工程实践](mattpocock-skills/) | TS 和前端工程：TDD、代码评审、调试 | 17 | tdd、code-review |
| 营销增长套件 | 转化优化、SEO、邮件、定价、广告 | 32 | [pricing-strategy](pricing-strategy/)、[seo-audit](seo-audit/) |
| 工程类 | 架构、后端、测试、部署 | 21 | [clean-architecture](clean-architecture/)、[playwright-skill](playwright-skill/) |
| 设计类 | 品牌、配色、界面评审 | 19 | [better-colors](better-colors/)、[impeccable](impeccable/) |
| GSAP 官方 | 网页动画 | 8 | [gsap-core](gsap-core/) |
| [广智销售宇宙](guangzhi-b2b-sales/) | B2B 销售全流程：商机跟进、通话复盘、100 场景话术 | 4 | guangzhi-b2b-sales、sales-script-system |

广智销售宇宙是我们用开源的 [`multi-source-skill-forge`](multi-source-skill-forge/)（炼技 SkillForge）把《广智销售宇宙》整本书蒸馏出来的：喂书进去，产出带原文依据、可独立调用、能压力测试的成套技能。想蒸馏自己的书、课程或播客，装它。

来源说明：Matt Pocock 系列原版在 GitHub（mattpocock/skills），GSAP 是官方技能，其余为社区收集，部分原作者不明。

## 这些 skill 是怎么做出来的

做法只有一条主线：先把要解决的问题说清楚，再让 AI 去找这个专业领域历史上最好的解法——谁解决过、用什么理论、用什么工具，然后一比一复刻，详细到他们用什么工具我们就用什么工具。比如复刻一个人的语言习惯，就去找语言修辞学和刑侦语言鉴定的底层论文，而不是凭感觉总结。

做出来之后不算完：写正例反例，跑多轮机器评测，按 V1、V2、V3 加 latest 的版本管理一路迭代，直到在日常工作里稳定好用。

这条主线的每一步自己都固化成了 skill，也在仓库里：

- [`jc-find-standard-answer`](jc-find-standard-answer/)：负责「找这个领域历史上最好的解法」这一步，挖理论、对照成功失败反例、给带条件的答案。
- [`jc-skills-creator`](jc-skills-creator/)：负责「把它写成一个值得存在的 skill」这一步，含正例反例和评测怎么跑。
- [`jc-skill-installer`](jc-skill-installer/)：负责版本管理和多平台同步，V1、V2 加 latest 的迭代靠它落地。

安装提示词见上面的「调研套」和「技能工程套」。

## License

[MIT](LICENSE)
