---
name: ios-messaging-design
description: 为消息、聊天、群组、频道和即时通信界面选择、比较并应用 16 套逆向整理的移动端设计系统，提供 framework-neutral、SwiftUI、Expo/React Native 与 Jetpack Compose 版本。用户要求设计、实现或分析 WhatsApp、Telegram、Discord、Slack、Signal、Messenger、LINE、WeChat、iMessage、Viber、Skype、Kik、GroupMe、KakaoTalk、Zalo、Threema 风格，或需要消息产品的色彩、排版、气泡、回执、动效与无障碍参考时使用。
---

# iOS Messaging Design

把仓库中的设计文档作为按需加载的参考资料。先遵守当前项目的 `AGENTS.md`、`CLAUDE.md`、设计 Token 和组件边界。

## 工作流

1. 明确目标界面、参考 App 和实现栈。用户未指定 App 时，先读 [Messaging 索引](references/messaging/README.md)，根据产品目标选择 1～3 个候选；用户未指定实现栈时，分析任务使用 `DESIGN.md`。
2. 只读取所选 App 的必要文件：
   - `DESIGN.md`：框架无关的设计系统。
   - `DESIGN-swiftui.md`：SwiftUI。
   - `DESIGN-expo.md`：Expo / React Native。
   - `DESIGN-android.md`：Jetpack Compose。
   - `README.md`：该设计包的定位、标志性模式和文件导航。
3. 提取与任务相关的语义角色：视觉氛围、色彩职责、排版层级、组件状态、布局、层级、动效、触感、响应式与无障碍。
4. 将参考角色映射到当前项目已有 Token 和组件。项目禁止原始色值时，不把资料中的 hex 直接写入业务代码；先完成 Token 映射或沿用现有语义 Token。
5. 实现后检查亮色／暗色、Dynamic Type、触控目标、键盘与安全区、加载／发送／失败／已读等状态。只在用户明确要求且项目规则允许时做像素级复刻。
6. 交付时说明使用了哪些参考文件、哪些细节被采用，以及哪些细节因项目规范、品牌或平台约束而调整。

## 使用边界

- 这些文档是第三方逆向整理的设计参考，不能表述成相关品牌的官方规范或当前产品事实。
- 不复制未经授权的商标、Logo、专有插画或品牌素材；优先迁移交互模式与语义结构。
- 广泛比较时先用分类索引建立维度，再按需读具体文档，避免一次加载全部 16 套资料。
- 需要确认最新 Apple HIG、平台 API 或品牌现状时，另外查阅对应官方一手资料。

## 上游快照

- 仓库：`https://github.com/meliwat/awesome-ios-design-md`
- 分支：`main`
- 提交：`5d3aeca239caef3ea4080034eb22ab87cc77fa24`
- 范围：`design-md/messaging/`
- 许可证：[MIT](references/LICENSE)
