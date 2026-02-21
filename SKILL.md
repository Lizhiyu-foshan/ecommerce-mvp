---
name: bmad-method
metadata:
  openclaw:
    emoji: 🚀
    requires:
      bins: ["opencode"]
    install:
      - id: npm
        kind: npm
        package: "@opencode-ai/opencode"
        bins: ["opencode"]
---

# BMAD-METHOD for OpenClaw

将 **BMAD-METHOD** (Breakthrough Method of Agile AI Driven Development) 引入 OpenClaw，实现完整的敏捷开发流程。

## 什么是 BMAD-METHOD？

BMAD-METHOD 是一个突破性的 AI 代理编排框架，通过专门的 AI 代理模拟完整的敏捷开发团队，让一个人就能拥有整个团队的力量。

**核心理念**: 不是让 AI 替你写代码，而是让 AI 帮你更专业地写代码。

## 特点

- 🎭 **7 个专业 Agent** - 从分析师到 QA，完整覆盖
- ⚡ **关键路径并行** - 架构师和 UX 可同时工作
- 🔄 **双模式支持** - 快速流程 (Quick Flow) 和完整流程 (Full Flow)
- 🔗 **OpenCode 集成** - 利用 opencode CLI 启动多 Agent
- 📝 **完整文档输出** - PRD、架构文档、UX 设计、测试报告

## 安装

```bash
# 方式 1: 通过 OpenClaw 安装
openclaw skill install bmad-method

# 方式 2: 手动安装
cd /root/.openclaw/skills
git clone https://github.com/your-username/bmad-method.git
```

## 快速开始

```bash
# 进入项目目录
cd /path/to/your/project

# 显示帮助
bmad-help

# 执行快速流程 (小功能)
bmad-quick

# 执行完整流程 (新产品)
bmad-full

# 单独执行某个角色
bmad-analyst      # 业务分析师
bmad-pm           # 产品经理
bmad-architect    # 架构师
bmad-dev          # 开发者
bmad-qa           # QA 工程师
```

## 命令列表

| 命令 | 角色 | 说明 | 时间 |
|------|------|------|------|
| `bmad-help` | - | 显示帮助信息 | - |
| `bmad-analyst` | 业务分析师 | 创建项目简报 | 10min |
| `bmad-pm` | 产品经理 | 创建产品需求文档 | 15min |
| `bmad-architect` | 架构师 | 创建架构设计文档 | 20min |
| `bmad-ux` | UX 设计师 | 创建 UX 设计文档 | 20min |
| `bmad-sm` | Scrum Master | 规划 Sprint | 10min |
| `bmad-dev` | 开发者 | 开发用户故事 | 30min |
| `bmad-qa` | QA 工程师 | 代码审查 | 10min |
| `bmad-quick` | 多角色 | 快速开发流程 | 15min |
| `bmad-full` | 全角色 | 完整开发流程 | 2h |

## 工作流程

### 快速流程 (Quick Flow)
适合小功能开发和 bug 修复，三步完成：

```
分析师 → 开发者 → QA
 10min    15min    5min
```

### 完整流程 (Full Flow)
适合新产品开发或大型重构：

```
Phase 1: 规划 (串行)
  ├── product-brief (分析师) 10min
  └── create-prd (产品经理) 15min

Phase 2: 设计 (并行) ⭐
  ├── create-architecture (架构师) 20min
  └── create-ux (UX设计师) 20min

Phase 3: Sprint 规划 (串行)
  └── sprint-planning (Scrum Master) 10min

Phase 4: 开发 (循环)
  └── 重复: create-story → dev-story → code-review
```

**并行优化**: Phase 2 可节省 20 分钟 (40%)

## Agent 角色详情

### 业务分析师 (Analyst)
- **职责**: 市场调研、需求收集、用户画像
- **输出**: 项目简报 (Project Brief)
- **并行**: 可独立启动

### 产品经理 (PM)
- **职责**: PRD 创建、功能优先级、产品路线图
- **输出**: 产品需求文档 (PRD)、Epic
- **依赖**: 分析师输出

### 架构师 (Architect) ⭐ 可并行
- **职责**: 系统设计、技术选型、API 设计
- **输出**: 架构设计文档 (ADR)
- **依赖**: PRD
- **并行**: 可与 UX 同时工作

### UX 设计师 (UX) ⭐ 可并行
- **职责**: 用户流程、界面设计、原型
- **输出**: UX 设计文档
- **依赖**: PRD
- **并行**: 可与架构师同时工作

### Scrum Master
- **职责**: Sprint 规划、故事拆分、进度跟踪
- **输出**: Sprint 计划、用户故事
- **依赖**: 架构 + UX

### 开发者 (Developer)
- **职责**: 编码实现、单元测试、代码提交
- **输出**: 可运行的代码
- **依赖**: Sprint 计划

### QA 工程师 (QA)
- **职责**: 代码审查、测试策略、质量保证
- **输出**: 测试报告、审查意见
- **依赖**: 开发输出

## 配置

编辑 `~/.openclaw/skills/bmad-method/config.yaml`:

```yaml
settings:
  default_model: "kimi-coding/k2p5"
  max_parallel_agents: 5
  timeout_minutes: 30

integrations:
  opencode:
    enabled: true
```

## 输出结构

```
your-project/
├── docs/
│   ├── project-brief.md      # 项目简报
│   ├── prd.md                # 产品需求文档
│   ├── architecture.md       # 架构设计
│   ├── ux-design.md          # UX 设计
│   ├── sprint-plan.md        # Sprint 计划
│   ├── story-1.md            # 用户故事 1
│   ├── story-2.md            # 用户故事 2
│   └── review-1.md           # 审查报告
├── src/                      # 源代码
└── tests/                    # 测试代码
```

## 最佳实践

### 1. 选择合适的流程
- **小功能/bug** → Quick Flow (10-15分钟)
- **新模块** → 完整流程的 Phase 3-4
- **新产品** → 完整流程全阶段 (1-2小时)

### 2. 利用并行优势
- 架构师和 UX 设计师可以同时工作
- 多个开发者可以并行开发不同 Story
- QA 可以在开发完成后立即介入

### 3. 迭代优化
- 每个 Sprint 结束后回顾
- 根据项目特点调整 Agent 配置
- 积累项目特定的模板和最佳实践

## 故障排除

### Agent 启动失败
```bash
# 检查 OpenCode 安装
opencode --version

# 检查配置
cat ~/.openclaw/skills/bmad-method/config.yaml
```

### 任务超时
```bash
# 调整超时时间
export BMAD_TIMEOUT=60  # 60分钟
```

## 许可证

MIT License

## 致谢

- [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) - 原始框架
- [OpenCode](https://github.com/opencode-ai/opencode) - Agent 引擎
- [Kimi](https://kimi.moonshot.cn) - AI 模型
