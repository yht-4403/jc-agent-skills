---
name: jc-skill-installer
description: 搜索、安装、启停、去重、版本管理并同步个人 Skill 库到 Codex、Claude Code、Antigravity (Gemini)、CodeBuddy、WorkBuddy、DeepSeek Harness、Kimi Work、Kimi Code 和 Grok Build；用户口头要求为当前任务寻找合适 Skill 时也使用。
---

# JC Skill Installer

Maintain one physical copy of every user-managed Skill and derive runtime state from it.

## Authority and layout

Use this hierarchy:

1. Project `AGENTS.md` or equivalent project rules control behavior inside that project.
2. The repository containing `jc-skill-installer/` stores all user-managed Skill files. Prefer `~/.cc-switch/skills/`, but do not require that absolute path.
3. `~/.codex/skills/`, `~/.claude/skills/`, and `~/.gemini/config/skills/`
   expose the same active Skill set through symlinks to the repository.
4. `active-skills.json` records the portable set enabled in Codex, Claude Code,
   Antigravity, CodeBuddy, WorkBuddy, DeepSeek Harness, Kimi Work and Grok Build.
   Grok uses Claude compatibility plus registered direct source paths for vendor-filtered names.
5. CodeBuddy exposes the active manifest through symlinks in `~/.codebuddy/skills/`
   (`~/.codebuddy/skills` on this computer); never create a second
   physical copy there. Additional projects may use `<project-root>/.codebuddy/skills/`.
6. DeepSeek Harness discovers user skills in `~/.dsh/skills` (`user-dsh`, rank 400).
   Expose the same active manifest there with symlinks only. Do not recreate the
   deprecated `~/.agents/skills/` directory; Harness also scans it at a lower rank,
   and a second copy would duplicate providers.
7. WorkBuddy is a separate client. Its existing `~/.workbuddy/skills/` root uses
   the same manifest and source symlinks; CodeBuddy synchronization does not cover it.
8. `runtime-policy.json` registers platform-owned Skill exceptions and Grok source
   selection. `source-imports.json` records imported personal sources and recovery locations.

State files (`active-skills.json`, `source-imports.json`, `skill-profiles.json`,
`skill-channels.json`, `runtime-policy.json`) are machine-specific and are not versioned
in this repository. They record the local Skill inventory, absolute paths and import
provenance, so they must be generated per machine: run `bootstrap` after cloning or
moving the Skill store to a new computer, and do not copy them across machines.

Exceptions:

- Leave Codex-managed `~/.codex/skills/.system/` untouched.
- Leave plugin caches under `~/.codex/plugins/` untouched unless explicitly uninstalling that plugin.
- Leave Grok-managed `~/.grok/bundled/` and plugin content untouched.
- Do not mirror the active manifest into `~/.grok/skills/` by default. Grok already scans
  `~/.claude/skills/`; a second mirror would expose duplicate providers under the same name.
- Do not recreate the deprecated `~/.agents/skills/` directory.

Never place a real third-party Skill body directly in a runtime directory. Kimi Work is a discovery exception: use real entry directories containing only links to source children, not copied content. Never expose ambiguous providers under the same invocation name. Grok can retain registered plugin/user namespace pairs only when `inspect --json` proves distinct `invocableAs` values; select the registered personal provider and preserve the plugin.

## 区分“启用、自动触发、按需搜索”

不要把三种状态混成一个开关：

1. **启用且可自动触发**：出现在运行时，模型可根据 Description 主动选择；只保留 JC 常用入口和经过验证的高频能力。
2. **启用但仅显式调用**：保留在运行时，但 `agents/openai.yaml` 设置 `policy.allow_implicit_invocation: false`；适合兼容入口、高风险动作和容易误触发的工具。
3. **未启用但可搜索**：文件保留在单一来源仓库，不进入日常候选列表；适合低频和长尾 Skill，需要时通过 `search` 找到并读取或临时启用。

官方语义中的“implicit”表示模型可以自动选择，并不等于节省候选列表开销。要减少日常上下文，应优先把低频 Skill 置于第三种状态，而不是仅修改触发措辞。

JC 自有 Skill 必须在默认核心集合中显式保留，不得因批量精简被静默停用；但是否允许自动触发仍按风险判断。`jc-skill-installer` 必须允许自动触发，因为用户会直接说“帮我找一下本次任务适合什么 Skill”；涉及安装、激活、停用、推广版本等写操作时，仍以用户当前请求的授权范围为准。

## JC 界面元数据预检

安装、激活或更新前检查源目录中的 `agents/openai.yaml`。不要只确认链接可读，还要区分机器标识、英文产品名和中文备注：

- `SKILL.md` 的 `name` 与目录名保持英文小写 kebab-case；
- JC 自有及用户在当前库维护的品牌 Skill，`interface.display_name` 默认使用英文 Title Case；同一产品线必须统一以产品名开头；
- `interface.short_description` 使用中文作为列表备注；`default_prompt` 跟随目标用户语言并包含 `$skill-name`；
- 激活前对照同品牌相邻 Skill，检查前缀、大小写、命名结构和列表语言是否一致；
- 第三方 Skill 保留上游 `display_name`，除非用户明确要求本地改名，不得按 JC 规范擅自翻译。

发现 JC 品牌展示名不符合约定时，修改单一来源仓库中的 `agents/openai.yaml` 后再同步；不要只改 Codex、Claude Code 或 CodeBuddy 的运行时链接。英文产品名尚未确定时停止并向用户确认，安装器不得自行发明品牌名称。

## Use the manager

The manager requires Python 3.11 or newer for standard-library TOML parsing.

Run:

```bash
python3 <skills-root>/jc-skill-installer/scripts/manage.py audit
python3 <skills-root>/jc-skill-installer/scripts/manage.py prune-broken
python3 <skills-root>/jc-skill-installer/scripts/manage.py prune-source-self-links
python3 <skills-root>/jc-skill-installer/scripts/manage.py export
python3 <skills-root>/jc-skill-installer/scripts/manage.py activate <relative-skill-path>
python3 <skills-root>/jc-skill-installer/scripts/manage.py deactivate <skill-name>
python3 <skills-root>/jc-skill-installer/scripts/manage.py search <任务或能力关键词>
python3 <skills-root>/jc-skill-installer/scripts/manage.py channels
python3 <skills-root>/jc-skill-installer/scripts/manage.py select-latest <skill-family>
python3 <skills-root>/jc-skill-installer/scripts/manage.py promote <skill-family> <version>
python3 <skills-root>/jc-skill-installer/scripts/manage.py profiles
python3 <skills-root>/jc-skill-installer/scripts/manage.py profile-diff <profile-name>
python3 <skills-root>/jc-skill-installer/scripts/manage.py apply-profile <profile-name>
python3 <skills-root>/jc-skill-installer/scripts/manage.py bootstrap
python3 <skills-root>/jc-skill-installer/scripts/manage.py rules
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-rules
python3 <skills-root>/jc-skill-installer/scripts/manage.py reconcile
python3 <skills-root>/jc-skill-installer/scripts/manage.py update <relative-skill-path>
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-claude
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-gemini
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-codebuddy
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-codebuddy <project-root>
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-dsh
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-workbuddy --dry-run
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-workbuddy
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-grok --dry-run
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-grok
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-kimi-code --dry-run
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-kimi-code
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-kimi-work --dry-run
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-kimi-work
```

The script refuses conflicting real directories and symlinks. Do not bypass a conflict without inspecting the existing target.

## 全端管理规则与操作完成条件

所有个人 Skill 的新增、更新和停用都交回本管理器。各端内置 creator、installer、
技能市场或其他迁移工具只负责生成、下载候选文件；不得自行决定全局安装目录，
不得在运行时留下实体副本，不得对源链接调用客户端原生删除工具。

- 新增：创建或导入到唯一来源仓库后，执行 `activate <relative-skill-path>`。
- 更新：先保存旧内容，修改对应源文件后，执行 `update <relative-skill-path>`。
  `update` 是修改完成后的同步和检查步骤，不会擅自联网拉取或激活未启用入口。
  它刷新 Kimi Work 新增或删除的顶层资源链接，拒绝从仓库外的路径或历史归档入口完成更新。
- 停用：执行 `deactivate <skill-name>`，只撤下各端入口，保留源内容。
  `jc-skill-installer` 是管理入口，不能通过普通停用命令移除。
- 更新整套源文件或修复：执行 `reconcile`，保持当前活动集合，重建规则与入口并检查。

每次改变活动集合或完成更新，管理器先维护全局规则、登记的来源管理桥接，再同步
所有已安装客户端，最后运行完整检查。检查失败时返回非零，不输出全端同步成功。
这些命令自动传播改动；本管理器不是文件监听器，任意手工复制或 GUI 直接安装不能
据此声称已同步。Agent 遇到这种候选内容应先导入统一仓库，再执行管理器命令。

`rules` 列出并核对管理规则的实际目标；`sync-rules` 只维护规则，不改变活动集合。
规则块与当前管理器文本逐字比较，缺失、过时或损坏会被检查报告；维护时保留块外用户内容。

已核实的客户端入口：

- Codex：`~/.codex/AGENTS.md`。
- Claude Code：`~/.claude/CLAUDE.md`；Grok 通过 Claude 兼容继承该文件，
  `grok inspect --json` 必须实际发现它，不能仅凭文件存在认定生效。
- Gemini / Antigravity：`~/.gemini/GEMINI.md`。
- CodeBuddy：`~/.codebuddy/CODEBUDDY.md`。
- WorkBuddy：内嵌 CLI 默认 `CODEBUDDY.md`，产品品牌可改变 basename；同时维护
  `~/.workbuddy/CODEBUDDY.md` 和 `~/.workbuddy/WORKBUDDY.md` 的同一规则块。
- DeepSeek Harness：`~/.dsh/AGENTS.md`，安装的原生规则读取器已验证。
- Kimi Code：`<KIMI_CODE_HOME>/AGENTS.md`，安装包的原生读取逻辑已验证。
- Kimi Work：当前原生读取器只读取配置中 agent 的 `workDir/AGENTS.md`，不应猜测
  `daimon/AGENTS.md` 是全局入口。管理器读取现有 agent 配置并维护这些实际工作区的
  AGENTS.md；现有工作目录未配置或不存在时，检查失败，不创建猜测路径。
  用户在客户端绕过配置临时切换到其他工作目录时，必须为那个实际目录维护规则后再
  声称覆盖；本机已验证的是现有配置中 main agent 的工作区。

`runtime-policy.json` 的 `management_routes` 和 `management_script_routes` 登记
会与本机规则冲突的个人安装、更新入口。管理器自动维护带独立标记的本地桥接，保留
原上游正文；上游内容被替换后，完成更新会重新放回桥接，并检查是否正确。
目前登记了 DBS 安装入口、DBS 更新入口和自有产品线更新入口。DBS 的安装脚本在
检测到管理器仓库后，将 `link`、`unlink`、`status` 交给 `dbs-route`，不执行旧的
公共目录 / Grok 薄适配层逻辑；仓库外的候选源必须先导入，脚本不擅自复制。

`prune-source-self-links` removes only a symlink located directly inside a Skill when
that link resolves back to the same Skill directory and a real sibling `SKILL.md` is
present. It never removes the target directory or the source `SKILL.md`.

## 口头搜索长尾 Skill

当用户说“看看这次有什么合适的 Skill”“帮我搜一个能做 X 的 Skill”或同义表达时，无需 `$skill-name` 关键词，直接使用：

```bash
python3 <skills-root>/jc-skill-installer/scripts/manage.py search "<用户当前任务>"
```

`search` 同时扫描启用与未启用的源 Skill，并标注状态。读取排名靠前候选的完整 `SKILL.md`，核对任务边界、依赖与冲突后再推荐。搜索结果只是候选，不代表已经启用，也不得仅凭名称自动安装或持久激活。一次性任务可以按路径读取后在当前任务中使用；只有用户要求以后默认可用时，才执行 `activate`。

搜索不到合适能力时，说明缺口并继续用通用能力完成任务；不要为了证明仓库有用而硬套相邻 Skill。

## 默认加载集合

`skill-profiles.json` 保存可审查的激活集合。默认集合只收录：

- 全部 JC 自有入口；
- 自有产品线主链路及版本通道当前指向的稳定版；
- 从近期真实任务中反复出现的开发、讲解、UI、文档与协作能力。

先执行 `profile-diff jc-default` 查看变化，再由用户决定是否 `apply-profile jc-default`。应用 Profile 只改活动清单和运行时链接，不删除源 Skill；被停用的长尾能力仍可由 `search` 找回。每次增删默认项都要写出真实使用证据或路由理由，不以“也许有用”为准入标准。

`jc-default` 使用 `require_all_prefixes: ["jc-"]` 做硬校验：仓库新增 JC Skill 后，如果没有明确加入 Profile，预览和应用都会失败，避免批量精简时静默漏掉自有能力。

Profile 中引用版本 family，不直接硬编码其 v2/v3 路径；解析时自动跟随 `latest`。这样升级版本不会把新旧两版同时带回默认集合。

## 最新版命名与历史版本归档

JC 自有及本地维护、需要版本管理的 Skill 统一采用以下约定（2026-09-17 用户确认）：

- 当前版本使用固定的 `family-latest` 实体目录，`SKILL.md` 的 name 和默认调用名保持一致；展示名使用 Latest，不带 v 编号。统一拼写 latest，不使用 lastest。
- 当前版本只保存一份实体文件，不额外复制同内容的 v 目录，也不只用隐藏的 latest 指针而继续展示 v 编号。
- 有下一版内容需要发布时，才把被替换的当前版归档为 `family-vN`；先保存旧版，再修改 latest。已归档版本不可覆盖或改写。
- `skill-channels.json` 中 latest 指针为 `latest`，versions.latest 指向 `family-latest`；`archive_on_next_update` 记录当前版被替换时应使用的 v 编号。归档后登记版本路径，并递增待归档编号；操作前检查编号未占用。
- 归档副本的 frontmatter name、展示名和默认调用名改为相应 v 编号；当前版保持 latest 名称，相关 Skill 的活动路由指向 latest。
- 同一 family 日常只启用 latest；历史版本仅用于回归、对照与回滚，不进入自动加载。
- 新内容发布前完成结构校验、触发/不触发 Eval 和真实任务回归；单纯改名只需结构、引用、同步和发现检查，不声称完成内容质量回归。
- 更新活动清单后通过管理器 bootstrap 和 audit 同步运行时；select-latest 让清单与当前通道对齐。
- 回滚时保留当前内容的可恢复归档，将指定历史内容恢复到 latest，并调整当前入口元数据；不修改历史源文件，不直接启用历史 v 入口。
- 其他现有版本目录不因这次规则变化而批量迁移；在用户要求改名或下次维护该 family 时按此约定迁移。第三方 Skill 保留上游命名，未采用版本管理的 Skill 不强行添加 latest。

## Install a Skill

1. Resolve the official repository, branch or tag, exact Skill path, and dependencies.
2. Check for an existing directory, symlink, manifest entry, duplicate name, and local modifications.
3. Download the real files into `<skills-root>/<folder>`.
   - Prefer Codex's system installer with an explicit destination:

     ```bash
     python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
       --repo owner/repo --ref main --path path/to/skill \
       --dest <skills-root>
     ```

   - Never rely on an installer's default global destination.
4. Read the installed `SKILL.md` and install required companion Skills.
5. 对 JC 自有或本地维护的品牌 Skill 执行界面元数据预检；第三方 Skill 保留上游命名。
6. Activate it and update the manifest:

   ```bash
   python3 <skills-root>/jc-skill-installer/scripts/manage.py activate <folder>
   ```

7. Run `audit` and report the upstream source and revision.
8. `activate` automatically exposes the newly active Skill in Codex, Claude Code,
   Gemini, the default `~/.codebuddy/skills/` runtime, and DeepSeek Harness at
   `~/.dsh/skills`. Grok Build sees the Claude runtime through its default
   compatibility layer. Run `sync-codebuddy <project-root>` only when an additional
   project-local runtime is also required. Run `sync-dsh` only to repair `~/.dsh/skills`.

For a repository containing several Skills, store the repository once and activate nested Skill paths. Do not clone the same repository once per Skill.

## Update a Skill

Identify its upstream source before changing files. Fetch into a temporary directory, compare versions, and preserve user modifications. Replace only the intended Skill files, keep the same manifest path, then run `bootstrap` and `audit`. `bootstrap` automatically reconciles Codex, Claude Code, Gemini, the default CodeBuddy runtime, and DeepSeek Harness `~/.dsh/skills`; re-run `sync-codebuddy <project-root>` only for additional project-local runtimes. Do not claim “latest” without checking the upstream revision at update time.

For a versioned JC Skill, follow 最新版命名与历史版本归档 above: archive the outgoing latest under its reserved v number before changing content, keep the active name family-latest, validate the replacement, then reconcile through bootstrap and audit. Never overwrite an archived version. For existing legacy families, migrate their naming when that family is next maintained; do not bulk-rename unrelated Skills.

## Disable or uninstall

- To disable while retaining files, run `deactivate <name>`.
- To uninstall, first resolve the manifest path and verify every runtime link points to it. Remove links and the manifest entry before deleting the exact source directory.
- Treat deletion as destructive: use explicit paths, refuse the repository root, preserve unrelated files, and report recoverability.
- After uninstalling, run `export` and `audit`. `export` automatically reconciles the
  default CodeBuddy runtime; sync any additional project-local runtimes explicitly.

## Sync CodeBuddy

CodeBuddy discovers Skills one folder below `~/.codebuddy/skills/`. The default runtime on
this computer is `~/.codebuddy/skills`. Reconcile it manually when needed:

```bash
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-codebuddy
```

For an additional project-local runtime, provide its project root:

```bash
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-codebuddy <project-root>
```

The command creates one readable symlink per active Skill, flattens repository containers
that hold nested Skills, and removes stale symlinks. It refuses to overwrite real files or
directories. The cc-switch repository remains the only physical source of Skill files.

`activate`, `deactivate`, `export`, and `bootstrap` automatically reconcile the default
`~/.codebuddy/skills/` runtime and DeepSeek Harness `~/.dsh/skills`. The explicit command
is retained for manual repair and additional project-local runtimes.

## Sync Kimi Work

Kimi Work uses its managed root through `--skills-dir`; do not assume that Kimi Code's
Claude-compatible discovery also applies to Work. On macOS the currently verified root is:

```text
~/Library/Application Support/kimi-desktop/daimon-share/daimon/skills
```

Run `sync-kimi-work --dry-run`, then `sync-kimi-work`. The manager detects an existing
macOS root or the same suffix under Windows `%APPDATA%`; Windows discovery is a candidate
layout and has not been verified on a Windows client. For another verified root, set
`JC_KIMI_WORK_SKILLS_DIR` to its existing directory. Never silently fall back to
`~/.kimi/skills`, create a guessed Work root, or alter the application's configuration.

Work 3.2.15's `skill list` skips directory symlinks. Each managed Skill therefore uses a
real entry directory whose `SKILL.md`, scripts, references, assets and other source children
are symlinks. All real content remains in the single source repository. The runtime receipt
`.jc-skill-installer-links.json` owns these entry directories; only recorded entries may be
reconciled or removed. Preflight all conflicts, preserve builtins and unrelated links, and
refuse modified managed resources instead of deleting them. Do not use Work's `skill delete`
on source-linked entries; use this manager to deactivate them.

When an existing Work root is detected, `activate`, `deactivate`, `export`, `bootstrap`,
Profile application and channel selection automatically reconcile it. On machines without
Work, automatic synchronization skips it; the explicit command reports a missing root.
Source edits are visible through links; adding or removing top-level resource files requires
another sync. Audit checks every resource link and ownership record.

Unregistered personal Skill directories must be imported into the source repository
before synchronization. Preserve their original files and record provenance in
`source-imports.json`. Register verified Kimi builtin entries in `runtime-policy.json`;
do not import or rewrite those application-managed files. Audit reports unregistered extras.

Verify discovery with the installed Work bundle's `kimi-daimon skill list`, explicitly
setting `KIMI_SKILLS_ROOT` to the Work root (the standalone runner otherwise defaults to
`~/.kimi/daimon/skills`). Use `skill view <name>` to verify linked Markdown is readable.
Preserve app-provided skills and compare names against the active manifest, allowing extra
builtin/plugin providers. Successful discovery does not prove model invocation or all
external tool dependencies work. For an already-open conversation, use a new task to obtain
fresh discovery; do not automatically restart or interrupt the user's running tasks.

`agents/openai.yaml` UI names and invocation policy are platform metadata. Do not claim
Kimi honors `allow_implicit_invocation: false` without target-client verification; explicit-only
workflow boundaries must also remain clear in runtime instructions. Codex-only tools, MCP
providers and private dependencies require detection or a supported fallback on Work.

## Sync DeepSeek Harness

DeepSeek Harness desktop (`com.deepseek.dsh`) and the `dsh` CLI scan `<dshHome>/skills`,
defaulting to `~/.dsh/skills`. Reconcile it manually when needed:

```bash
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-dsh
```

The command uses the same flat symlink mapping as Claude Code. It refuses to overwrite
real files. Do not copy Skill bodies into `~/.dsh/skills` or `~/.agents/skills`. After
linking, restart DeepSeek Harness so it rescans the new root.

## Sync Claude Code

Claude Code discovers Skills in `~/.claude/skills/`. It uses the same active manifest and
flat symlink mapping as CodeBuddy:

```bash
python3 <skills-root>/jc-skill-installer/scripts/manage.py sync-claude
```

`activate`, `deactivate`, `export`, and `bootstrap` automatically reconcile Claude Code.
The explicit command is retained for manual repair.

## Use with Grok Build

Grok Build scans `~/.claude/skills/` by default, so `sync-claude` is also the canonical
Grok synchronization path. Do not add a separate `sync-grok` mirror or duplicate the
manifest under `~/.grok/skills/`. Use `sync-grok` to reconcile the supported `[skills]`
`paths` and `ignore` configuration, retaining unrelated settings and user paths.
The receipt `~/.grok/.jc-skill-installer-grok-config.json` owns only the values this
manager adds; deactivation removes obsolete owned paths. No second physical copy is created.

Some Grok releases filter `docx`, `pdf` and `pptx` from the Claude compatibility
provider. `runtime-policy.json` registers their direct canonical source paths and
temporarily excludes the bundled counterparts while those personal Skills are active.
The bundled files remain untouched. Audit verifies that selected discovery paths
resolve to the active source repository, rather than accepting a same-name builtin.

Grok's plugin scanner can expose qualified namespace pairs even when a skill path
is in `[skills].ignore`. Do not claim that this excludes plugin providers. Register
the verified pair and preferred invocation; currently `user:clean-architecture`
selects the canonical personal source while `developer-kit-java:clean-architecture`
remains plugin-owned. Audit rejects unregistered collisions, missing qualifiers,
unexpected providers or a preferred qualifier resolving to another source.

`sync-grok` removes only retired mirror symlinks pointing to the deprecated
`~/.agents/skills/` tree or duplicating active source targets. Preserve unrelated
Grok user directories until they have been inspected and imported.

Verify discovery from the target project directory with:

```bash
grok inspect
grok inspect --json
```

Expected user Skill sources resolve through `~/.claude/skills/` and are reported with
Claude compatibility enabled. Grok may normalize spaces, underscores, or punctuation in
names, filter known vendor defaults, prefer a bundled Skill, or recursively expose nested
`SKILL.md` files, so compare resolved source paths and declared names instead of requiring
the raw entry count to equal `active-skills.json`.

If Claude compatibility was explicitly disabled in `~/.grok/config.toml` or through
`GROK_CLAUDE_SKILLS_ENABLED=false`, restore the default compatibility setting. Do not
work around it by creating a second managed runtime unless the user explicitly requires a
Grok-only setup and accepts the duplicate-provider risk.

## Initialize another computer

The Skill cannot bootstrap itself before the repository exists. First clone or copy the complete Skills repository anywhere on the new computer, keeping `jc-skill-installer/` directly inside the repository root. The recommended location remains:

```text
~/.cc-switch/skills
```

Then run:

```bash
python3 <actual-skills-root>/jc-skill-installer/scripts/manage.py bootstrap
python3 <actual-skills-root>/jc-skill-installer/scripts/manage.py audit
```

The manager resolves `<actual-skills-root>` from its own real filesystem location. Use `--root <path>` only when `jc-skill-installer/` is not directly inside the repository root.

`bootstrap` performs the complete self-initialization:

- recreates Codex runtime symlinks from `active-skills.json`;
- recreates Claude Code runtime symlinks at `~/.claude/skills/`;
- recreates the default CodeBuddy runtime at `~/.codebuddy/skills/`;
- recreates DeepSeek Harness user skills at `~/.dsh/skills/`;
- reconciles installed WorkBuddy and Kimi Code desktop from the same manifest;
- reconciles Grok's registered canonical source selection and retired mirror links;
- makes the same Claude runtime available to Grok Build through its default compatibility;
- installs a small managed priority rule in `~/.codex/AGENTS.md` and `~/.claude/CLAUDE.md`;

The managed rule block may be updated safely without replacing unrelated user instructions. This manager never reads or writes the cc-switch application database.

## Sync WorkBuddy and automatic reconciliation

Kimi Code desktop is distinct from Kimi Work. The installed macOS desktop's bundled
`agent-core-v2/src/features/skill/catalog/skillRoots.ts` uses `<KIMI_CODE_HOME>/skills`
(default `~/.kimi-code/skills`) and the retired `.agents/skills` fallback; it does not
read the Claude directory by default. Use `sync-kimi-code` to create flat source links
under an existing Kimi Code user root. Its scanner follows directory symlinks. Automatic
reconciliation and audit include this root. Do not recreate `.agents/skills` or guess
`~/.kimi/skills`; this layout is verified for the installed Kimi Code desktop only,
not every legacy Kimi CLI version. A running conversation may need a fresh task to
discover newly linked entries; no application restart is performed automatically.

WorkBuddy uses `~/.workbuddy/skills/`, independently of CodeBuddy. The manager
detects an existing `~/.workbuddy/` user root; it skips automatic synchronization
when WorkBuddy is not installed and refuses an explicit sync when that root is absent.
The installed client follows directory symlinks during Skill discovery.

Use `sync-workbuddy --dry-run` before an initial import. Existing real directories
are conflicts: compare their names and resources, preserve them with restore paths,
then import unique personal Skills or retire duplicate runtime copies before syncing.
Do not overwrite them or flatten an old suite without preserving its original resources.

`activate`, `deactivate`, `export`, `bootstrap`, Profile application and channel
selection reconcile WorkBuddy and Grok alongside all previously supported clients.
Bootstrap maintains WorkBuddy's global managed rule block without replacing unrelated
instructions. Audit includes WorkBuddy, Grok's real `inspect` discovery, unregistered
real runtime Skill directories and the deprecated `.agents/skills` root.

Successful file discovery does not prove business workflows or platform-specific
MCP dependencies work. Verify fresh WorkBuddy cache results and Kimi's installed
CLI without restarting or interrupting existing conversations.

## Completion checks

Before reporting success, confirm:

- every enabled manifest entry has a readable `SKILL.md`;
- runtime entries are symlinks to the expected cc-switch paths;
- Codex, Claude Code, CodeBuddy, and DeepSeek Harness resolve the same declared active Skill set;
- WorkBuddy resolves the same set from its independent root and a refreshed client cache;
- when Grok Build is installed, `grok inspect --json` reports the expected source Skills
  through Claude compatibility, allowing for Grok name normalization, bundled filtering,
  and nested Skill discovery;
- Codex and Claude global rule files contain the managed priority block;
- there are no conflicting names or broken links;
- Grok's selected personal sources match the manifest, with only explicitly registered
  namespace pairs retained under distinct callable names;
- unregistered real personal Skill directories are reported instead of silently ignored;
- each registered version family has at most one active version and any active version matches its `latest` channel;
- any proposed activation Profile resolves successfully, preserves required JC entries, and follows version channels instead of listing parallel versions;
- JC 自有品牌 Skill 的英文 `display_name`、中文 `short_description` 与相邻产品列表保持一致，第三方展示名未被擅自翻译；
- the source repository contains no symlink that resolves back to its own Skill directory;
- the target CodeBuddy project has a readable `.codebuddy/skills/<name>/SKILL.md`
  link for each active Skill and no stale managed links;
- installed Kimi Work resolves the active set through real entry directories with source-linked resources; ownership audit passes and builtins remain untouched;
- system Skills and unrelated user changes remain untouched.
