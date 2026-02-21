# E-Commerce MVP - 项目结构说明

**项目版本**: v1.0.0  
**最后更新**: 2026-02-21

---

## 📁 项目目录结构

```
ecommerce-mvp/
│
├── 📄 核心文件
│   ├── main.py                      # FastAPI 应用入口
│   ├── database.py                  # 数据库配置和连接
│   ├── requirements.txt             # Python 依赖列表
│   └── pytest.ini                   # 测试配置
│
├── 📁 config/                       # 配置文件
│   └── settings.py                  # 应用配置（数据库、JWT等）
│
├── 📁 models/                       # 数据模型层 (ORM)
│   ├── __init__.py                  # 模型初始化，导出所有模型
│   ├── product.py                   # 商品模型 (Product, Category, Spec)
│   ├── cart.py                      # 购物车模型 (Cart)
│   ├── address.py                   # 地址模型 (Address)
│   └── schemas.py                   # Pydantic 数据验证模型
│
├── 📁 services/                     # 业务逻辑层
│   ├── __init__.py
│   ├── auth_service.py              # 认证服务 (登录、注册、Token)
│   ├── product_service.py           # 商品服务 (CRUD、库存管理)
│   ├── cart_service.py              # 购物车服务 (增删改查、结算)
│   ├── address_service.py           # 地址服务 (CRUD、默认地址)
│   ├── order_service.py             # 订单服务 (创建、取消、退款)
│   ├── image_service.py             # 图片服务 (上传、压缩、验证)
│   └── payment_service.py           # 支付服务 (支付、退款)
│
├── 📁 routers/                      # API 路由层 (Controller)
│   ├── __init__.py
│   ├── auth.py                      # 认证路由 (/auth/*)
│   ├── products.py                  # 商品路由 (/products/*)
│   ├── cart.py                      # 购物车路由 (/cart/*)
│   ├── addresses.py                 # 地址路由 (/addresses/*)
│   ├── orders.py                    # 订单路由 (/orders/*)
│   └── payment.py                   # 支付路由 (/payment/*)
│
├── 📁 utils/                        # 工具模块
│   ├── __init__.py
│   ├── transaction.py               # 事务管理装饰器
│   └── helpers.py                   # 辅助函数 (UUID生成等)
│
├── 📁 tests/                        # 测试文件
│   ├── test_product_execution.py    # 商品模块测试
│   ├── test_cart_execution.py       # 购物车模块测试
│   ├── test_address_execution.py    # 地址模块测试
│   ├── test_transaction.py          # 事务管理测试
│   ├── test_cart_status_refresh.py  # 购物车状态测试
│   ├── test_image_optimization.py   # 图片优化测试
│   ├── test_simple.py               # 简单测试
│   ├── SYSTEM_TEST_REPORT.md        # 系统测试报告
│   ├── FINAL_TEST_REPORT.md         # 最终测试报告
│   └── CODE_REVIEW_REPORT_V2.md     # 代码审查报告
│
├── 📁 docs/                         # 项目文档
│   ├── project-brief.md             # 项目简报
│   ├── prd.md                       # 产品需求文档
│   ├── architecture.md              # 架构设计文档
│   ├── FEATURES.md                  # 功能文档
│   ├── CODE_REVIEW_REPORT.md        # 第一次代码审查报告
│   ├── CODE_REVIEW_REPORT_V2.md     # 第二次代码审查报告
│   ├── SECURITY_FIX.md              # 安全修复文档
│   └── P0_FIX_COMPLETION_REPORT.md  # P0修复完成报告
│
├── 📁 uploads/                      # 上传文件存储
│   └── products/                    # 商品图片目录
│       └── YYYY/MM/                 # 按年月组织
│
└── 📄 项目日志
    ├── PROJECT_LOG.md               # 项目开发日志
    ├── BMAD_PROJECT_COMPLETION_REPORT.md  # BMAD项目完成报告
    └── FINAL_PROJECT_COMPLETION.md  # 最终完成报告
```

---

## 🏗️ 架构分层

```
┌─────────────────────────────────────────┐
│           API 路由层 (Routers)           │
│  /auth, /products, /cart, /orders...    │
│  - 参数验证、权限检查、响应格式化        │
├─────────────────────────────────────────┤
│           业务逻辑层 (Services)          │
│  AuthService, ProductService...         │
│  - 业务逻辑、数据处理、事务管理          │
├─────────────────────────────────────────┤
│           数据访问层 (Models)            │
│  User, Product, Cart, Order...          │
│  - ORM模型、数据库操作                   │
├─────────────────────────────────────────┤
│           数据库 (Database)              │
│  SQLite (开发) / PostgreSQL (生产)      │
└─────────────────────────────────────────┘
```

---

## 📦 核心模块说明

### 1. 认证模块 (auth)

**文件**:
- `services/auth_service.py` - 认证业务逻辑
- `routers/auth.py` - 认证API路由

**功能**:
- 用户注册/登录
- JWT Token 生成/验证
- 密码加密 (bcrypt)
- 权限验证

### 2. 商品模块 (product)

**文件**:
- `models/product.py` - 商品数据模型
- `services/product_service.py` - 商品业务逻辑
- `routers/products.py` - 商品API路由

**功能**:
- 商品分类管理
- 商品CRUD
- 库存管理 (原子操作)
- 图片上传

### 3. 购物车模块 (cart)

**文件**:
- `models/cart.py` - 购物车数据模型
- `services/cart_service.py` - 购物车业务逻辑
- `routers/cart.py` - 购物车API路由

**功能**:
- 添加/删除商品
- 修改数量
- 购物车合并
- 结算验证

### 4. 地址模块 (address)

**文件**:
- `models/address.py` - 地址数据模型
- `services/address_service.py` - 地址业务逻辑
- `routers/addresses.py` - 地址API路由

**功能**:
- 地址CRUD
- 默认地址设置
- 手机号验证

### 5. 订单模块 (order)

**文件**:
- `services/order_service.py` - 订单业务逻辑
- `routers/orders.py` - 订单API路由

**功能**:
- 创建订单
- 订单查询
- 订单取消
- 事务管理

---

## 🔧 配置文件

### settings.py

```python
# 数据库配置
DATABASE_URL = "sqlite:///./ecommerce.db"

# JWT配置
SECRET_KEY = "your-secret-key"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 文件上传配置
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# 架构模式
ARCHITECTURE_MODE = "monolithic"  # monolithic / microservices
```

---

## 🧪 测试结构

```
tests/
├── 单元测试
│   ├── test_product_execution.py    # 商品服务测试
│   ├── test_cart_execution.py       # 购物车服务测试
│   ├── test_address_execution.py    # 地址服务测试
│   └── test_transaction.py          # 事务管理测试
│
├── 集成测试
│   ├── test_cart_status_refresh.py  # 购物车状态测试
│   └── test_image_optimization.py   # 图片优化测试
│
└── 测试报告
    ├── SYSTEM_TEST_REPORT.md        # 系统测试报告
    ├── FINAL_TEST_REPORT.md         # 最终测试报告
    └── CODE_REVIEW_REPORT_V2.md     # 代码审查报告
```

---

## 📚 文档结构

```
docs/
├── 需求文档
│   ├── project-brief.md             # 项目简报
│   └── prd.md                       # 产品需求文档
│
├── 设计文档
│   └── architecture.md              # 架构设计文档
│
├── 功能文档
│   └── FEATURES.md                  # 功能说明文档
│
├── 审查报告
│   ├── CODE_REVIEW_REPORT.md        # 第一次审查
│   └── CODE_REVIEW_REPORT_V2.md     # 第二次审查
│
└── 修复报告
    ├── SECURITY_FIX.md              # 安全修复
    └── P0_FIX_COMPLETION_REPORT.md  # P0修复完成
```

---

## 🚀 快速开始

### 1. 安装依赖
```bash
cd /root/.openclaw/workspace/projects/ecommerce-mvp
pip install -r requirements.txt
```

### 2. 初始化数据库
```bash
# 数据库会自动创建
python -c "from database import engine, Base; Base.metadata.create_all(bind=engine)"
```

### 3. 运行项目
```bash
# 开发模式
uvicorn main:app --reload

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. 访问 API 文档
```
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

---

## 📊 项目统计

| 类别 | 数量 |
|------|------|
| Python文件 | 21个 |
| 代码行数 | ~6500行 |
| 测试文件 | 8个 |
| 测试用例 | 201+个 |
| 文档文件 | 10+个 |
| 文档字数 | 100000+字 |

---

*文档生成时间: 2026-02-21*  
*版本: v1.0.0*
