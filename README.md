# jc-skills

**我在真实工作里每天在用的一套 Agent Skills。18 个技能，覆盖写作与表达、学习与研究、工作协作、技能工程和前端设计。**

A collection of 18 [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) I use in my actual daily work — writing, research, learning, coordination, and frontend design.

---

## 这是什么

Agent Skill 是给 AI Agent 加载的能力包：一份 `SKILL.md` 说明**什么时候该用、怎么做**，配 `references/` 放按需读取的细节，`scripts/` 放确定性执行，`evals/` 放回归用例。它只在相关时进入上下文，因此比把一堆规则长期塞进系统提示词更容易维护和迭代。

这个仓库不是教程合集，是我自己的工具库。每一条都来自一次真实的失败或返工——某个任务模型做不好，我写了规则；规则太长，我拆成 references；规则需要稳定输出，我改成脚本；改完之后用 evals 确认没退化。

## 三个用途

1. **跨平台同步源。** 我在 Claude Code、Codex、WorkBuddy、CodeBuddy、Gemini、Kimi Code 之间切换，各平台的 skills 目录互相独立。这里是唯一事实源，其余全部软链过来，改一处、处处生效。
2. **方法论样本。** 如果你也在写 Agent Skill，这里能看到边界怎么写、上下文怎么分层、评估怎么设计。
3. **作品集。** 它记录了我怎么把一个模糊的工作要求，编译成 Agent 能稳定执行的东西。

## 技能清单

### 写作与表达

| 技能 | 解决什么问题 |
| --- | --- |
| [`jc-voice`](jc-voice/) | 个人写作嗓音系统。三种嗓音按场景三选一：说明嗓、主理人暖嗓、dbs 冷嗓。写对外说明和对用户说话的内容时用 |
| [`jc-site-copy`](jc-site-copy/) | 中文官网、落地页、定价页和界面文案。先判断页面类型，再按字数预算写 |
| [`jc-knowledge-capture`](jc-knowledge-capture/) | 把对话、灵感、方案整理成可回顾的知识文档，或转成适合公开发布的直述体 |
| [`jc-daily-thought-social-publisher-v5`](jc-daily-thought-social-publisher-v5/) | 把知识库长文改成单主题社媒文案 |
| [`jc-markdown-visual-writer`](jc-markdown-visual-writer/) | 用图、表、清单把复杂的 Markdown 内容讲清楚 |
| [`jc-concept-deconstruct`](jc-concept-deconstruct/) | 把文章、课程、论文按固定结构拆成概念字典、案例拆解和商业化判断题 |

### 学习与研究

| 技能 | 解决什么问题 |
| --- | --- |
| [`jc-learning`](jc-learning/) | 地图先行的工具箱学习法。先出 8–12 个思维工具的全景地图，再逐讲深入 |
| [`jc-learning-map`](jc-learning-map/) | 为陌生领域画可行动的知识地图，标注卡点和第一步 |
| [`jc-english-chunk-cards`](jc-english-chunk-cards/) | 把日常语料拆成语义块，制卡并写入墨墨背单词牌组 |
| [`jc-audio-transcriber`](jc-audio-transcriber/) | 把录音文件夹批量转成逐字稿加一份精简知识文档 |
| [`jc-company-research`](jc-company-research/) | 公司调研的倒推法。先定这次调研支撑哪个输出，再倒推查什么、查多深、什么算够了 |

### 工作与协作

| 技能 | 解决什么问题 |
| --- | --- |
| [`jc-report`](jc-report/) | 日报、周报、月报、阶段总结的统一规范，写清结论、进展、验证和风险 |
| [`jc-work-coordination`](jc-work-coordination/) | 把情况说明改成能直接发出去的工作对接消息，按接收人职责保留行动和必要事实 |
| [`jc-project-loop`](jc-project-loop/) | 用本地任务账本持续推进、复核和恢复跨会话的长周期项目 |
| [`jc-rich-doc-publisher`](jc-rich-doc-publisher/) | 把长内容做成适合手机和电脑阅读的富文档，并处理云文档的协作、权限和发布后校验 |

### 技能工程

| 技能 | 解决什么问题 |
| --- | --- |
| [`jc-skills-creator`](jc-skills-creator/) | 创建、审查、迭代带明确边界和评估的 Agent Skill。先证明它该存在，再动手写 |
| [`jc-skill-installer`](jc-skill-installer/) | 搜索、安装、启停、去重、版本管理并同步个人 Skill 库到 9 个 Agent 平台 |

### 前端与设计

| 技能 | 解决什么问题 |
| --- | --- |
| [`jc-frontend-uiux`](jc-frontend-uiux/) | 前端界面设计纪律。动手前先写设计预算，生成后做冗余、层次、颜色三组自查，诊断观感问题时先量化再改 |

## 快速开始

```bash
git clone https://github.com/yht-4403/jc-agent-skills.git
cd jc-agent-skills
cd ~/Code/jc-skills

# 软链到你实际在用的平台，不需要的行删掉即可
for dir in ~/.claude/skills ~/.codex/skills ~/.workbuddy/skills ~/.codebuddy/skills; do
  mkdir -p "$dir"
  for s in jc-*/; do
    ln -sfn "$PWD/${s%/}" "$dir/${s%/}"
  done
done
```

各平台 skills 目录：

| 平台 | 目录 |
| --- | --- |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| WorkBuddy | `~/.workbuddy/skills/` |
| CodeBuddy | `~/.codebuddy/skills/` |
| Gemini / Antigravity | `~/.gemini/config/skills/` |
| DeepSeek Harness | `~/.dsh/skills/` |
| Kimi Code | `~/.kimi-code/skills/` |
| Grok | `~/.grok/skills/` |

只想用某一个，直接 `cp -r jc-report ~/.claude/skills/` 也可以。

## 一个技能长什么样

以 `jc-company-research` 为例：

```text
jc-company-research/
├── SKILL.md                  # 触发条件、边界、主流程
├── references/
│   ├── research-protocol.md  # 调研的完整步骤
│   ├── evidence-layers.md    # 证据分层：什么算查到
│   ├── stage-inference.md    # 从公开信息推公司阶段
│   ├── scenario-reverse-lookup.md
│   ├── spoken-script.md      # 交付物的口播结构
│   └── delivery-contract.md
├── evals/cases.md            # 回归用例
└── agents/openai.yaml        # 跨平台元数据与调用策略
```

原则是 `SKILL.md` 只放主干和路由，细节沉到 `references/` 按需读取——避免每次触发都吃掉一大块上下文。

## 设计原则

这几条是写这些技能时反复吃过亏之后定下来的，`jc-skills-creator` 里有完整版本：

**先证明该存在，再写。** 新增之前先问：模型没有这个技能时是不是已经做得好？一句临时提示够不够？问题是不是只是确定性重复执行、应该写脚本？只有都能否掉，才值得做成技能。

**边界写成否定句。** 每个技能的 description 都写明「不用于什么」。`jc-voice` 明确不用于简历正文和官网文案，`jc-report` 明确不用于原始笔记和会议纪要。不写否定边界的技能会被错误触发，然后污染输出。

**证据优先于措辞。** 没有材料支撑的判断不写进去；不确定的部分标成待核实，而不是用确定的语气糊过去。`references/claims-and-evidence.md` 专门管这条。

**确定性的交给脚本，判断留给模型。** 文件名解析、目录扫描、接口调用这类事情写进 `scripts/`，不让模型每次自由发挥；需要权衡的部分才留给判断。

**用评估回归，不靠感觉。** 改完技能要跑 `evals/`，确认原本能过的用例没退化。`jc-work-coordination` 的 `evals/` 里保留了带 sha256 的运行结果，可以对照。

## 关于个人绑定

需要说清楚：这些技能是按**我自己的工作环境**写的，不是通用产品。

一部分技能会读写我个人的知识库结构（`jc-report` 写日记、`jc-learning` 读学习地图），一部分绑定个人文风（`jc-voice`），一部分依赖本地工具链（`jc-audio-transcriber` 依赖本地 ASR）。直接装到你的环境里，触发可能正常，但输出会指向不存在的东西。

**所以建议把它当方法论参考读，而不是当插件装。** 想复用的部分，抄结构、改路径、换掉个人设定，比直接拿来用更靠谱。这也是我把它开源而不是发到技能市场的原因——市场形态适合分发标准化能力，不适合分发一个高度个人化的工作流。

另外说明两点处理方式：

- `jc-voice` 里用于校准语感的原文锚点，在这个仓库中替换成了**虚构示例**。它的约束力来自"这句话真的被人确认过"，虚构示例只能示范结构。你自己用时，把手写原文替换进 `references/` 才有完整效果。
- `jc-skill-installer` 的机器级状态文件（`active-skills.json` 等）**不版本化**。它们记录本机技能清单和绝对路径，换机器时要重新 `bootstrap`。

## 更新方式

这是活仓库。我在用的过程中发现规则失效或输出退化，就会直接改，然后把失败案例补进对应的 `evals/`。所以提交历史比 README 更能说明问题。

日常的编辑发生在本地 Skill 库里，不直接在这个仓库里改。仓库只保留技能本体，运行时状态文件（`active-skills.json`、`skill-channels.json` 之类）留在库里，不进 git——否则每次安装或启停技能都会产生无意义的提交。发布时用 [`scripts/sync-from-library.sh`](scripts/sync-from-library.sh) 单向同步过来：

```bash
./scripts/sync-from-library.sh            # 同步并查看变更
./scripts/sync-from-library.sh --commit   # 同步并提交
```

脚本会排除 `.env`、`__pycache__`、`.pyc`，并对「仓库里有、库里已没有」的技能只提示不自动删。这个脚本是作者自用，但如果你也是「本地库 + 发布仓库」两层的结构，把 `JC_SKILL_LIB` 指向自己的库就能直接复用。

## License

[MIT](LICENSE)
