# RemSkills

面向 Rem 模块开发的 AI skills 集合 —— 采用 [Agent Skills](https://agentskills.io/specification)
格式，指导 AI 编码代理完成 Unreal Engine 插件开发全流程：C++ 规范、测试、提交工作流、
子模块维护、多引擎适配。每个 skill 是一个包含 `SKILL.md` 入口的文件夹，按需加载。

> **English version**: [README.md](README.md)

两份语言版本保持精确同步 —— 一句话简介与各 skill 自身的 `SKILL.md` description
保持一致；skill 描述变更时，两份文件在同一改动中同步更新。

## 内容分类

**提交与 Git 工作流**

- [`rem-commit-workflow`](rem-commit-workflow/SKILL.md) — 单一职责提交、构建前测试完备性关卡、无头构建与测试
- [`rem-rewrite-commit-history`](rem-rewrite-commit-history/SKILL.md) — 重塑未推送的提交栈（amend / fixup / rebase -i）
- [`rem-submodule-sync`](rem-submodule-sync/SKILL.md) — 更新子模块到远端最新、构建验证、提交
- [`rem-submodule-push`](rem-submodule-push/SKILL.md) — 三轴审计 + 批量推送，以 `--recurse-submodules=check` 为关卡

**C++ 开发规范**

- [`rem-cpp-best-practices`](rem-cpp-best-practices/SKILL.md) — C++ 审查清单（构建设置、文件/头文件结构、命名、const、UPROPERTY 与元数据完整性、优雅实现代理项、日志宏、测试模块）与提交前 checklist
- [`rem-observability-and-profiling`](rem-observability-and-profiling/SKILL.md) — 运行时可见性：何时/记录什么、开关控制的调试绘制、调试器与控制台钩子、性能剖析 scope、stat group 与 CSV 统计
- [`rem-docs-and-config`](rem-docs-and-config/SKILL.md) — 文档与配置义务：技术文档、配置参考、提示文本、与变更联动的文档更新
- [`rem-ranges-transrangers`](rem-ranges-transrangers/SKILL.md) — 用 `Rem::Ranges`、transrangers、`RemStd::bind_back` 编写函数式流水线代码

**UE 模块与编辑器扩展**

- [`rem-create-new-module`](rem-create-new-module/SKILL.md) — 从 RemMyBlank 模板创建新模块或插件
- [`rem-customize-factory-asset-menu`](rem-customize-factory-asset-menu/SKILL.md) — 把自定义 `UFactory` 放到 Content Browser "Add" 菜单的指定分类与子菜单
- [`rem-sequencer-custom-channel-section`](rem-sequencer-custom-channel-section/SKILL.md) — 自定义 `FMovieSceneChannel` / `UMovieSceneSection`，支持逐关键帧结构体编辑
- [`rem-ue-localization`](rem-ue-localization/SKILL.md) — UE 本地化：target 与加载策略、编辑器文本的 namespace+key 查表、gather → 翻译 → compile 管线与验证

**测试**

- [`rem-test-completeness`](rem-test-completeness/SKILL.md) — 提交前关卡：变更→用例映射、五条完备性判定、bug 修复 regression-first
- [`rem-bdd-test-tree`](rem-bdd-test-tree/SKILL.md) — 层级化 BDD 测试树（思维导图式索引）+ 分层审查工作流

**多引擎插件适配**

- [`rem-ue-plugin-adapter`](rem-ue-plugin-adapter/SKILL.md) — 把 UE 插件从上游最新适配到 5.3–5.8，含分支管理与 build-fix-commit 循环

**Skill 元技能**

- [`rem-write-better-skill`](rem-write-better-skill/SKILL.md) — 本集合的 skill 编写约定
- [`rem-public-material-generalization`](rem-public-material-generalization/SKILL.md) — 所有公开材料的发布规则：占位符、提交信息与历史泄漏、逐 skill 的 `local/` overlay、推送前 checklist
- [`rem-session-knowledge-distillation`](rem-session-knowledge-distillation/SKILL.md) — 将会话中可复用的知识点沉淀到新文档，或对现有文档 / skill 进行改进与补充

**主会话编排**

- [`rem-orchestration`](rem-orchestration/SKILL.md) — 主会话的委派机制、迭代/冻结点节奏、run 目录与等待纪律

**环境约束**

- [`rem-no-disk-scanning`](rem-no-disk-scanning/SKILL.md) — 始终加载：禁用磁盘扫描器（`rg`、`grep`、`find`、`fd`、ripgrep、findstr），所有文本搜索走项目的 MCP 服务器（Rider MCP）；这些工具已由配置从 agent 工具集中移除
- [`rem-temp-files`](rem-temp-files/SKILL.md) — 始终加载：临时文件默认放系统 TEMP 目录；只有后续读者需要的才持久化到 run/artifact 目录，绝不落工作树

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
  - 提交 — `rem-commit-workflow`（message、hygiene、完备性关卡、构建、无头测试）；项目事实来自其 `local/` overlay
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
包含触发条件、结尾 checklist、体量预算（>32KB 告警 / >48KB 失败，不含
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

它是**本地门禁**，不是 CI 任务——检查必须在变更离开本机之前通过，而不是推送之后。
每个克隆安装一次：

```bash
git config core.hooksPath .githooks
```

## 项目笔记

- [`orchestration-policy.md`](orchestration-policy.md) —— 主会话的**常驻硬规则**（禁扫盘、委派默认值、只编译的迭代、事件驱动等待）；其背后的流程在 `rem-orchestration` 技能里。它是项目根目录 `AGENTS.md` 软链接的源文件，指向该软链接的 harness 加载的正是这份文件。与根目录的两份 README 一样，它是仓库文档，不是 skill。

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
