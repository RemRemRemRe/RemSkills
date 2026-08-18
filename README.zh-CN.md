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

- [`rem-cpp-best-practices`](rem-cpp-best-practices/SKILL.md) — C++ 审查清单（构建设置、文件/头文件结构、命名、const、UPROPERTY、日志、测试模块）与提交前 checklist
- [`rem-ranges-transrangers`](rem-ranges-transrangers/SKILL.md) — 用 `Rem::Ranges`、transrangers、`RemStd::bind_back` 编写函数式流水线代码

**UE 模块与编辑器扩展**

- [`rem-create-new-module`](rem-create-new-module/SKILL.md) — 从 RemMyBlank 模板创建新模块或插件
- [`rem-customize-factory-asset-menu`](rem-customize-factory-asset-menu/SKILL.md) — 把自定义 `UFactory` 放到 Content Browser "Add" 菜单的指定分类与子菜单
- [`rem-sequencer-custom-channel-section`](rem-sequencer-custom-channel-section/SKILL.md) — 自定义 `FMovieSceneChannel` / `UMovieSceneSection`，支持逐关键帧结构体编辑

**测试**

- [`rem-test-completeness`](rem-test-completeness/SKILL.md) — 提交前关卡：变更→用例映射、五条完备性判定、bug 修复 regression-first
- [`rem-bdd-test-tree`](rem-bdd-test-tree/SKILL.md) — 层级化 BDD 测试树（思维导图式索引）+ 分层审查工作流

**多引擎插件适配**

- [`rem-ue-plugin-adapter`](rem-ue-plugin-adapter/SKILL.md) — 把 UE 插件从上游最新适配到 5.3–5.8，含分支管理与 build-fix-commit 循环

**Skill 元技能**

- [`rem-write-better-skill`](rem-write-better-skill/SKILL.md) — 本集合的 skill 编写约定
- [`rem-public-skill-generalization`](rem-public-skill-generalization/SKILL.md) — 发布规则：占位符、私有伴生 skill、推送前 checklist

**环境约束**

- [`rem-no-disk-scanning`](rem-no-disk-scanning/SKILL.md) — 始终加载：禁用 `rg` / `grep` / `fd`，所有文本搜索走 Rider MCP

## 日常参考工作流

- **开始会话** — `rem-no-disk-scanning` 始终加载；所有文本搜索走 Rider MCP
- **编写**
  - 编写 / 审查 C++ — `rem-cpp-best-practices`（规则 + §17 提交前 checklist）；流水线代码用 `rem-ranges-transrangers`
  - 新建模块 / 插件 — `rem-create-new-module`
  - UE 编辑器 / 资产工作 — `rem-customize-factory-asset-menu`、`rem-sequencer-custom-channel-section`
- **测试**
  - 确认测试完备 — `rem-test-completeness`（关卡）；`rem-bdd-test-tree`（审查索引）；spec 模板与运行坑位在 `rem-cpp-best-practices` `references/tests.md`
- **提交与推送**
  - 提交 — `rem-commit-workflow`（message、hygiene、完备性关卡、构建、无头测试）；项目事实来自其 `-local` 伴生 skill
  - 推送前整理历史 — `rem-rewrite-commit-history`
  - 同步 / 推送子模块 — `rem-submodule-sync`、`rem-submodule-push`
- **扩展与维护**
  - 多引擎版本适配 — `rem-ue-plugin-adapter`
  - 编写 / 发布 skill — `rem-write-better-skill`、`rem-public-skill-generalization`

## 安装

- 克隆本仓库（或只复制需要的 skill 文件夹）。每个 skill 自包含于自己的文件夹。
- 让代理加载该集合：使用 [pi](https://github.com/earendil-works/pi) 时，把路径加入
  settings 的 `skills` 数组，或传 `--skill <path>`（可重复）。任何兼容 Agent Skills
  的 harness 均可。
- 项目本地 skill：放在项目的 `.agents/skills` 下（harness 启动时信任）。
- 私有伴生 skill（`*-local`）位于独立的私有仓库（**无公开远端**）—— 见下方分流说明。

## 前置依赖

- 兼容 Agent Skills 的代理 harness（推荐 pi）。
- **Rider MCP** —— `rem-no-disk-scanning` 所必需：文本搜索走 Rider，禁用磁盘扫描器。
- 支持自动化测试的 Unreal Engine 项目（`DEFINE_SPEC` BDD spec + 无头 `-nullrhi` 运行路径）。

## 公开 / 私有分流

公开 skill 只携带泛化知识 —— 通用占位符，不含项目名、路径或内部决策。项目专属事实
放在**私有伴生 skill**（`*-local`，独立私有仓库，永无公开远端）或外部逐插件配置中。
规则单一归属
[`rem-public-skill-generalization`](rem-public-skill-generalization/SKILL.md)。

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
