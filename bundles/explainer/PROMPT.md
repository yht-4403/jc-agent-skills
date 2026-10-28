# 一键安装提示词：通俗讲解

先装「去 AI 味核心」（bundles/core/），再把下面整段复制发给你的 AI：

```text
把 https://github.com/yht-4403/jc-agent-skills 仓库里的 jc-plain-explainer 这个技能装到我当前的平台：克隆仓库，把这个目录复制（或软链）到我当前平台的 skills 目录——WorkBuddy 用 ~/.workbuddy/skills/，Claude Code 用 ~/.claude/skills/，Codex 用 ~/.codex/skills/。装完告诉我它管什么，然后从现在起，我问机制、原理、流程类问题时按它的规则讲：用一个具体对象走完一遍真实过程，术语第一次出现给一句人话解释。
```

装好后验证：问一个一直觉得抽象的机制（比如「HTTPS 握手」「幂等」），看它是不是用具体例子带你走完。
