---
name: jc-english-chunk-cards
description: 把用户日常中文、英文对话、网页、截图或知识库过往文案拆成语义块，制成墨墨记忆卡并写入指定牌组。用于「丢一段工作英语给我」「写进记忆卡」「按 chunk 制卡」「从日常思考抽英语」「和外国人商务洽谈怎么说」「面试自我介绍英语」。空调用、只说「今天的」或「从聊天里抽」时，从当天 Grok 会话用户原文抽一个主题再制卡。从知识库抽句时只做一个主题，按把话说完需要的深度出连贯开口链，不套固定张数。不用于雅思/四六级词表、墨墨背单词云词本、知识库沉淀、改简历投递，或只问 Markji 制卡语法。
---

# JC English Chunk Cards

把日常材料做成「正面整句英文、背面语义块」的记忆卡，写入墨墨记忆卡。不是背单词，也不是中译英默写。

## 首次回复

当前对话第一次触发时，读取 [首次说明](onboarding/core-introduction.md)，按用户语言输出，然后立刻拆材料。后续不重复介绍。

材料已经是一句中文、英文、聊天或截图时，介绍完直接制卡并上传。用户没贴材料、只调用本 Skill、或说「今天的 / 从聊天里抽」时，走空调用：读取 [从对话抽条](references/harvest.md)，跑 `harvest_today.py`，再按 [抽哪些句子](references/pick-scenes.md) 制卡。点名知识库、日常思考或过往文案时，读该材料并按同一份场景规范抽句。环境变量和 Skill 目录 `.env` 都没有 Token 时才问 `MAIMEMO_TOKEN`，获取地址见 [记忆卡接口](references/markji-api.md)。不要先要词表、牌组清单或确认页。

## 边界

做：

- 从日常材料抽出完整英文句并切语义块；
- 按本 Skill 模板写成记忆卡；
- 写入用户自建牌组，默认名称 `英语`。

不做：

- 雅思 / 四六级 / BEC 词表 → 不制卡；
- 墨墨背单词云词本、`add_words`、提交认识/模糊；
- 知识库沉淀 → `jc-knowledge-capture`；
- 改简历、投递策略、JD 定制 → 简历类技能；用自我介绍和过往经历练开口英文仍走本 Skill；
- 只问 Markji 标签语法、不给学习材料。

## 工作流程

1. **抽句**  
   已贴原句：一句一卡。中文先译成美国人会说的句子。一段话拆成多张，不塞进一张，不套场景比例。  
   从知识库、日常思考、过往文案或对话抽条：读取 [抽哪些句子](references/pick-scenes.md)。只做一个主题，按把话说完需要的深度出连贯开口链；用户指定场景则整批按该类。  
   无材料：先 `python3 scripts/harvest_today.py --days 1`，按 [从对话抽条](references/harvest.md) 和 [抽哪些句子](references/pick-scenes.md) 抽句，列出正面再上传。

2. **切块与排版**  
   读取 [切块](references/chunking.md) 和 [卡片模板](references/card-template.md)。正面纯英文；背面才分块。顺序从左到右往下加，不从句尾倒读，不拆主谓宾。

3. **写入**  
   读取 [记忆卡接口](references/markji-api.md)。Token 先读环境变量 `MAIMEMO_TOKEN`，没有再读本 Skill 的 `.env`。不要把 Token 写进 `SKILL.md` 或 git。运行：

   ```bash
   python3 scripts/markji_upload.py --deck 英语 --file <cards.json>
   ```

   JSON 为 `[{"content":"..."}]`。`grammar_version` 由脚本固定为 3。

4. **交付**  
   报告主题、这条链覆盖哪些环节、张数、牌组名和每张正面。提醒在 App 里加入学习。失败则给出 HTTP 码和 `errors`。

## 核心 Gotchas

- 建卡 body 不要带 `deck`/`chapter`，否则 `not a valid ObjectId`。
- `grammar_version` 用 3；1 会报无效 GV。
- `/markji/decks` 返回 403 是记忆卡开放能力未开通，不要改走背单词接口。
- 正面写中文或 `/` 分块，就测不到秒懂。
- 学习圈词必须给日常替换，否则用户会把 spaced review 说出口。

## 停止

材料是沉淀、改简历投递或考纲刷词时停止制卡并转交。Token 缺失只问这一项。牌组不存在时列出已有名称，不擅自新建（API 也不能建牌组）。
