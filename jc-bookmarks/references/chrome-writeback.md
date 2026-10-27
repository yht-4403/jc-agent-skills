# Chrome 写回细节

写回是这个流程里唯一会损坏数据的一步。前面整理得再好，这一步做错就是「书签全没了」。

## profile 目录里的四个文件

路径（macOS）：`~/Library/Application Support/Google/Chrome/Default/`

| 文件 | 是什么 | 能不能动 |
| --- | --- | --- |
| `Bookmarks` | 本机书签树，明文 JSON | **改这个** |
| `Bookmarks.bak` | Chrome 唯一的备份，每次会话首次改书签时写一次 | 只做兜底，不要主动写 |
| `AccountBookmarks` | Chrome 134+ 登录未同步时的**账户树**，浏览器里和本机树合并显示 | 别动；它没有 `.bak` |
| `EncryptedBookmarks2` | 书签加密实验的密文副本（`v10;` 开头） | 改动不生效时移走它 |

`BookmarkMergedSurfaceOrdering` 只记录两棵树的显示顺序，不含书签，可以忽略。

## 写回前必查：同步

```python
json.load(open("Preferences"))["sync"]["has_setup_completed"]   # true = 登录即同步
json.load(open("Preferences"))["sync"]["sync_to_signin_migration_state"]  # 2 = 已迁移
```

开着同步时，改本地文件的结局是：**Chrome 一启动，云端旧数据合并进来**，表现为顶层文件夹变多、条目数上涨。实测一次：写入 561 条 / 7 个顶层，正常启动后变成 592 条 / 19 个顶层（旧的 13 个 + 新的 7 个，同名合并）。

三条路：

1. **关同步**（推荐）：设置 → 你和 Google → 同步 → 关闭 → 选「保留此设备上的数据」。
2. **临时禁用**：`open -a "Google Chrome" --args --disable-sync`，只影响本次会话，用来确认结果。
3. **清云端重建**：开同步 → 全选删除（云端一起清空）→ 导入 HTML。会经历一段空书签状态，多设备在线时慎用。

## 写回时必做：合并而不是覆盖

整份替换等于告诉同步端「全删了又全加了 561 条」。正确做法是按 URL 配对，沿用原节点：

```python
node["guid"] = old_node["guid"]
node["id"] = old_node["id"]
node["date_added"] = old_node["date_added"]
```

URL 归一化时去掉 scheme、`www.` 和结尾斜杠，否则 `http://x.com` 和 `https://x.com` 配不上。

`bookmark_bar` 根节点保留 Chrome 原来的 `id`（通常是 `1`）和 `guid`，只替换 `children`。

## checksum 只能留空

Chrome 的 `BookmarkCodec` 是**按节点逐个累加**哈希的，不是对最终 JSON 整串哈希，因此无法从文件内容反推。穷举过 md5/sha1、hex/base64、紧凑/带空格/pretty、sort_keys、roots/全文各种组合，都对不上。

处理方式：`"checksum": ""`。空值会跳过校验，Chrome 加载后自己重算并写回。

## 完整流程

```bash
# 0. 退出 Chrome（⌘Q）。用 pgrep -x 检查，-f 会匹配到脚本自己的命令行
# 1. 生成合并文件（不写）
python scripts/merge_back.py --src bookmarks.json
# 2. 确认输出里的「沿用 N 条原 GUID / M 条新增」符合预期
# 3. 写入（自动备份 Bookmarks / Bookmarks.bak / EncryptedBookmarks2）
python scripts/merge_back.py --write --src bookmarks.json
# 4. 启动验证
open -a "Google Chrome" --args --disable-sync
```

成功标志：`EncryptedBookmarks2` 的字节数随新数据变化（说明它按新树重新加密），顶层文件夹是整理后的结构。

## 回滚

按顺序试，越靠前越新：

1. `Bookmarks.mybackup-<时间戳>`（脚本写的）
2. `Bookmarks.bak`（Chrome 写的，内容是「最后一次变更前」）
3. `bookmarks-整理后.html` → 用 Chrome 导入

```bash
cp "Bookmarks.mybackup-20261020-133736" Bookmarks
```

## 其他浏览器

- **Edge / Brave / Vivaldi**：同样是 Chromium 结构，把 `--chrome` 指向各自 profile 的 `Bookmarks` 即可。
- **Firefox**：`places.sqlite`，不能直接换文件，只能导出 HTML 后通过界面导入。
