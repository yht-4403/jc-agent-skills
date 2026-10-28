---
name: jc-skill-publisher
description: 把本地库里的一个或多个 skill 发布到开源仓库 yht-4403/jc-agent-skills。固定五步——隐私扫描、复制清理、归类上架、更新 README 和地图、提交推送；发布后做本地版本归档。用户说「发布这个 skill」「推到 GitHub」「上架这套」时使用。不管本地库的启停和安装（归 jc-skill-installer），不做全量同步，不写新 skill（归 jc-skills-creator）。
---

# JC Skill Publisher

把本地 skill 发布到开源仓库。流程固定，判断留给人的只有两处：含个人信息的内容能不能发、第三方的东西有没有权利发。

## 仓库事实

- 远程：`git@github.com:yht-4403/jc-agent-skills.git`
- 本地克隆：没有就克隆到当前工作区，有就 `git pull` 后再动
- 结构：自研 skill 在根目录（jc- 前缀），收录合集也放根目录（gingiris-skills/、dbskill/ 等保持原目录结构）
- 主区八套和附录类别写在 README 里，新增类别先和人确认

## 固定流程

### 1. 隐私扫描（不通过就停）

对待发布目录逐项查：

- `grep -rn "/Users/"`：本机绝对路径，全部改成 `~/` 或通用写法
- `grep -rni "token\|apikey\|api_key\|secret\|密码"`：命中逐条人工判断
- 个人文案、真实客户信息、内部系统名：命中就停下来问人
- 垃圾文件必删：`.DS_Store`、`__pycache__`、`node_modules`、`.env*`

注意：description 是多行写法时单行 grep 会误判成「空描述」，判废弃前必须打开文件看。

### 2. 复制进仓库

复制整个 skill 目录进仓库克隆，删掉上一步的垃圾文件。合集类（如 gingiris-skills）保持原目录结构整个拷。

### 3. 归类上架

- 自研 jc 系：决定进主区八套的哪一套，或单件工具
- 收录的第三方：进附录对应类别，新类别先和人确认
- 归属说不清就问，不猜

### 4. 更新 README 和地图

每加一个 skill，检查五处：

1. 开头计数（自研 N 个 + 收录 M 个）
2. 所属套件的 bullet 列表（一句话「遇到什么问题所以做了它」）
3. 该套件的安装提示词里的目录清单
4. 附录表格的数量和代表（收录类）
5. `assets/repo-map.svg` 的根节点计数，结构变了才改分支

### 5. 提交推送 + 本地归档

- commit message 写清干了什么：加了什么、改了哪几处
- push 后确认远程更新成功
- 本地版本管理：现役目录带 `-latest` 后缀，被替换的旧版移到 `~/.cc-switch/skills/.backups/` 并加日期前缀，不直接删除
- 改名或删除 skill 后，检查三端软链（`~/.workbuddy/skills`、`~/.claude/skills`、`~/.codex/skills`），清掉失效的

## 人拍板的两件事

1. **个人信息**：扫描命中的个人内容，发不发由人决定。默认做法是脱敏后发，不擅自决定发。
2. **第三方权利**：别人的 skill（官方或社区收集）本体上架前，确认许可允许再分发。拿不准就在附录只列名字和来源，不放本体。

## 不归本 skill 管

- 本地库的安装、启停、多平台同步：`jc-skill-installer`
- 新 skill 怎么写、值不值得写：`jc-skills-creator`
- 全量同步：不用 `scripts/sync-from-library.sh`，它会用本地未脱敏版本覆盖仓库里已脱敏的旧 skill。只发布指定的 skill。

## 发布前自检

- 隐私扫描四项全过，命中项都有处理记录
- README 五处更新点无遗漏，计数对得上实际目录数
- push 成功，远程能看到新文件
- 本地软链指向正确，失效链接已清
