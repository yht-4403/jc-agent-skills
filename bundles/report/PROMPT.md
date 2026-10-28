# 一键安装提示词：报告

先装「去 AI 味核心」（bundles/core/）和图先行套里的 jc-markdown-visual-writer-latest，再把下面整段复制发给你的 AI：

```text
把 https://github.com/yht-4403/jc-agent-skills 仓库里的 jc-report 这个技能装到我当前的平台：克隆仓库，把这个目录复制（或软链）到我当前平台的 skills 目录——WorkBuddy 用 ~/.workbuddy/skills/，Claude Code 用 ~/.claude/skills/，Codex 用 ~/.codex/skills/。装完告诉我它管什么，然后从现在起，我让你整理日报、周报、项目进展时按它的规则写：业务进展和验证状态为主，技术细节只留影响判断的部分。
```

装好后验证：把最近一周的工作流水发给 AI，让它出一份周报，看有没有测试计数、错误码这类不该出现的细节。
