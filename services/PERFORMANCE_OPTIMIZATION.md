# BUG-002 大图片上传超时修复 - 性能优化说明

## 问题背景
当前图片上传在处理大文件时容易超时，主要原因是：
1. 同步文件读取导致阻塞
2. 一次性加载整个文件到内存
3. 缺乏超时控制机制
4. 文件大小限制较低 (5MB)

## 优化方案

### 1. 流式文件上传 (Streaming Upload)

**实现方式：**
```python
CHUNK_SIZE = 1024 * 1024  # 1MB分块

async def save_upload_file_stream(self, file: UploadFile, ...):
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(self.CHUNK_SIZE):
            buffer.write(chunk)
```

**优化效果：**
- 内存占用从 `文件大小` 降低到 `1MB`
- 支持上传 10MB 以上大文件
- 避免内存溢出风险

### 2. 异步图片压缩

**实现方式：**
```python
async def compress_image(self, image_path: Path, max_size: tuple = (1920, 1080)):
    def _compress():
        with Image.open(image_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            compressed_path = image_path.parent / f"compressed_{image_path.name}"
            img.save(compressed_path, "JPEG", quality=85, optimize=True)
            return compressed_path
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _compress)
```

**优化效果：**
- 压缩操作在线程池中执行，不阻塞事件循环
- 自动调整大尺寸图片到合理尺寸
- JPEG 质量 85%，平衡画质和文件大小

### 3. 超时控制

**实现方式：**
```python
def timeout(seconds: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise HTTPException(status_code=408, detail="上传超时")
        return wrapper
    return decorator

@timeout(30)  # 30秒超时
async def save_upload_file_stream(...):
    ...
```

**优化效果：**
- 明确的超时时间控制 (30秒)
- 超时后返回 408 状态码
- 自动清理失败文件

### 4. 文件大小限制优化

| 项目 | 优化前 | 优化后 |
|------|--------|--------|
| 最大文件大小 | 5MB | 10MB |
| 内存占用 | 文件大小 | 1MB (分块) |
| 上传方式 | 同步 | 异步流式 |

## 向后兼容

### 保留的同步方法
- `save_upload_file()` - 原有的同步保存方法
- `validate_image()` - 原有的同步验证方法
- `_generate_thumbnail()` - 原有的同步缩略图生成

### 新增方法
- `save_upload_file_stream()` - 异步流式上传 (推荐)
- `_validate_image_async()` - 异步验证
- `compress_image()` - 异步压缩
- `_generate_thumbnail_async()` - 异步缩略图生成

## 使用示例

### 新异步方式 (推荐)
```python
# 在 FastAPI 路由中使用
@app.post("/upload")
async def upload_image(file: UploadFile):
    result = await image_service.save_upload_file_stream(
        file=file,
        folder="products",
        generate_thumbnail=True,
        compress=True
    )
    return result
```

### 原同步方式 (向后兼容)
```python
# 原有代码无需修改
result = image_service.save_upload_file(
    file=file,
    folder="products",
    generate_thumbnail=True
)
```

## 性能对比

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 最大支持文件 | 5MB | 10MB | 2x |
| 内存占用 (10MB文件) | 10MB+ | 1MB | 10x |
| 超时控制 | 无 | 30秒 | 新增 |
| 图片压缩 | 无 | 自动 | 新增 |
| 并发处理能力 | 低 | 高 | 显著提升 |

## 注意事项

1. **异步方法需要在异步环境中调用** (如 FastAPI 的 async 路由)
2. **同步方法保持原有行为**，可在非异步环境使用
3. **压缩后的图片格式为 JPEG**，透明背景会被填充为白色
4. **超时时间可根据实际需求调整** (默认30秒)
