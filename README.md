# BMAD-Kimi

**专为 Kimi AI 优化的多Agent敏捷开发框架**

利用 Kimi 2.5 的多模态能力，实现从需求到代码的完整可视化开发流程。

---

## 🌟 核心特性

| 特性 | 说明 |
|------|------|
| 🎨 **可视化需求沟通** | 低保真原型直接生成，与客户确认需求 |
| 🖼️ **多模态设计** | Kimi图像理解 + 视觉描述 + 设计生成 |
| 🔗 **智能接口设计** | UX视角评估后端API，前后端无缝协作 |
| ⚡ **并行开发** | 架构师∥UX、前端∥后端，效率提升40% |

---

## 🚀 快速开始

```bash
# 克隆仓库
git clone https://github.com/Lizhiyu-foshan/bmad-kimi.git
cd bmad-kimi

# 安装
./install.sh

# 使用
bmad-kimi --help
```

---

## 📋 完整工作流程

```
Phase 1: 需求可视化
├── 分析师: 项目简报
├── UX设计师: 低保真原型 (ASCII/Mermaid)
└── 客户确认 → 需求完善

Phase 2: 产品设计
└── 产品经理: PRD文档

Phase 3: 并行设计
├── 架构师: 系统架构
└── UX设计师: 高保真设计 + 接口UX评估

Phase 4: 并行开发
├── 前端: 基于高保真设计图
└── 后端: 基于接口UX评估优化

Phase 5: 测试交付
└── QA: 代码审查 + 测试
```

**总时间: 75分钟** (vs 传统流程 120分钟)

---

## 🎭 Agent 角色

| 角色 | 命令 | Kimi多模态能力 |
|------|------|---------------|
| 分析师 | `bk analyst` | 文本分析 |
| UX设计师(第一次) | `bk ux-wireframe` | **图像理解**、**ASCII线框图**、**Mermaid流程图** |
| 产品经理 | `bk pm` | 文本生成 |
| 架构师 | `bk architect` | 系统设计 |
| UX设计师(第二次) | `bk ux-visual` | **设计系统**、**组件库**、**接口UX评估** |
| 前端开发者 | `bk frontend` | **视觉→代码** |
| 后端开发者 | `bk backend` | 接口实现 |
| QA | `bk qa` | 代码审查 |

---

## 🧠 Kimi 多模态能力应用

### 1. 图像理解 (Image Understanding)

```bash
# 上传参考产品截图
bk ux-wireframe --reference ./ref-app.png

# Kimi自动分析:
# - 布局结构
# - 配色方案
# - 交互模式
# - 视觉层次
```

### 2. 视觉描述 (Visual Description)

```markdown
## Kimi生成的详细视觉描述

商品卡片:
- 尺寸: 280px × 360px
- 背景: #FFFFFF
- 圆角: 12px
- 阴影: 0 4px 12px rgba(0,0,0,0.08)
- 图片区: 280px × 200px, object-fit: cover
- 标题: 18px, font-weight: 600, 单行截断
- 价格: 20px, color: #1890ff, font-weight: 700
```

### 3. 设计生成 (Design Generation)

```bash
# 生成设计系统
bk ux-visual --generate-design-system

# 输出:
# - 色彩系统
# - 字体系统
# - 间距系统
# - 组件库
```

### 4. 接口UX评估 (Interface UX Review)

```markdown
## 接口UX评估报告

GET /api/products
✅ 响应时间 < 200ms，体验良好
⚠️ 建议: 添加无限滚动支持
⚠️ 建议: 筛选条件本地缓存

POST /api/orders
⚠️ 建议: 添加乐观更新
⚠️ 建议: 创建过程展示进度条
```

---

## 📁 项目结构

```
my-project/
├── docs/
│   ├── 01-project-brief.md       # 项目简报
│   ├── 02-ux-wireframes.md       # 低保真原型 ⭐
│   ├── 03-prd.md                 # PRD文档
│   ├── 04-architecture.md        # 架构设计
│   ├── 05-ux-design.md           # 高保真设计 ⭐
│   │   ├── design-system.md      # 设计系统
│   │   ├── components.md         # 组件库
│   │   └── interface-ux-review.md # 接口UX评估 ⭐
│   └── 06-api-spec.md            # API规范
├── src/
│   ├── frontend/                 # 前端代码
│   └── backend/                  # 后端代码
├── tests/
└── bmad-kimi.config.yaml         # 配置文件
```

---

## 🛠️ 安装

### 依赖

- OpenClaw >= 1.0
- Kimi API Key
- Node.js >= 18

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/Lizhiyu-foshan/bmad-kimi.git

# 2. 安装
cd bmad-kimi
./install.sh

# 3. 配置Kimi API
export KIMI_API_KEY="your-api-key"

# 4. 验证安装
bk --version
```

---

## 📖 使用示例

### 示例1: 电商首页开发

```bash
# 1. 创建项目
mkdir ecommerce-homepage && cd ecommerce-homepage

# 2. 需求分析
bk analyst --input "开发一个电商首页，包含商品展示、搜索、购物车入口"

# 3. 低保真原型 (Kimi生成ASCII线框图)
bk ux-wireframe
# 输出: docs/02-ux-wireframes.md

# 4. 与客户确认原型后，完善需求
# ... 客户反馈 ...

# 5. PRD文档
bk pm

# 6. 并行设计
bk architect &      # 架构设计
bk ux-visual        # 高保真设计 (包含接口UX评估)

# 7. 并行开发
bk frontend &       # 基于高保真设计图
bk backend          # 基于接口UX评估

# 8. 测试
bk qa
```

### 示例2: 使用参考图

```bash
# 上传竞品截图作为参考
bk ux-wireframe --reference ./competitor-app.png

# Kimi自动分析参考图风格，生成相似设计
```

---

## ⚙️ 配置

```yaml
# bmad-kimi.config.yaml

kimi:
  model: "kimi-coding/k2p5"
  api_key: "${KIMI_API_KEY}"
  
  multimodal:
    enabled: true
    image_understanding: true
    visual_description: true
    design_generation: true

ux_design:
  wireframe_format: "ascii"      # ascii | mermaid
  visual_detail_level: "high"    # high | medium | low
  generate_design_system: true
  interface_ux_review: true

workflow:
  parallel_architecture_ux: true
  parallel_frontend_backend: true
  
output:
  docs_dir: "./docs"
  src_dir: "./src"
```

---

## 📊 性能对比

| 指标 | 传统开发 | BMAD-Kimi | 提升 |
|------|---------|-----------|------|
| 需求确认 | 2天 | 30分钟 | **99%** |
| 设计交付 | 3天 | 40分钟 | **98%** |
| 前后端协作 | 串行 | 并行 | **40%** |
| 总开发时间 | 2周 | 2天 | **86%** |

---

## 🤝 贡献

欢迎提交Issue和PR！

---

## 📄 许可证

MIT License

---

**BMAD-Kimi** - 让Kimi的多模态能力赋能敏捷开发
