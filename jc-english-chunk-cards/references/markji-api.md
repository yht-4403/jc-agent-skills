# 墨墨记忆卡写入

生产：`https://open.maimemo.com/open`

鉴权：`Authorization: Bearer $MAIMEMO_TOKEN`

Token 在 https://www.markji.com/ 获取或更换，写入本 Skill 目录 `.env` 的 `MAIMEMO_TOKEN=`。读取顺序：先环境变量 `MAIMEMO_TOKEN`，没有再读 `.env`。`.env` 已 gitignore，不要写进 `SKILL.md`、对话笔记或 git。`scripts/markji_upload.py` 会自己加载。

这是记忆卡接口，不是背单词。背单词 Token 若对 `/api/v1/markji/decks` 返回 403，去记忆卡 App 开通开放能力后再试，不要改写云词本。

## 实测约定

- 列牌组：`GET /api/v1/markji/decks?limit=20&offset=0`
- 章节：`GET /api/v1/markji/decks/{deck}/chapters?with_cards=true`
- 建卡：`POST /api/v1/markji/decks/{deck}/chapters/{chapter}/cards`
- 改卡：`POST /api/v1/markji/decks/{deck}/cards/{card}`
- 建卡/改卡的 JSON **只含** `{"card":{"content":"...","grammar_version":3}}`。body 里不要带 `deck`/`chapter`，否则 `not a valid ObjectId`。
- `grammar_version` 只接受 2 或 3，用 3。
- 不能用 API 建牌组、建章节、删卡片。
- 写入不等于加入学习。

脚本：`scripts/markji_upload.py`。
