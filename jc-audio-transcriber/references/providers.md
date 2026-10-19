# 转写提供方

只在实际选择对应提供方时读取本文件。2026-08-25 短片段证据见 [asr-bakeoff-2026-08-25.md](asr-bakeoff-2026-08-25.md)。

## 选择规则

- 用户未指定：`--provider local`。默认模型 `FunAudioLLM/Fun-ASR-Nano-2512`。录音不离开本机。
- 用户明确说云端、质量优先、说话人分离，或本地质量不够：`--provider qwen`。通义听悟不是 Qwen，禁止拿 `TINGWU_*` 冒充。
- 用户明确说豆包、火山语音、volc：`--provider doubao`（极速版）。
- 用户明确说豆包 2.0、Seed-ASR：`--provider doubao --doubao-resource-id volc.seedasr.auc`。
- 未允许上传时不得改走云端。云端缺凭据时停止云端调用，保留已有本地结果并准确报告。
- A/B 只截短片段，不整批重复计费。

后付费单价（2026-08 官方标价，按音频时长）：Qwen 北京 `qwen-audio-3.0-asr-flash-filetrans` 约 0.79 元/小时；豆包 2.0 约 0.8 元/小时；豆包极速版约 4.5 元/小时。云端次选 Qwen，不因为豆包极速版专名略好就默认走更贵的通道。

## 本地 Fun-ASR-Nano

适合不允许录音离开本机，以及中文、中英混杂和中文方言。

```bash
python3 scripts/transcribe_folder.py transcribe "<录音目录>" \
  --provider local \
  --output "<完整逐字稿.txt>"
```

运行要求：`uv` 隔离安装 `funasr==1.4.3`、`torch`、`torchaudio`、`modelscope`；`ffmpeg`。Apple Silicon 优先 MPS。模型缓存在 `~/.cache/modelscope/`。Nano 没有可靠字级时间戳，脚本用 FSMN-VAD 分段。嘈杂、多人远场仍要抽查。

## 豆包录音文件识别

同一把 `VOLC_SPEECH_API_KEY`，两条通道。只有用户点名豆包才走这里；云端默认是 Qwen。

### 极速版（默认）

- 接口：`POST https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash`
- 资源：`volc.bigasr.auc_turbo`
- 请求体模型名：`bigmodel`
- 限制：不超过 2 小时、100MB

DJI 原文件常超过 100MB，脚本先转成 16 kHz 单声道 WAV；约 6 分钟以内走 base64，更长则经 MinIO 预签名 URL。

```bash
python3 scripts/transcribe_folder.py transcribe "<录音目录>" \
  --provider doubao \
  --env-file "<配置文件>" \
  --output "<完整逐字稿.txt>"
```

### 标准版 2.0

- 接口：`POST .../bigmodel/submit` 与 `.../bigmodel/query`
- 资源：`volc.seedasr.auc`（Doubao-Seed-ASR-2.0）
- 限制：不超过 5 小时、512MB
- 必须 MinIO 预签名 URL；有说话人标签

```bash
python3 scripts/transcribe_folder.py transcribe "<录音目录>" \
  --provider doubao \
  --doubao-resource-id volc.seedasr.auc \
  --env-file "<配置文件>" \
  --output "<完整逐字稿.txt>"
```

同一批 150 秒对比里，极速版专名更稳，2.0 去掉了 `141` 循环并带说话人，但把领星听成「李欣」。不要因为 2.0 更新就自动替换默认。

需要的配置：

```text
VOLC_SPEECH_API_KEY=
VOLC_SPEECH_RESOURCE_ID=volc.bigasr.auc_turbo
VOLC_SPEECH_UID=jc-audio-transcriber

MINIO_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=
MINIO_REGION=us-east-1
MINIO_PRESIGN_HOURS=12
```

短文件走极速版可以没有 MinIO。标准版和长文件没有 MinIO 时停止并说明，不要改回静默本地。

官方参考：

- https://www.volcengine.com/docs/6561/1631584
- https://www.volcengine.com/docs/6561/1354868

## Qwen Audio 文件转写

适合长录音、多人谈话、需要说话人分离。2026-08-25 测试模型：

```text
qwen-audio-3.0-asr-flash-filetrans
```

官方接口接受公网文件 URL，单次一个文件。脚本复用 S3/MinIO 临时上传、异步轮询和断点状态；结果下载完成后默认删除临时对象。

```bash
python3 scripts/transcribe_folder.py transcribe "<录音目录>" \
  --provider qwen \
  --env-file "<配置文件>" \
  --diarization \
  --output "<完整逐字稿.txt>"
```

需要的配置：

```text
DASHSCOPE_API_KEY=
DASHSCOPE_WORKSPACE_ID=              # 可选；为空时使用兼容旧域名
DASHSCOPE_REGION=cn-beijing
QWEN_ASR_MODEL=qwen-audio-3.0-asr-flash-filetrans

MINIO_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=
MINIO_REGION=us-east-1
MINIO_PRESIGN_HOURS=12
```

脚本按顺序查找配置：

1. `--env-file`；
2. `JC_AUDIO_TRANSCRIBER_ENV` 指定的文件；
3. `~/.config/jc-audio-transcriber/.env`；
4. 当前机器上的旧项目 `~/dji-audio-transcriber/.env`，仅作迁移兼容。

环境变量优先于文件值。不得把密钥写入 Skill、知识库、逐字稿或日志。

可重复使用 `--hotword "词语=5"` 增加即时热词；可用 `--speaker-count 2` 给出人数提示。默认关闭系统敏感词替换，以尽量保留完整原话。

官方参考：

- https://help.aliyun.com/zh/model-studio/non-realtime-speech-recognition-user-guide
- https://help.aliyun.com/en/model-studio/fun-asr-recorded-speech-recognition-http-api
