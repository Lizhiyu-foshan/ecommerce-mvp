# 架构设计文档 (ADR): E-Commerce MVP Phase 1

**版本**: v1.0  
**日期**: 2026-02-21  
**作者**: Winston (架构师)  
**状态**: 草案

---

## 1. 架构概述

### 1.1 设计目标

基于 Phase 1 功能完善需求，设计一个**可扩展、高性能、易维护**的电商系统架构。

**核心目标**:
1. **整合新模块**: 商品、购物车、地址管理无缝整合到现有系统
2. **渐进优化**: 从 SQLite 向 PostgreSQL 平滑迁移
3. **性能提升**: 引入缓存层，减少数据库压力
4. **异步处理**: 关键业务流程异步化，提升响应速度
5. **预留扩展**: 为未来微服务拆分预留接口和设计

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **渐进演进** | 不推翻重来，基于现有架构逐步优化 |
| **模块化** | 各模块独立，降低耦合 |
| **配置化** | 关键参数可配置，支持不同环境 |
| **可观测** | 完善的日志、监控、告警 |
| **安全第一** | 安全设计贯穿始终 |

### 1.3 技术栈选择

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| **后端框架** | FastAPI 0.115+ | 高性能、异步支持、自动文档 |
| **ORM** | SQLAlchemy 2.0+ | 成熟稳定，支持多种数据库 |
| **数据库** | SQLite → PostgreSQL | 开发用 SQLite，生产用 PostgreSQL |
| **缓存** | Redis 7.0+ | 高性能缓存，支持多种数据结构 |
| **消息队列** | Redis + Celery | 轻量级，与缓存复用基础设施 |
| **文件存储** | 本地 + MinIO | 开发用本地，生产用 MinIO (S3兼容) |
| **任务调度** | Celery Beat | 定时任务、异步处理 |
| **监控** | Prometheus + Grafana | 指标采集和可视化 |

### 1.4 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端层                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   Web    │  │  Mobile  │  │   小程序  │  │  第三方   │       │
│  │  浏览器   │  │   App    │  │          │  │   系统    │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API 网关层                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI + Uvicorn                                        │  │
│  │  - 路由分发                                                │  │
│  │  - 认证鉴权 (JWT)                                          │  │
│  │  - 限流熔断                                                │  │
│  │  - 请求日志                                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   业务服务层  │  │   业务服务层  │  │   业务服务层  │
│  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │
│  │  认证  │  │  │  │  商品  │  │  │  │  订单  │  │
│  │  服务  │  │  │  │  服务  │  │  │  │  服务  │  │
│  └────────┘  │  │  └────────┘  │  │  └────────┘  │
│  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │
│  │  用户  │  │  │  │  购物车│  │  │  │  支付  │  │
│  │  服务  │  │  │  │  服务  │  │  │  │  服务  │  │
│  └────────┘  │  │  └────────┘  │  │  └────────┘  │
│  ┌────────┐  │  │  ┌────────┐  │  │              │
│  │  地址  │  │  │  │  库存  │  │  │              │
│  │  服务  │  │  │  │  服务  │  │  │              │
│  └────────┘  │  │  └────────┘  │  │              │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   数据访问层  │  │   缓存层      │  │   消息队列层  │
│  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │
│  │SQLAlchemy│  │  │  Redis  │  │  │  Celery │  │
│  │  ORM   │  │  │  Cache  │  │  │  Worker │  │
│  └────────┘  │  │  └────────┘  │  │  └────────┘  │
│  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │
│  │ 连接池  │  │  │ Session│  │  │  │  Beat  │  │
│  │ 管理   │  │  │  Store │  │  │  │ 定时器 │  │
│  └────────┘  │  │  └────────┘  │  │  └────────┘  │
└──────┬───────┘  └──────────────┘  └──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         数据存储层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   SQLite     │  │  PostgreSQL  │  │    MinIO     │          │
│  │   (开发)     │  │   (生产)     │  │  (文件存储)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据模型设计

### 2.1 新增表结构

#### 商品分类表 (categories)
```sql
CREATE TABLE categories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    parent_id       UUID REFERENCES categories(id),
    sort_order      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_category_name UNIQUE (name)
);

-- 索引
CREATE INDEX idx_categories_parent ON categories(parent_id);
CREATE INDEX idx_categories_active ON categories(is_active);
```

#### 商品表 (products)
```sql
CREATE TABLE products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    price           DECIMAL(10, 2) NOT NULL,
    original_price  DECIMAL(10, 2),
    stock           INTEGER NOT NULL DEFAULT 0,
    category_id     UUID REFERENCES categories(id),
    images          JSONB DEFAULT '[]',  -- [{"url": "...", "sort": 1}]
    status          VARCHAR(20) DEFAULT 'active',  -- active, inactive, deleted
    sort_order      INTEGER DEFAULT 0,
    sales_count     INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT positive_price CHECK (price >= 0),
    CONSTRAINT positive_stock CHECK (stock >= 0)
);

-- 索引
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_status ON products(status);
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_created ON products(created_at DESC);

-- 全文搜索索引 (PostgreSQL)
CREATE INDEX idx_products_search ON products USING gin(to_tsvector('chinese', name || ' ' || COALESCE(description, '')));
```

#### 商品规格表 (product_specs)
```sql
CREATE TABLE product_specs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name            VARCHAR(50) NOT NULL,  -- 颜色、尺寸等
    values          JSONB NOT NULL,  -- ["红色", "蓝色", "黑色"]
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_product_specs_product ON product_specs(product_id);
```

#### 购物车表 (carts)
```sql
CREATE TABLE carts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id      VARCHAR(100),  -- 匿名用户会话ID
    product_id      UUID NOT NULL REFERENCES products(id),
    spec_combo      JSONB DEFAULT '{}',  -- {"颜色": "红色", "尺寸": "XL"}
    quantity        INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT positive_quantity CHECK (quantity > 0),
    CONSTRAINT user_or_session CHECK (user_id IS NOT NULL OR session_id IS NOT NULL)
);

-- 索引
CREATE INDEX idx_carts_user ON carts(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_carts_session ON carts(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX idx_carts_product ON carts(product_id);
```

#### 收货地址表 (addresses)
```sql
CREATE TABLE addresses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,  -- 收件人姓名
    phone           VARCHAR(20) NOT NULL,
    province        VARCHAR(50) NOT NULL,
    city            VARCHAR(50) NOT NULL,
    district        VARCHAR(50) NOT NULL,
    detail          VARCHAR(200) NOT NULL,  -- 详细地址
    zip_code        VARCHAR(10),
    is_default      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_addresses_user ON addresses(user_id);
CREATE INDEX idx_addresses_default ON addresses(user_id, is_default) WHERE is_default = TRUE;
```

### 2.2 与现有表的关联

```
┌─────────────────────────────────────────────────────────────┐
│                        ER 关系图                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐   │
│   │  users   │◄────────┤  orders  ├────────►│ payments │   │
│   └────┬─────┘         └────┬─────┘         └──────────┘   │
│        │                    │                               │
│        │         ┌──────────┘                               │
│        │         │                                          │
│        │    ┌────┴─────┐                                    │
│        └───►│ addresses│                                    │
│             └──────────┘                                    │
│                                                             │
│   ┌──────────┐         ┌──────────┐                        │
│   │categories│◄────────┤ products │◄──────────────────┐    │
│   └──────────┘         └────┬─────┘                   │    │
│                             │                         │    │
│                             │         ┌──────────┐    │    │
│                             └────────►│  carts   ├────┘    │
│                                       └──────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 索引策略

| 表 | 索引 | 用途 |
|----|------|------|
| products | idx_products_category | 按分类查询 |
| products | idx_products_status | 筛选上架商品 |
| products | idx_products_price | 价格区间筛选 |
| products | idx_products_search | 全文搜索 |
| carts | idx_carts_user | 用户购物车查询 |
| carts | idx_carts_session | 匿名购物车查询 |
| addresses | idx_addresses_user | 用户地址列表 |
| addresses | idx_addresses_default | 默认地址快速查询 |

---

## 3. API 设计

### 3.1 RESTful API 规范

**基础路径**: `/api/v1`

**认证方式**: JWT Bearer Token

**响应格式**:
```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100
  }
}
```

### 3.2 新增接口列表

#### 商品分类接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/categories` | 获取分类列表 | 否 |
| GET | `/categories/{id}` | 获取分类详情 | 否 |
| POST | `/categories` | 创建分类 | 管理员 |
| PUT | `/categories/{id}` | 更新分类 | 管理员 |
| DELETE | `/categories/{id}` | 删除分类 | 管理员 |

#### 商品接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/products` | 商品列表 | 否 |
| GET | `/products/{id}` | 商品详情 | 否 |
| GET | `/products/search` | 商品搜索 | 否 |
| POST | `/products` | 创建商品 | 管理员 |
| PUT | `/products/{id}` | 更新商品 | 管理员 |
| DELETE | `/products/{id}` | 删除商品 | 管理员 |
| POST | `/products/{id}/images` | 上传图片 | 管理员 |

**查询参数示例**:
```
GET /api/v1/products?
  category_id=xxx&
  min_price=10&
  max_price=100&
  keyword=手机&
  sort_by=price&
  sort_order=desc&
  page=1&
  page_size=20
```

#### 购物车接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/cart` | 获取购物车 | 可选 |
| POST | `/cart/items` | 添加商品 | 可选 |
| PUT | `/cart/items/{id}` | 修改数量 | 是 |
| DELETE | `/cart/items/{id}` | 删除商品 | 是 |
| DELETE | `/cart` | 清空购物车 | 是 |
| POST | `/cart/checkout` | 购物车结算 | 是 |

#### 地址接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/addresses` | 地址列表 | 是 |
| GET | `/addresses/{id}` | 地址详情 | 是 |
| POST | `/addresses` | 添加地址 | 是 |
| PUT | `/addresses/{id}` | 更新地址 | 是 |
| DELETE | `/addresses/{id}` | 删除地址 | 是 |
| PUT | `/addresses/{id}/default` | 设为默认 | 是 |

### 3.3 与现有接口的兼容性

**订单接口扩展**:
```python
# 原有接口
POST /orders  # 直接创建订单

# 新增支持购物车结算
POST /orders
{
  "cart_id": "xxx",  # 新增：从购物车创建
  "address_id": "xxx",
  "payment_method": "alipay"
}
```

---

## 4. 数据持久化策略

### 4.1 SQLite vs PostgreSQL 对比

| 特性 | SQLite | PostgreSQL | 建议 |
|------|--------|------------|------|
| **适用场景** | 开发测试、单机 | 生产环境、高并发 | 开发用 SQLite，生产用 PostgreSQL |
| **并发性能** | 一般 | 优秀 | 生产环境必须 PostgreSQL |
| **数据类型** | 基础 | 丰富 (JSONB, Array) | PostgreSQL 支持更复杂数据 |
| **全文搜索** | 有限 | 强大 | PostgreSQL 支持中文全文搜索 |
| **扩展性** | 无 | 丰富 | PostgreSQL 支持分区、复制 |
| **运维成本** | 低 | 中 | 使用云数据库降低运维成本 |

### 4.2 迁移方案

**配置化切换**:
```python
# config/settings.py
class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "sqlite:///./ecommerce.db"
    # 生产环境: postgresql://user:pass@localhost/ecommerce
    
    # 连接池配置 (PostgreSQL)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
```

**迁移步骤**:
1. 使用 `pgloader` 或自定义脚本迁移数据
2. 验证数据一致性
3. 切换数据库连接配置
4. 运行回归测试

### 4.3 连接池配置

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings

if settings.DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,  # 自动检测连接有效性
        echo=settings.DEBUG
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

---

## 5. 缓存策略

### 5.1 缓存架构

```
┌─────────────────────────────────────────┐
│           缓存分层架构                   │
├─────────────────────────────────────────┤
│                                         │
│  L1: 应用内存缓存 (LRU)                  │
│  ├── 用户会话信息                        │
│  └── 配置信息                            │
│                                         │
│  L2: Redis 分布式缓存                    │
│  ├── 商品列表 (TTL: 5分钟)               │
│  ├── 商品详情 (TTL: 10分钟)              │
│  ├── 购物车数据 (TTL: 30分钟)            │
│  └── 热点数据                            │
│                                         │
│  L3: 数据库                              │
│  └── 持久化存储                          │
│                                         │
└─────────────────────────────────────────┘
```

### 5.2 缓存数据类型

| 数据类型 | 缓存键 | TTL | 更新策略 |
|----------|--------|-----|----------|
| 商品列表 | `products:list:{hash}` | 5分钟 | 主动更新+过期 |
| 商品详情 | `product:{id}` | 10分钟 | 主动更新+过期 |
| 购物车 | `cart:{user_id}` | 30分钟 | 实时更新 |
| 用户地址 | `addresses:{user_id}` | 60分钟 | 主动更新 |
| 分类树 | `categories:tree` | 60分钟 | 主动更新 |

### 5.3 缓存更新策略

**Cache-Aside (旁路缓存)**:
```python
class ProductService:
    async def get_product(self, product_id: str):
        # 1. 先查缓存
        cache_key = f"product:{product_id}"
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # 2. 缓存未命中，查数据库
        product = await db.query(Product).filter(Product.id == product_id).first()
        if product:
            # 3. 写入缓存
            await redis.setex(cache_key, 600, json.dumps(product.to_dict()))
        
        return product
    
    async def update_product(self, product_id: str, data: dict):
        # 1. 更新数据库
        await db.query(Product).filter(Product.id == product_id).update(data)
        await db.commit()
        
        # 2. 删除缓存 (或更新缓存)
        cache_key = f"product:{product_id}"
        await redis.delete(cache_key)
        await redis.delete("products:list:*")  # 清除列表缓存
```

### 5.4 缓存穿透/击穿防护

**缓存穿透防护 (Bloom Filter)**:
```python
# 使用 Redis Bloom Filter 判断商品是否存在
async def get_product_with_protection(product_id: str):
    # 1. Bloom Filter 检查
    exists = await redis.bf.exists("products:bloom", product_id)
    if not exists:
        return None  # 商品肯定不存在，直接返回
    
    # 2. 正常缓存流程
    return await get_product(product_id)
```

**缓存击穿防护 (互斥锁)**:
```python
async def get_product_with_lock(product_id: str):
    cache_key = f"product:{product_id}"
    lock_key = f"lock:{cache_key}"
    
    # 1. 查缓存
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # 2. 获取分布式锁
    lock = await redis.set(lock_key, "1", nx=True, ex=10)
    if not lock:
        # 未获取到锁，等待后重试
        await asyncio.sleep(0.1)
        return await get_product_with_lock(product_id)
    
    try:
        # 3. 双重检查
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # 4. 查询数据库并缓存
        product = await db.query(Product).filter(Product.id == product_id).first()
        if product:
            await redis.setex(cache_key, 600, json.dumps(product.to_dict()))
        return product
    finally:
        await redis.delete(lock_key)
```

---

## 6. 队列策略

### 6.1 消息队列选型

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **Redis List** | 简单、无额外依赖 | 功能有限 | 简单任务队列 |
| **Celery + Redis** | 成熟、功能丰富 | 额外依赖 | 复杂异步任务 |
| **RabbitMQ** | 专业、可靠 | 运维复杂 | 大规模生产环境 |

**推荐**: Celery + Redis (与缓存复用基础设施)

### 6.2 使用场景

| 场景 | 处理方式 | 优先级 |
|------|----------|--------|
| **订单超时取消** | 延迟队列 | 高 |
| **库存扣减** | 异步处理 | 高 |
| **支付回调处理** | 异步处理 | 高 |
| **邮件/短信通知** | 异步发送 | 中 |
| **日志异步写入** | 批量处理 | 低 |
| **数据统计** | 定时任务 | 低 |

### 6.3 任务处理流程

```python
# tasks/order_tasks.py
from celery import Celery
from datetime import timedelta

app = Celery('ecommerce', broker='redis://localhost:6379/0')

@app.task
def cancel_overdue_order(order_id: str):
    """取消超时未支付订单"""
    order = get_order(order_id)
    if order.status == "pending_payment":
        order.status = "cancelled"
        # 恢复库存
        restore_stock(order.items)
        save_order(order)
        logger.info(f"Order {order_id} cancelled due to timeout")

@app.task
def process_payment_callback(payment_data: dict):
    """异步处理支付回调"""
    try:
        verify_payment(payment_data)
        update_order_status(payment_data['order_id'], "paid")
        send_notification.delay(payment_data['user_id'], "支付成功")
    except Exception as e:
        logger.error(f"Payment callback failed: {e}")
        raise  # 失败重试

@app.task(bind=True, max_retries=3)
def deduct_stock(self, product_id: str, quantity: int):
    """异步扣减库存"""
    try:
        product = get_product(product_id)
        if product.stock >= quantity:
            product.stock -= quantity
            save_product(product)
        else:
            raise ValueError("库存不足")
    except Exception as exc:
        # 重试策略：指数退避
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

# 延迟任务示例
def schedule_order_timeout(order_id: str):
    """15分钟后检查订单是否支付"""
    cancel_overdue_order.apply_async(
        args=[order_id],
        countdown=15 * 60  # 15分钟
    )
```

### 6.4 失败重试机制

| 任务类型 | 重试次数 | 重试间隔 | 失败处理 |
|----------|----------|----------|----------|
| 支付回调 | 3次 | 指数退避 | 人工介入 |
| 库存扣减 | 3次 | 指数退避 | 回滚订单 |
| 邮件发送 | 3次 | 固定间隔 | 记录日志 |
| 数据统计 | 1次 | 立即 | 跳过 |

---

## 7. 文件存储

### 7.1 存储方案

| 环境 | 方案 | 说明 |
|------|------|------|
| **开发** | 本地文件系统 | 简单，无需额外配置 |
| **测试** | MinIO | S3 兼容，本地部署 |
| **生产** | 阿里云 OSS / AWS S3 | 高可用，CDN 加速 |

### 7.2 图片处理

```python
# services/image_service.py
from PIL import Image
import io

class ImageService:
    ALLOWED_FORMATS = {'JPEG', 'PNG', 'WebP'}
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    
    async def upload_product_image(self, file: UploadFile, product_id: str):
        # 1. 验证文件
        if file.size > self.MAX_SIZE:
            raise ValueError("图片大小超过 5MB")
        
        # 2. 读取并处理图片
        image = Image.open(file.file)
        if image.format not in self.ALLOWED_FORMATS:
            raise ValueError(f"不支持的图片格式: {image.format}")
        
        # 3. 压缩图片
        # 大图: 800x800
        large = self._resize_image(image, (800, 800))
        large_url = await self._upload_to_storage(large, f"products/{product_id}/large.jpg")
        
        # 缩略图: 200x200
        thumb = self._resize_image(image, (200, 200))
        thumb_url = await self._upload_to_storage(thumb, f"products/{product_id}/thumb.jpg")
        
        return {
            "large": large_url,
            "thumbnail": thumb_url,
            "original_name": file.filename
        }
    
    def _resize_image(self, image: Image.Image, size: tuple) -> bytes:
        """等比缩放图片"""
        image.thumbnail(size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
```

### 7.3 CDN 策略

```python
# config/settings.py
class Settings(BaseSettings):
    # 文件存储配置
    STORAGE_TYPE: str = "local"  # local, minio, oss, s3
    
    # CDN 配置
    CDN_DOMAIN: str = "https://cdn.example.com"
    CDN_ENABLED: bool = False
    
    # 本地存储路径
    LOCAL_STORAGE_PATH: str = "./uploads"
    
    # OSS 配置 (生产环境)
    OSS_ACCESS_KEY: str = ""
    OSS_SECRET_KEY: str = ""
    OSS_BUCKET: str = ""
    OSS_ENDPOINT: str = ""

# 使用 CDN URL
def get_image_url(image_path: str) -> str:
    if settings.CDN_ENABLED:
        return f"{settings.CDN_DOMAIN}/{image_path}"
    return f"/uploads/{image_path}"
```

---

## 8. 模块整合方案

### 8.1 目录结构

```
ecommerce-mvp/
├── main.py                    # 应用入口
├── config/
│   ├── settings.py           # 配置
│   ├── logging_config.py     # 日志配置
│   └── celery_config.py      # Celery 配置 (新增)
├── database.py               # 数据库连接
├── models/                   # 数据模型
│   ├── __init__.py
│   ├── user.py              # 用户模型 (已有)
│   ├── order.py             # 订单模型 (已有)
│   ├── payment.py           # 支付模型 (已有)
│   ├── product.py           # 商品模型 (新增)
│   ├── category.py          # 分类模型 (新增)
│   ├── cart.py              # 购物车模型 (新增)
│   └── address.py           # 地址模型 (新增)
├── services/                # 业务服务层
│   ├── __init__.py
│   ├── auth_service.py      # 认证服务 (已有)
│   ├── order_service.py     # 订单服务 (已有)
│   ├── payment_service.py   # 支付服务 (已有)
│   ├── product_service.py   # 商品服务 (新增)
│   ├── cart_service.py      # 购物车服务 (新增)
│   ├── address_service.py   # 地址服务 (新增)
│   └── image_service.py     # 图片服务 (新增)
├── routers/                 # API 路由
│   ├── __init__.py
│   ├── auth.py              # 认证路由 (已有)
│   ├── orders.py            # 订单路由 (已有)
│   ├── payment.py           # 支付路由 (已有)
│   ├── products.py          # 商品路由 (新增)
│   ├── categories.py        # 分类路由 (新增)
│   ├── cart.py              # 购物车路由 (新增)
│   └── addresses.py         # 地址路由 (新增)
├── tasks/                   # 异步任务 (新增)
│   ├── __init__.py
│   ├── order_tasks.py       # 订单相关任务
│   ├── payment_tasks.py     # 支付相关任务
│   └── notification_tasks.py # 通知任务
├── cache/                   # 缓存封装 (新增)
│   ├── __init__.py
│   ├── redis_client.py      # Redis 客户端
│   └── cache_decorator.py   # 缓存装饰器
├── storage/                 # 存储封装 (新增)
│   ├── __init__.py
│   ├── local_storage.py     # 本地存储
│   └── oss_storage.py       # OSS 存储
├── tests/                   # 测试
│   ├── unit/               # 单元测试
│   ├── integration/        # 集成测试 (新增)
│   └── e2e/                # 端到端测试 (新增)
├── docs/                    # 文档
│   ├── project-brief.md    # 项目简报
│   ├── prd.md              # PRD
│   ├── architecture.md     # 架构设计
│   └── deployment.md       # 部署指南 (新增)
└── scripts/                 # 脚本
    ├── migrate.py          # 数据迁移脚本
    └── setup.py            # 初始化脚本
```

### 8.2 依赖关系

```
┌─────────────────────────────────────────┐
│            依赖关系图                    │
├─────────────────────────────────────────┤
│                                         │
│   routers (API层)                       │
│   ├── 依赖: services, models            │
│   └── 不依赖: database, cache           │
│                                         │
│   services (业务层)                      │
│   ├── 依赖: models, cache, storage      │
│   └── 不依赖: routers                   │
│                                         │
│   models (数据层)                        │
│   ├── 依赖: database                    │
│   └── 不依赖: services, routers         │
│                                         │
│   tasks (异步任务)                       │
│   ├── 依赖: services, cache             │
│   └── 不依赖: routers                   │
│                                         │
│   cache, storage (基础设施)              │
│   └── 无业务依赖                         │
│                                         │
└─────────────────────────────────────────┘
```

### 8.3 避免循环依赖的策略

1. **依赖注入**: 使用依赖注入而非直接导入
```python
# 不推荐
from services.product_service import ProductService

# 推荐
from typing import Protocol

class ProductServiceProtocol(Protocol):
    async def get_product(self, product_id: str) -> Product: ...

async def create_order(product_service: ProductServiceProtocol, ...):
    product = await product_service.get_product(product_id)
```

2. **接口隔离**: 服务间通过接口通信
```python
# services/interfaces.py
from abc import ABC, abstractmethod

class IProductService(ABC):
    @abstractmethod
    async def get_product(self, product_id: str) -> Product: ...

class IOrderService(ABC):
    @abstractmethod
    async def create_order(self, user_id: str, items: list) -> Order: ...
```

3. **事件驱动**: 模块间通过事件通信
```python
# events/order_events.py
from pydantic import BaseModel

class OrderCreatedEvent(BaseModel):
    order_id: str
    user_id: str
    total_amount: float
    created_at: datetime

# 发布事件
await event_bus.publish(OrderCreatedEvent(...))

# 订阅事件
@event_bus.subscribe(OrderCreatedEvent)
async def on_order_created(event: OrderCreatedEvent):
    await notification_service.send_order_confirmation(event.user_id, event.order_id)
```

---

## 9. 可扩展性设计

### 9.1 微服务拆分路线图

```
Phase 1: 单体架构 (当前)
┌─────────────────────────────────┐
│         E-Commerce MVP          │
│  (认证 + 商品 + 订单 + 支付)      │
└─────────────────────────────────┘

Phase 2: 模块化单体 (3-6月)
┌─────────────────────────────────┐
│         API Gateway             │
├─────────┬─────────┬─────────────┤
│  Auth   │ Product │  Order      │
│ Module  │ Module  │  Module     │
│         │         ├─────────────┤
│         │         │  Payment    │
│         │         │  Module     │
└─────────┴─────────┴─────────────┘

Phase 3: 微服务架构 (6-12月)
┌─────────────────────────────────────────┐
│           API Gateway                   │
│    (Kong / Spring Cloud Gateway)        │
├─────────┬─────────┬─────────┬──────────┤
│  Auth   │ Product │  Order  │ Payment  │
│ Service │ Service │ Service │ Service  │
│         │         │         ├──────────┤
│         │         │         │ Notification
│         │         │         │ Service  │
└─────────┴─────────┴─────────┴──────────┘
```

### 9.2 模块间通信机制

**当前 (单体)**:
```python
# 直接函数调用
product = await product_service.get_product(product_id)
```

**未来 (微服务)**:
```python
# HTTP API 调用
product = await http_client.get(f"http://product-service/api/products/{product_id}")

# 或 gRPC
product = await grpc_client.product_service.get_product(product_id)

# 或消息队列
await message_bus.publish(GetProductRequest(product_id))
```

### 9.3 配置中心

```python
# config/settings.py
class Settings(BaseSettings):
    # 服务发现 (微服务阶段启用)
    SERVICE_DISCOVERY_ENABLED: bool = False
    CONSUL_HOST: str = "localhost"
    CONSUL_PORT: int = 8500
    
    # 配置中心 (微服务阶段启用)
    CONFIG_CENTER_ENABLED: bool = False
    APOLLO_HOST: str = ""
    APOLLO_APP_ID: str = ""
    
    # 当前使用本地配置
    # 未来可从配置中心动态加载
    @classmethod
    def load_from_config_center(cls):
        if cls.CONFIG_CENTER_ENABLED:
            # 从 Apollo/Nacos 加载配置
            pass
        return cls()
```

### 9.4 服务治理

| 功能 | 当前方案 | 微服务方案 |
|------|----------|------------|
| **服务注册** | 无 | Consul / Nacos |
| **配置管理** | 环境变量 | Apollo / Nacos |
| **限流熔断** | 手动实现 | Sentinel / Hystrix |
| **链路追踪** | 日志 | Jaeger / Zipkin |
| **监控告警** | 日志 | Prometheus + Grafana |

---

## 10. 性能优化

### 10.1 数据库优化

**索引优化**:
```sql
-- 商品表索引
CREATE INDEX CONCURRENTLY idx_products_category_status 
ON products(category_id, status) WHERE status = 'active';

-- 复合索引
CREATE INDEX CONCURRENTLY idx_products_price_sort 
ON products(price, created_at DESC);

-- 覆盖索引
CREATE INDEX CONCURRENTLY idx_orders_user_status 
ON orders(user_id, status) INCLUDE (total_amount, created_at);
```

**查询优化**:
```python
# 避免 N+1 问题
# 不推荐
products = await db.query(Product).all()
for product in products:
    category = await db.query(Category).filter(Category.id == product.category_id).first()

# 推荐
products = await db.query(Product).options(
    joinedload(Product.category)
).all()

# 分页优化
# 不推荐 (大数据量时慢)
query = db.query(Product).offset((page - 1) * page_size).limit(page_size)

# 推荐 (游标分页)
query = db.query(Product).filter(Product.id > last_id).limit(page_size)
```

### 10.2 API 优化

**响应压缩**:
```python
# main.py
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**异步处理**:
```python
# 同步操作改为异步
# 不推荐
def process_order(order_id: str):
    order = db.query(Order).filter(Order.id == order_id).first()
    return order

# 推荐
async def process_order(order_id: str):
    order = await db.query(Order).filter(Order.id == order_id).first()
    return order
```

**批量操作**:
```python
# 批量插入
# 不推荐
for product in products:
    db.add(product)
await db.commit()

# 推荐
await db.execute(
    insert(Product),
    [p.to_dict() for p in products]
)
await db.commit()
```

### 10.3 缓存优化

**多级缓存**:
```python
async def get_product(product_id: str):
    # L1: 本地缓存
    if product_id in local_cache:
        return local_cache[product_id]
    
    # L2: Redis
    cached = await redis.get(f"product:{product_id}")
    if cached:
        product = json.loads(cached)
        local_cache[product_id] = product  # 回填本地缓存
        return product
    
    # L3: 数据库
    product = await db.query(Product).filter(Product.id == product_id).first()
    if product:
        await redis.setex(f"product:{product_id}", 600, json.dumps(product.to_dict()))
        local_cache[product_id] = product
    return product
```

### 10.4 监控方案

```python
# middleware/metrics.py
from prometheus_client import Counter, Histogram, generate_latest

# 定义指标
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

# 暴露指标端点
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## 11. 安全设计

### 11.1 认证授权

**JWT Token 策略**:
```python
# config/settings.py
class Settings(BaseSettings):
    # Token 配置
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 安全头部
    SECURE_HEADERS: bool = True
    
# 刷新 Token 机制
@app.post("/auth/refresh")
async def refresh_token(refresh_token: str):
    payload = verify_refresh_token(refresh_token)
    new_access_token = create_access_token(payload["sub"])
    return {"access_token": new_access_token}
```

**权限控制**:
```python
# dependencies/auth.py
from fastapi import Depends, HTTPException
from enum import Enum

class Role(Enum):
    USER = "user"
    ADMIN = "admin"
    MERCHANT = "merchant"

async def require_role(required_role: Role):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role.value:
            raise HTTPException(status_code=403, detail="权限不足")
        return current_user
    return role_checker

# 使用
@app.post("/products", dependencies=[Depends(require_role(Role.ADMIN))])
async def create_product(...):
    pass
```

### 11.2 数据安全

**敏感数据加密**:
```python
# 数据库字段加密
from cryptography.fernet import Fernet

class EncryptedString(TypeDecorator):
    impl = String
    
    def __init__(self, key: str, **kwargs):
        super().__init__(**kwargs)
        self.cipher = Fernet(key)
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return self.cipher.encrypt(value.encode()).decode()
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.cipher.decrypt(value.encode()).decode()

# 使用
class User(Base):
    phone = Column(EncryptedString(key=settings.ENCRYPTION_KEY))
```

### 11.3 接口安全

**参数校验**:
```python
from pydantic import BaseModel, validator, Field

class CreateProductRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    price: Decimal = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    
    @validator('name')
    def validate_name(cls, v):
        if '<script>' in v.lower():
            raise ValueError('名称包含非法字符')
        return v
```

**限流防护**:
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost", encoding="utf8")
    FastAPILimiter.init(redis)

# 限流: 每分钟最多 10 次
@app.post("/login", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def login(...):
    pass
```

### 11.4 审计日志

```python
# middleware/audit.py
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    # 记录敏感操作
    if request.method in ["POST", "PUT", "DELETE"]:
        await audit_log.info({
            "user_id": request.state.user_id,
            "action": f"{request.method} {request.url.path}",
            "ip": request.client.host,
            "timestamp": datetime.now().isoformat(),
            "user_agent": request.headers.get("user-agent")
        })
    
    return await call_next(request)
```

---

## 12. 部署架构

### 12.1 部署方案

**开发环境**:
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=sqlite:///./ecommerce.db
      - REDIS_URL=redis://redis:6379
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**生产环境**:
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  app:
    build: .
    replicas: 3
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/ecommerce
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=ecommerce
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app
```

### 12.2 环境配置

| 环境 | 数据库 | 缓存 | 文件存储 | 队列 |
|------|--------|------|----------|------|
| **开发** | SQLite | 可选 | 本地 | 同步 |
| **测试** | PostgreSQL | Redis | MinIO | Celery |
| **生产** | PostgreSQL | Redis Cluster | OSS/S3 | Celery Cluster |

### 12.3 监控告警

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ecommerce'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'

# 告警规则
groups:
  - name: ecommerce
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "错误率过高"
```

### 12.4 备份策略

| 数据类型 | 备份频率 | 保留周期 | 方式 |
|----------|----------|----------|------|
| 数据库 | 每日 | 30天 | pg_dump + 云存储 |
| 文件 | 实时 | 永久 | OSS 多副本 |
| 配置 | 每次变更 | 永久 | Git + 配置中心 |
| 日志 | 实时 | 90天 | ELK / Loki |

---

## 13. 总结

### 13.1 关键决策

| 决策 | 方案 | 理由 |
|------|------|------|
| **数据库** | SQLite → PostgreSQL | 开发简单，生产高性能 |
| **缓存** | Redis | 与队列复用，生态成熟 |
| **队列** | Celery + Redis | 轻量级，功能完整 |
| **文件存储** | 本地 → MinIO → OSS | 渐进演进，成本可控 |
| **架构** | 单体 → 模块化 → 微服务 | 逐步拆分，风险可控 |

### 13.2 实施建议

1. **第一阶段 (2周)**:
   - 完成商品、购物车、地址模块开发
   - 保持 SQLite，添加新表
   - 完成单元测试

2. **第二阶段 (1周)**:
   - 迁移到 PostgreSQL
   - 添加 Redis 缓存
   - 性能测试

3. **第三阶段 (1周)**:
   - 添加 Celery 异步任务
   - 集成测试
   - 部署文档

### 13.3 风险缓解

| 风险 | 缓解措施 |
|------|----------|
| 数据迁移失败 | 备份 + 灰度迁移 |
| 性能不达标 | 压测 + 优化迭代 |
| 缓存雪崩 | 多级缓存 + 熔断 |
| 微服务拆分困难 | 预留接口，渐进拆分 |

---

**架构设计完成** ✅

*本文档由架构师 Winston 创建，基于产品经理 John 的 PRD*

*最后更新: 2026-02-21*
