---
name: jc-audio-transcriber
description: 将一个录音文件夹转成单份完整逐字稿和一篇精简知识文档；适用于 DJI Mic 等批量录音的扫描、转写、合并、质量检查与 Obsidian 归档。默认本地 Fun-ASR-Nano；用户明确要求云端时用 Qwen，点名豆包才走火山。不用于实时听写或只改写现成文字。
---

# JC Audio Transcriber

把一个输入文件夹视为一批录音。默认长期保留且只交付两个文件：完整逐字稿 TXT 和 AI 梳理后的 Markdown。

## 工作流

1. 先读取目标知识库中的 `AGENTS.md`、`CLAUDE.md` 和命名规则，再运行：

   ```bash
   python3 scripts/transcribe_folder.py inventory "<录音目录>"
   ```

2. 选择转写提供方，命令读 [references/providers.md](references/providers.md)：
   - 用户未指定：`--provider local`，模型 `FunAudioLLM/Fun-ASR-Nano-2512`，录音不离开本机。
   - 用户明确要求云端、质量优先、说话人分离，或本地质量不够：`--provider qwen`。通义听悟不是 Qwen。
   - 用户明确要求豆包 / 火山语音：`--provider doubao`（极速版 `volc.bigasr.auc_turbo`）。
   - 用户明确要求豆包 2.0 / Seed-ASR：同一提供方，加 `--doubao-resource-id volc.seedasr.auc`。
   - 未允许上传时不得改走云端。
   短片段对比和单价在 [references/asr-bakeoff-2026-08-25.md](references/asr-bakeoff-2026-08-25.md)。
3. 运行 `transcribe`。脚本把逐文件结果、断点状态和原始 JSON 放在外部缓存中，只把合并后的 TXT 写到指定位置。
4. 检查脚本生成的质量报告，并抽查开头、中间、结尾。明显乱码、重复幻觉、漏文件或空转写不能直接包装成确定结论；必要时换提供方重跑。
5. 按 [references/output-contract.md](references/output-contract.md) 生成最终 TXT 文件名。
6. 读取并调用同级 `../jc-knowledge-capture/SKILL.md`。根据逐字稿的实际信息密度选择轻量或标准沉淀；用户临时指定文风或用途时按其要求路由。
7. 最终 Markdown 与 TXT 使用相同主题，保存到用户指定目录；默认目录是 `~/Documents/JC知识库/06-录音转写`。

## 不可破坏的边界

- 不移动、不删除、不改写源录音；云端临时对象只在结果已经保存后删除。
- 不把 `._*`、旧 TXT、JSON、SRT、VTT、Markdown 或历史整理稿当作输入。
- 按文件名内的录制时间排序；没有时间时才使用修改时间。
- 每个被发现的音频都必须有完成、无有效语音或失败状态。极短录音只能标记，不能静默丢弃。
- 逐字稿不经过 LLM 改写；只允许供应商标点、时间戳、说话人标签、文件边界和必要的空白规范化。
- 不长期保存逐文件 TXT、供应商 JSON、SRT、VTT 或运行日志到知识库。
- 不把 API Key 写入 Skill、知识库、逐字稿或日志。
- 转写不完整时，不得声称已经交付“完整逐字稿”。

## 交付检查

- 一个输入文件夹对应一对最终文件。
- TXT 覆盖清单中的全部音频，文件顺序与录制时间一致。
- Markdown 不复制大段逐字稿，只保留值得回顾的背景、判断、过程、结论和确有依据的下一步。
- 材料价值较低时，Markdown 简短说明内容概览和未深入沉淀的原因，不强行总结方法论。
- 最终回复只说明两份产物路径、使用的转写提供方和具体模型、知识沉淀模式和仍存在的质量限制。
