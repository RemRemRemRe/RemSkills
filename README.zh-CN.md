# RemSkills

面向 Rem 模块开发的 AI skills 集合 —— 采用 [Agent Skills](https://agentskills.io/specification)
格式，指导 AI 编码代理完成 Unreal Engine 插件开发全流程：C++ 规范、测试、提交工作流、
子模块维护、多引擎适配。每个 skill 是一个包含 `SKILL.md` 入口的文件夹，按需加载。

> **English version**: [README.md](README.md)

两份语言版本保持精确同步 —— 一句话简介与各 skill 自身的 `SKILL.md` description
保持一致；skill 描述变更时，两份文件在同一改动中同步更新。

## 内容分类

**提交与 Git 工作流**

- [`rem-commit-workflow`](rem-commit-workflow/SKILL.md) — 在 UE 项目中提交改动：单一职责提交、格式 + 审查 + 一次构建。提交或拆分混合提交时使用。
- [`rem-rewrite-commit-history`](rem-rewrite-commit-history/SKILL.md) — 用 amend、fixup + autosquash 或 rebase -i 把未推送的 WIP 折叠为单一职责提交。推送前重塑本地分支时使用。
- [`rem-submodule-sync`](rem-submodule-sync/SKILL.md) — 把 git 子模块快进或 rebase 到远端默认分支最新，构建验证后提交。子模块落后或需要同步插件子模块时使用。
- [`rem-submodule-push`](rem-submodule-push/SKILL.md) — 安全推送父仓库及其子模块：三轴审计、显式 origin 引用、以 `--recurse-submodules=check` 为关卡。推送带子模块的项目时使用。

**C++ 开发规范**

- [`rem-cpp-best-practices`](rem-cpp-best-practices/SKILL.md) — 模块代码的 C++ 审查清单：include、命名、const、UPROPERTY 元数据、日志、测试。提交前审查 diff 或编写模块代码时使用。
- [`rem-observability-and-profiling`](rem-observability-and-profiling/SKILL.md) — 日志、开关控制的调试绘制、控制台与 cvar 钩子、剖析标签。编写或审查必须在运行时可见的代码时使用。
- [`rem-docs-and-config`](rem-docs-and-config/SKILL.md) — 记录一次改动带来的文档与配置：技术文档、配置参考、提示文本。新增子系统、公开 API、配置属性或面向策划的行为时使用。
- [`rem-ranges-transrangers`](rem-ranges-transrangers/SKILL.md) — 用 Rem::Ranges、transrangers、RemStd::bind_back 编写函数式流水线代码。编写或阅读 filter/transform/group 流水线时使用。

**UE 模块与编辑器扩展**

- [`rem-create-new-module`](rem-create-new-module/SKILL.md) — 按关键字替换复制 RemMyBlank 模板来创建模块或插件。新增模块或新建插件时使用。Last verified: 2026-07。
- [`rem-customize-factory-asset-menu`](rem-customize-factory-asset-menu/SKILL.md) — 把自定义 UFactory 放进 Content Browser 的 Add/New Asset 分类或子菜单。工厂没出现在预期菜单、或 GetAssetMenuPathsForCategory 被忽略时使用。
- [`rem-sequencer-custom-channel-section`](rem-sequencer-custom-channel-section/SKILL.md) — 为 Sequencer 添加自定义 FMovieSceneChannel 与 UMovieSceneSection，支持逐关键帧结构体编辑。关键帧存放需逐帧编辑的结构体数据时使用。
- [`rem-ue-localization`](rem-ue-localization/SKILL.md) — UE 本地化：localization target、编辑器文本的 namespace+key 查表、gather/translate/compile。新增语言或文本未翻译时使用。

**测试**

- [`rem-test-completeness`](rem-test-completeness/SKILL.md) — 判断一次改动的自动化测试是否完备：变更→用例映射、五条判定、bug 修复 regression-first。编写缺失用例时使用。
- [`rem-bdd-test-tree`](rem-bdd-test-tree/SKILL.md) — 把 UE 自动化 spec 文件（DEFINE_SPEC / Describe / It）整理成思维导图式的层级测试树。审查大型测试套件或需要测试树索引时使用。

**多引擎插件适配**

- [`rem-ue-plugin-adapter`](rem-ue-plugin-adapter/SKILL.md) — 把 UE 插件从上游最新适配到 5.3–5.8 引擎：分支管理、嵌入依赖、build-fix-commit 循环。运行跨版本构建时使用。

**Skill 元技能**

- [`rem-write-better-skill`](rem-write-better-skill/SKILL.md) — skill 编写约定：frontmatter、文件结构、占位符、示例、checklist。创建或更新本集合中的 skill 时使用。
- [`rem-public-material-generalization`](rem-public-material-generalization/SKILL.md) — 公开材料的发布规则：占位符、local/ overlay、推送前泄漏清单。编写公开文档、提交信息或 skill 时使用。
- [`rem-session-knowledge-distillation`](rem-session-knowledge-distillation/SKILL.md) — 把会话中可复用的经验沉淀为新文档，或对现有文档 / 流程 / skill 的增补。会话结束或到达里程碑时使用。

**主会话编排**

- [`rem-orchestration`](rem-orchestration/SKILL.md) — 委派子代理、执行迭代 / 冻结 / 推送档节奏、削减每轮最慢的步骤。作为主会话编排工作时使用。
- [`rem-shared-resources`](rem-shared-resources/SKILL.md) — 协调同一项目中的多个 agent 会话：声明要写的文件，租约 build / test / git / IDE 资源，保留各会话日志。两个会话共用一个项目时使用。

**环境约束**

- [`rem-no-disk-scanning`](rem-no-disk-scanning/SKILL.md) — 始终加载：禁止磁盘文本搜索（rg、grep、find、ripgrep、findstr）；搜索走项目的 MCP 服务器（Rider MCP）。每会话搜索文件时使用。
- [`rem-temp-files`](rem-temp-files/SKILL.md) — 始终加载：临时文件放系统 TEMP 目录而非工作树；只有后续读者需要的才持久化到 run 目录。会话写出中间文件时使用。

## 日常参考工作流

- **开始会话** — `rem-no-disk-scanning` 与 `rem-temp-files` 始终加载；所有文本搜索走 Rider MCP
- **编写**
  - 编写 / 审查 C++ — `rem-cpp-best-practices`（规则 + §17 提交前 checklist）；流水线代码用 `rem-ranges-transrangers`
  - 埋点与性能剖析 — `rem-observability-and-profiling`（日志、调试绘制、钩子、标签）
  - 文档与配置暴露 — `rem-docs-and-config`（技术文档、配置参考、提示文本）
  - 新建模块 / 插件 — `rem-create-new-module`
  - UE 编辑器 / 资产工作 — `rem-customize-factory-asset-menu`、`rem-sequencer-custom-channel-section`
  - 让编辑器文本支持其它语言 — `rem-ue-localization`
- **测试**
  - 确认测试完备 — `rem-test-completeness`（关卡）；`rem-bdd-test-tree`（审查索引）；spec 模板与运行坑位在 `rem-cpp-best-practices/references/tests.md`
- **提交与推送**
  - 提交 — `rem-commit-workflow`（message、hygiene、审查、构建）；套件在推送档运行；项目事实来自其 `local/` overlay
  - 推送前整理历史 — `rem-rewrite-commit-history`
  - 同步 / 推送子模块 — `rem-submodule-sync`、`rem-submodule-push`
- **扩展与维护**
  - 多引擎版本适配 — `rem-ue-plugin-adapter`
  - 编写 / 发布 skill — `rem-write-better-skill`、`rem-public-material-generalization`
  - 沉淀会话知识 — `rem-session-knowledge-distillation`

## 安装

- 克隆本仓库（或只复制需要的 skill 文件夹）。每个 skill 自包含于自己的文件夹。
- 让代理加载该集合：使用 [pi](https://github.com/earendil-works/pi) 时，把路径加入
  settings 的 `skills` 数组，或传 `--skill <path>`（可重复）。任何兼容 Agent Skills
  的 harness 均可。
- 项目本地 skill：放在项目的 `.agents/skills` 下（harness 启动时信任）。
- 机器本地值放在每个 skill 的 git 忽略 `local/` overlay 中，通过符号链接指向独立的私有仓库
  （**无公开远端**）—— 见下方分流说明。

## 前置依赖

- 兼容 Agent Skills 的代理 harness（推荐 pi）。
- **Rider MCP** —— `rem-no-disk-scanning` 所必需：文本搜索走 Rider，禁用磁盘扫描器。
- 支持自动化测试的 Unreal Engine 项目（`DEFINE_SPEC` BDD spec + 无头 `-nullrhi` 运行路径）。

## 公开 / 私有分流

公开 skill 只携带规则 —— 通用占位符，不含项目名、路径或内部决策。机器本地值放在每个
skill 的 git 忽略 `local/` overlay 中：以符号链接指向私有仓库中的跟踪文件，绝不提交到
公开仓库。`RemSkillsPrivate` 保存仅本地使用的 skill 与跟踪的 overlay 值；参数化工具的
skill 把值放在外部逐插件配置中。规则单一归属
[`rem-public-material-generalization`](rem-public-material-generalization/SKILL.md)。

## Skill lint

```bash
node tools/lint-skills.mjs
```

零依赖的集合约定检查：frontmatter 结构与取值、`name` 与文件夹一致、description
包含触发条件且不超过 160 字符（集合总计 3,500 字符 —— 它常驻在每个请求的
上下文中）、结尾 checklist、体量预算（>32KB 告警 / >48KB 失败，不含
checklist）、泄漏模式（盘符路径与家目录路径），以及
[`tools/public-names.json`](tools/public-names.json) 中的 Rem 家族名单白名单。

泄漏与名单检查会读取**所有会随仓库发布的非二进制文件**——每个 skill 自身的文件
（`SKILL.md`、`references/**`、`tools/` 下的脚本与模板）以及仓库级文件（README、
LICENSE、工作流、hooks、`tools/`）——因此搬进 reference 或随附脚本的内容都不会脱离
检查。除了白名单与 git 忽略的 `local/` overlay，没有任何豁免：会发布出去的文件，
就是对所有人可见的文件。`local/` overlay 不会发布，也不参与扫描；lint 会保持这一点
——`local/` 下没有任何被跟踪的路径、其中的每个文件都是目标可解析的符号链接、
且顶层 skill 目录之外不存在 `SKILL.md`。未在白名单中的 `Rem*`/`URem*` 名字会使
检查失败；请为其补充可公开验证的来源，或将其泛化。

它是**本地检查**，不是 CI 任务——检查必须在变更离开本机之前通过，而不是推送之后。
每个克隆安装一次：

```bash
git config core.hooksPath .githooks
```

## 项目笔记

- [`orchestration-policy.md`](orchestration-policy.md) —— 主会话的**常驻硬规则**（禁扫盘、委派默认值、只编译的迭代、削减每轮最慢步骤、事件驱动等待）；其背后的流程在 `rem-orchestration` 技能里。它是项目根目录 `AGENTS.md` 软链接的源文件，指向该软链接的 harness 加载的正是这份文件。与根目录的两份 README 一样，它是仓库文档，不是 skill。

## Star History

<a href="https://star-history.com/#RemRemRemRe/RemSkills&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=RemRemRemRe/RemSkills&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=RemRemRemRe/RemSkills&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=RemRemRemRe/RemSkills&type=Date" />
 </picture>
</a>

## License

[MIT](LICENSE)
