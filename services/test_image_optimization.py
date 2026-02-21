"""
BUG-002 图片上传优化测试脚本
测试流式上传、压缩和超时控制功能
"""
import asyncio
import os
import tempfile
import time
from pathlib import Path
from io import BytesIO

# 模拟 UploadFile
class MockUploadFile:
    def __init__(self, filename, content):
        self.filename = filename
        self._content = content
        self._position = 0
        self.file = BytesIO(content)
    
    async def read(self, size=-1):
        if size == -1:
            data = self._content[self._position:]
            self._position = len(self._content)
            return data
        else:
            data = self._content[self._position:self._position + size]
            self._position += len(data)
            return data
    
    async def seek(self, position):
        self._position = position
        self.file.seek(position)
    
    async def close(self):
        self.file.close()


def create_test_image(size_mb=1, filename="test.jpg"):
    """创建测试图片文件"""
    try:
        from PIL import Image
        import io
        
        # 计算图片尺寸以达到目标大小
        # JPEG 质量85时，大约每像素3字节
        pixels = (size_mb * 1024 * 1024) // 3
        width = int((pixels ** 0.5) * 1.5)  # 16:10 比例
        height = int(pixels / width)
        
        img = Image.new('RGB', (width, height), color=(73, 109, 137))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=85)
        return img_bytes.getvalue()
    except ImportError:
        # 如果没有 PIL，创建模拟数据
        return b'\xff\xd8\xff\xe0' + os.urandom(size_mb * 1024 * 1024)


async def test_stream_upload():
    """测试流式上传功能"""
    print("=" * 60)
    print("测试 1: 流式上传功能")
    print("=" * 60)
    
    # 导入服务
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/projects/ecommerce-mvp')
    
    from services.image_service import image_service
    
    # 创建测试文件 (2MB)
    test_content = create_test_image(2, "test.jpg")
    mock_file = MockUploadFile("test.jpg", test_content)
    
    start_time = time.time()
    try:
        result = await image_service.save_upload_file_stream(
            file=mock_file,
            folder="test",
            generate_thumbnail=False,
            compress=False
        )
        elapsed = time.time() - start_time
        
        print(f"✅ 流式上传成功!")
        print(f"   文件名: {result['filename']}")
        print(f"   文件大小: {result['size'] / 1024 / 1024:.2f} MB")
        print(f"   上传耗时: {elapsed:.2f} 秒")
        print(f"   文件路径: {result['path']}")
        
        # 清理测试文件
        full_path = image_service.upload_dir / result['path']
        if full_path.exists():
            full_path.unlink()
            print(f"   已清理测试文件")
        
        return True
    except Exception as e:
        print(f"❌ 流式上传失败: {e}")
        return False


async def test_compress_image():
    """测试图片压缩功能"""
    print("\n" + "=" * 60)
    print("测试 2: 图片压缩功能")
    print("=" * 60)
    
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/projects/ecommerce-mvp')
    
    from services.image_service import image_service
    from PIL import Image
    import io
    
    # 创建大图片 (4MB)
    pixels = (4 * 1024 * 1024) // 3
    width = int((pixels ** 0.5) * 1.5)
    height = int(pixels / width)
    
    img = Image.new('RGB', (width, height), color=(255, 100, 50))
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG', quality=95)
    test_content = img_bytes.getvalue()
    
    # 保存临时文件
    temp_dir = Path(tempfile.mkdtemp())
    temp_path = temp_dir / "test_large.jpg"
    temp_path.write_bytes(test_content)
    
    original_size = temp_path.stat().st_size
    print(f"原始图片大小: {original_size / 1024 / 1024:.2f} MB")
    print(f"原始图片尺寸: {width}x{height}")
    
    try:
        start_time = time.time()
        compressed_path = await image_service.compress_image(
            temp_path,
            max_size=(1920, 1080)
        )
        elapsed = time.time() - start_time
        
        compressed_size = compressed_path.stat().st_size
        
        # 检查压缩后尺寸
        with Image.open(compressed_path) as img:
            new_width, new_height = img.size
        
        print(f"✅ 图片压缩成功!")
        print(f"   压缩后大小: {compressed_size / 1024 / 1024:.2f} MB")
        print(f"   压缩后尺寸: {new_width}x{new_height}")
        print(f"   压缩率: {(1 - compressed_size/original_size) * 100:.1f}%")
        print(f"   压缩耗时: {elapsed:.2f} 秒")
        
        # 清理
        temp_path.unlink()
        compressed_path.unlink()
        temp_dir.rmdir()
        
        return True
    except Exception as e:
        print(f"❌ 图片压缩失败: {e}")
        return False


async def test_timeout_control():
    """测试超时控制功能"""
    print("\n" + "=" * 60)
    print("测试 3: 超时控制功能")
    print("=" * 60)
    
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/projects/ecommerce-mvp')
    
    from services.image_service import timeout, HTTPException
    
    # 测试正常函数
    @timeout(2)
    async def normal_function():
        await asyncio.sleep(0.5)
        return "success"
    
    # 测试超时函数
    @timeout(1)
    async def slow_function():
        await asyncio.sleep(3)
        return "should not reach"
    
    try:
        result = await normal_function()
        print(f"✅ 正常函数执行成功: {result}")
    except Exception as e:
        print(f"❌ 正常函数执行失败: {e}")
        return False
    
    try:
        result = await slow_function()
        print(f"❌ 超时函数应该抛出异常，但返回: {result}")
        return False
    except HTTPException as e:
        if e.status_code == 408:
            print(f"✅ 超时控制正常工作!")
            print(f"   状态码: {e.status_code}")
            print(f"   错误信息: {e.detail}")
            return True
        else:
            print(f"❌ 异常状态码不正确: {e.status_code}")
            return False
    except Exception as e:
        print(f"❌ 超时控制测试失败: {e}")
        return False


async def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "=" * 60)
    print("测试 4: 向后兼容性")
    print("=" * 60)
    
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/projects/ecommerce-mvp')
    
    from services.image_service import image_service
    
    # 检查同步方法是否存在
    methods_to_check = [
        'save_upload_file',
        'validate_image',
        '_generate_thumbnail',
        'delete_file',
        'get_file_url'
    ]
    
    all_exist = True
    for method in methods_to_check:
        if hasattr(image_service, method):
            print(f"✅ 方法 {method} 存在")
        else:
            print(f"❌ 方法 {method} 不存在")
            all_exist = False
    
    # 检查常量
    constants_to_check = [
        'ALLOWED_FORMATS',
        'ALLOWED_EXTENSIONS',
        'MAX_FILE_SIZE',
        'THUMBNAIL_SIZE',
        'MEDIUM_SIZE'
    ]
    
    for const in constants_to_check:
        if hasattr(image_service, const):
            print(f"✅ 常量 {const} 存在")
        else:
            print(f"❌ 常量 {const} 不存在")
            all_exist = False
    
    # 验证 MAX_FILE_SIZE 已更新
    if image_service.MAX_FILE_SIZE == 10 * 1024 * 1024:
        print(f"✅ MAX_FILE_SIZE 已更新为 10MB")
    else:
        print(f"⚠️ MAX_FILE_SIZE 为 {image_service.MAX_FILE_SIZE / 1024 / 1024}MB")
    
    return all_exist


async def test_large_file_handling():
    """测试大文件处理能力"""
    print("\n" + "=" * 60)
    print("测试 5: 大文件处理能力")
    print("=" * 60)
    
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/projects/ecommerce-mvp')
    
    from services.image_service import image_service
    
    # 测试不同大小的文件
    test_sizes = [1, 3, 5, 8]  # MB
    
    for size_mb in test_sizes:
        print(f"\n测试 {size_mb}MB 文件上传...")
        
        test_content = create_test_image(size_mb, "test.jpg")
        mock_file = MockUploadFile("test.jpg", test_content)
        
        start_time = time.time()
        try:
            result = await image_service.save_upload_file_stream(
                file=mock_file,
                folder="test",
                generate_thumbnail=False,
                compress=False
            )
            elapsed = time.time() - start_time
            
            print(f"  ✅ {size_mb}MB 文件上传成功 ({elapsed:.2f}s)")
            
            # 清理
            full_path = image_service.upload_dir / result['path']
            if full_path.exists():
                full_path.unlink()
                
        except Exception as e:
            print(f"  ❌ {size_mb}MB 文件上传失败: {e}")
            return False
    
    return True


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪 " * 30)
    print("开始 BUG-002 图片上传优化测试")
    print("🧪 " * 30 + "\n")
    
    results = []
    
    # 运行测试
    results.append(("流式上传", await test_stream_upload()))
    results.append(("图片压缩", await test_compress_image()))
    results.append(("超时控制", await test_timeout_control()))
    results.append(("向后兼容", await test_backward_compatibility()))
    results.append(("大文件处理", await test_large_file_handling()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 所有测试通过! BUG-002 修复成功!")
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，请检查修复")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
