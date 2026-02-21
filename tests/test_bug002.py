"""
BUG-002 图片上传修复验证测试
测试流式上传、超时控制、图片压缩和性能
"""
import os
import sys
import time
import asyncio
import tempfile
from pathlib import Path
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

# 添加项目路径
sys.path.insert(0, '/root/.openclaw/workspace/projects/ecommerce-mvp')

from PIL import Image
import numpy as np

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
        pass


def create_test_image(size_mb, filename="test.jpg"):
    """创建指定大小的测试图片（目标文件大小）"""
    target_bytes = size_mb * 1024 * 1024
    
    # 通过调整质量来逼近目标大小
    # 先创建一个大图，然后调整压缩质量
    width = 2000
    height = int(target_bytes / (width * 3)) + 100
    
    # 创建随机彩色图片
    array = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    img = Image.fromarray(array)
    
    # 二分查找合适的质量值
    low_quality, high_quality = 10, 95
    best_data = None
    
    for _ in range(10):  # 最多10次迭代
        mid_quality = (low_quality + high_quality) // 2
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=mid_quality)
        size = buffer.tell()
        
        if abs(size - target_bytes) < 100 * 1024:  # 误差在100KB内
            best_data = buffer.getvalue()
            break
        elif size < target_bytes:
            low_quality = mid_quality + 1
            best_data = buffer.getvalue()
        else:
            high_quality = mid_quality - 1
    
    if best_data is None:
        buffer.seek(0)
        best_data = buffer.getvalue()
    
    return best_data


async def test_streaming_upload():
    """测试1: 流式上传 - 5MB, 8MB, 10MB"""
    print("=" * 60)
    print("测试1: 流式上传功能")
    print("=" * 60)
    
    from services.image_service import ImageService
    service = ImageService()
    
    results = []
    test_sizes = [5, 8, 10]  # MB
    
    for size_mb in test_sizes:
        print(f"\n--- 测试 {size_mb}MB 图片上传 ---")
        try:
            # 创建测试图片
            start_time = time.time()
            image_data = create_test_image(size_mb)
            create_time = time.time() - start_time
            print(f"  图片创建耗时: {create_time:.2f}s, 实际大小: {len(image_data)/1024/1024:.2f}MB")
            
            # 创建模拟上传文件
            mock_file = MockUploadFile(f"test_{size_mb}mb.jpg", image_data)
            
            # 测试上传
            start_time = time.time()
            result = await service.save_upload_file_stream(
                file=mock_file,
                folder="test",
                compress=False,  # 先不压缩，测试纯上传
                generate_thumbnail=False
            )
            upload_time = time.time() - start_time
            
            success = upload_time < 5.0
            status = "✅ 通过" if success else "❌ 失败"
            
            print(f"  上传耗时: {upload_time:.2f}s {status}")
            print(f"  保存路径: {result.get('path', 'N/A')}")
            print(f"  文件大小: {result.get('size', 0)/1024/1024:.2f}MB")
            
            results.append({
                "test": f"{size_mb}MB上传",
                "size_mb": len(image_data)/1024/1024,
                "upload_time": upload_time,
                "success": success,
                "passed": upload_time < 5.0
            })
            
            # 清理测试文件
            file_path = Path(service.upload_dir) / result.get('path', '')
            if file_path.exists():
                file_path.unlink()
                
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            results.append({
                "test": f"{size_mb}MB上传",
                "size_mb": size_mb,
                "upload_time": -1,
                "success": False,
                "passed": False,
                "error": str(e)
            })
    
    return results


async def test_timeout_control():
    """测试2: 超时控制"""
    print("\n" + "=" * 60)
    print("测试2: 超时控制")
    print("=" * 60)
    
    from services.image_service import timeout
    
    results = []
    
    # 测试正常执行（应该不会超时）
    print("\n--- 测试正常执行（2秒任务，3秒超时）---")
    @timeout(3)
    async def normal_task():
        await asyncio.sleep(0.5)  # 缩短测试时间
        return "completed"
    
    try:
        start = time.time()
        result = await normal_task()
        elapsed = time.time() - start
        print(f"  任务完成: {result}, 耗时: {elapsed:.2f}s ✅")
        results.append({"test": "正常执行", "passed": True, "elapsed": elapsed})
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        results.append({"test": "正常执行", "passed": False, "error": str(e)})
    
    # 测试超时触发
    print("\n--- 测试超时触发（2秒任务，1秒超时）---")
    @timeout(1)
    async def slow_task():
        await asyncio.sleep(2)
        return "completed"
    
    try:
        start = time.time()
        result = await slow_task()
        elapsed = time.time() - start
        print(f"  任务完成（不应该到这里）: {result}")
        results.append({"test": "超时触发", "passed": False, "error": "未触发超时"})
    except Exception as e:
        elapsed = time.time() - start
        if "超时" in str(e) or "Timeout" in str(e):
            print(f"  正确触发超时异常: {e} ✅")
            results.append({"test": "超时触发", "passed": True, "elapsed": elapsed})
        else:
            print(f"  ❌ 异常类型错误: {e}")
            results.append({"test": "超时触发", "passed": False, "error": str(e)})
    
    return results


async def test_image_compression():
    """测试3: 图片压缩"""
    print("\n" + "=" * 60)
    print("测试3: 图片压缩")
    print("=" * 60)
    
    from services.image_service import ImageService
    service = ImageService()
    
    results = []
    
    # 创建大图片用于压缩测试
    print("\n--- 创建8MB测试图片 ---")
    image_data = create_test_image(8)
    original_size = len(image_data)
    print(f"  原始大小: {original_size/1024/1024:.2f}MB")
    
    # 先保存原图
    mock_file = MockUploadFile("test_compression.jpg", image_data)
    result = await service.save_upload_file_stream(
        file=mock_file,
        folder="test",
        compress=False,
        generate_thumbnail=False
    )
    
    original_path = Path(service.upload_dir) / result['path']
    
    # 测试压缩
    print("\n--- 测试图片压缩 ---")
    try:
        start_time = time.time()
        compressed_path = await service.compress_image(original_path)
        compress_time = time.time() - start_time
        
        compressed_size = compressed_path.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        print(f"  压缩耗时: {compress_time:.2f}s")
        print(f"  原图大小: {original_size/1024/1024:.2f}MB")
        print(f"  压缩后大小: {compressed_size/1024/1024:.2f}MB")
        print(f"  压缩率: {compression_ratio:.1f}%")
        
        # 验证压缩后图片质量
        with Image.open(compressed_path) as img:
            print(f"  压缩后尺寸: {img.size}")
            print(f"  压缩后格式: {img.format}")
            # 检查图片是否可正常打开
            img.load()
            print(f"  图片可正常打开: ✅")
        
        # 压缩应该减小文件大小
        passed = compressed_size < original_size
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  压缩效果: {status}")
        
        results.append({
            "test": "图片压缩",
            "original_size_mb": original_size/1024/1024,
            "compressed_size_mb": compressed_size/1024/1024,
            "compression_ratio": compression_ratio,
            "compress_time": compress_time,
            "passed": passed
        })
        
        # 清理
        compressed_path.unlink()
        
    except Exception as e:
        print(f"  ❌ 压缩失败: {e}")
        results.append({"test": "图片压缩", "passed": False, "error": str(e)})
    
    # 清理原图
    if original_path.exists():
        original_path.unlink()
    
    return results


async def test_performance():
    """测试4: 性能测试"""
    print("\n" + "=" * 60)
    print("测试4: 性能测试")
    print("=" * 60)
    
    from services.image_service import ImageService
    service = ImageService()
    
    results = []
    
    # 4.1 单文件上传性能
    print("\n--- 4.1 10MB图片上传性能 ---")
    image_data = create_test_image(10)
    
    upload_times = []
    for i in range(3):
        mock_file = MockUploadFile(f"perf_test_{i}.jpg", image_data)
        start = time.time()
        result = await service.save_upload_file_stream(
            file=mock_file,
            folder="test",
            compress=False,
            generate_thumbnail=False
        )
        elapsed = time.time() - start
        upload_times.append(elapsed)
        
        # 清理
        file_path = Path(service.upload_dir) / result['path']
        if file_path.exists():
            file_path.unlink()
    
    avg_time = sum(upload_times) / len(upload_times)
    min_time = min(upload_times)
    max_time = max(upload_times)
    
    print(f"  上传次数: 3")
    print(f"  平均耗时: {avg_time:.2f}s")
    print(f"  最小耗时: {min_time:.2f}s")
    print(f"  最大耗时: {max_time:.2f}s")
    print(f"  性能要求 (<5s): {'✅ 通过' if avg_time < 5.0 else '❌ 失败'}")
    
    results.append({
        "test": "单文件上传性能",
        "file_size_mb": 10,
        "avg_time": avg_time,
        "min_time": min_time,
        "max_time": max_time,
        "passed": avg_time < 5.0
    })
    
    # 4.2 并发上传测试
    print("\n--- 4.2 并发上传测试 (5个5MB文件) ---")
    
    async def upload_single(index):
        img_data = create_test_image(5)
        mock_file = MockUploadFile(f"concurrent_{index}.jpg", img_data)
        start = time.time()
        try:
            result = await service.save_upload_file_stream(
                file=mock_file,
                folder="test",
                compress=False,
                generate_thumbnail=False
            )
            elapsed = time.time() - start
            # 清理
            file_path = Path(service.upload_dir) / result['path']
            if file_path.exists():
                file_path.unlink()
            return {"index": index, "elapsed": elapsed, "success": True}
        except Exception as e:
            return {"index": index, "elapsed": time.time() - start, "success": False, "error": str(e)}
    
    start_all = time.time()
    tasks = [upload_single(i) for i in range(5)]
    concurrent_results = await asyncio.gather(*tasks)
    total_time = time.time() - start_all
    
    success_count = sum(1 for r in concurrent_results if r['success'])
    avg_concurrent = sum(r['elapsed'] for r in concurrent_results) / len(concurrent_results)
    
    print(f"  并发数: 5")
    print(f"  成功数: {success_count}/5")
    print(f"  总耗时: {total_time:.2f}s")
    print(f"  平均单文件耗时: {avg_concurrent:.2f}s")
    print(f"  并发稳定性: {'✅ 通过' if success_count == 5 else '❌ 失败'}")
    
    results.append({
        "test": "并发上传",
        "concurrent_count": 5,
        "file_size_mb": 5,
        "success_count": success_count,
        "total_time": total_time,
        "avg_time": avg_concurrent,
        "passed": success_count == 5
    })
    
    return results


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("BUG-002 图片上传修复验证测试")
    print("=" * 60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {
        "streaming": await test_streaming_upload(),
        "timeout": await test_timeout_control(),
        "compression": await test_image_compression(),
        "performance": await test_performance()
    }
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        for r in results:
            total_tests += 1
            if r.get('passed', False):
                passed_tests += 1
    
    print(f"总测试数: {total_tests}")
    print(f"通过数: {passed_tests}")
    print(f"失败数: {total_tests - passed_tests}")
    print(f"通过率: {passed_tests/total_tests*100:.1f}%")
    
    return all_results, passed_tests, total_tests


if __name__ == "__main__":
    results, passed, total = asyncio.run(run_all_tests())
    sys.exit(0 if passed == total else 1)
