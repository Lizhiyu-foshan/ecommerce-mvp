"""
图片上传服务
提供图片验证、保存、缩略图生成功能
支持流式上传、图片压缩和超时控制
"""
import os
import uuid
import shutil
import asyncio
from functools import wraps
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile, HTTPException
from PIL import Image
import io

from config.settings import settings
from config.logging_config import logger


def timeout(seconds: int):
    """超时装饰器 - 用于异步函数"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise HTTPException(status_code=408, detail="上传超时")
        return wrapper
    return decorator


class ImageService:
    """图片服务"""
    
    # 支持的图片格式
    ALLOWED_FORMATS = {'JPEG', 'PNG', 'GIF', 'WebP', 'BMP'}
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    
    # 文件大小限制 (10MB - 已优化)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # 分块大小 (1MB)
    CHUNK_SIZE = 1024 * 1024
    
    # 图片尺寸限制
    MAX_WIDTH = 4096
    MAX_HEIGHT = 4096
    
    # 缩略图尺寸
    THUMBNAIL_SIZE = (200, 200)
    MEDIUM_SIZE = (800, 800)
    
    # 压缩后图片质量
    COMPRESS_QUALITY = 85
    
    def __init__(self):
        """初始化图片服务"""
        self.upload_dir = Path(getattr(settings, 'LOCAL_STORAGE_PATH', './uploads'))
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self) -> None:
        """确保上传目录存在"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.upload_dir / "products").mkdir(exist_ok=True)
        (self.upload_dir / "avatars").mkdir(exist_ok=True)
        (self.upload_dir / "temp").mkdir(exist_ok=True)
    
    def validate_image(self, file: UploadFile) -> Tuple[bool, str]:
        """
        验证上传的图片文件 (同步版本 - 向后兼容)
        
        Args:
            file: 上传的文件
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        # 检查文件名
        if not file.filename:
            return False, "文件名不能为空"
        
        # 检查文件扩展名
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return False, f"不支持的文件格式，仅支持: {', '.join(self.ALLOWED_EXTENSIONS)}"
        
        # 检查文件大小
        file.file.seek(0, 2)  # 移动到文件末尾
        file_size = file.file.tell()
        file.file.seek(0)  # 重置文件指针
        
        if file_size > self.MAX_FILE_SIZE:
            return False, f"文件大小超过限制，最大允许 {self.MAX_FILE_SIZE // 1024 // 1024}MB"
        
        if file_size == 0:
            return False, "文件不能为空"
        
        # 验证图片格式
        try:
            image = Image.open(file.file)
            if image.format not in self.ALLOWED_FORMATS:
                return False, f"不支持的图片格式: {image.format}"
            
            # 检查图片尺寸
            width, height = image.size
            if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
                return False, f"图片尺寸过大，最大支持 {self.MAX_WIDTH}x{self.MAX_HEIGHT}"
            
            file.file.seek(0)  # 重置文件指针
            return True, ""
            
        except Exception as e:
            return False, f"图片验证失败: {str(e)}"
    
    async def _validate_image_async(self, file: UploadFile) -> Tuple[bool, str]:
        """
        异步验证上传的图片文件
        
        Args:
            file: 上传的文件
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        # 检查文件名
        if not file.filename:
            return False, "文件名不能为空"
        
        # 检查文件扩展名
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return False, f"不支持的文件格式，仅支持: {', '.join(self.ALLOWED_EXTENSIONS)}"
        
        # 检查文件大小 (流式读取时通过读取限制控制)
        file.file.seek(0, 2)  # 移动到文件末尾
        file_size = file.file.tell()
        file.file.seek(0)  # 重置文件指针
        
        if file_size > self.MAX_FILE_SIZE:
            return False, f"文件大小超过限制，最大允许 {self.MAX_FILE_SIZE // 1024 // 1024}MB"
        
        if file_size == 0:
            return False, "文件不能为空"
        
        # 异步验证图片格式
        try:
            content = await file.read()
            image = Image.open(io.BytesIO(content))
            if image.format not in self.ALLOWED_FORMATS:
                return False, f"不支持的图片格式: {image.format}"
            
            # 检查图片尺寸
            width, height = image.size
            if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
                return False, f"图片尺寸过大，最大支持 {self.MAX_WIDTH}x{self.MAX_HEIGHT}"
            
            # 重置文件指针
            await file.seek(0)
            return True, ""
            
        except Exception as e:
            return False, f"图片验证失败: {str(e)}"
    
    @timeout(30)  # 30秒超时
    async def save_upload_file_stream(
        self,
        file: UploadFile,
        folder: str = "products",
        filename: Optional[str] = None,
        generate_thumbnail: bool = False,
        compress: bool = True
    ) -> Dict[str, Any]:
        """
        流式保存上传的文件 (优化版本)
        
        Args:
            file: 上传的文件
            folder: 存储文件夹
            filename: 自定义文件名（不含扩展名）
            generate_thumbnail: 是否生成缩略图
            compress: 是否压缩图片
        
        Returns:
            Dict: 包含文件URL和路径信息
        
        Raises:
            HTTPException: 验证失败或保存失败
        """
        # 验证图片
        is_valid, error_msg = await self._validate_image_async(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 生成文件名
        if not filename:
            filename = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        
        file_ext = Path(file.filename).suffix.lower()
        final_filename = f"{filename}{file_ext}"
        
        # 确定存储路径
        target_dir = self.upload_dir / folder / datetime.now().strftime('%Y/%m')
        target_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = target_dir / final_filename
        
        try:
            # 流式写入 - 避免内存溢出
            total_size = 0
            with open(file_path, "wb") as buffer:
                while chunk := await file.read(self.CHUNK_SIZE):
                    total_size += len(chunk)
                    if total_size > self.MAX_FILE_SIZE:
                        # 清理失败文件
                        buffer.close()
                        if file_path.exists():
                            file_path.unlink()
                        raise HTTPException(status_code=400, detail=f"文件大小超过限制，最大允许 {self.MAX_FILE_SIZE // 1024 // 1024}MB")
                    buffer.write(chunk)
            
            result = {
                "original_name": file.filename,
                "filename": final_filename,
                "path": str(file_path.relative_to(self.upload_dir)),
                "url": f"/uploads/{folder}/{datetime.now().strftime('%Y/%m')}/{final_filename}",
                "size": file_path.stat().st_size
            }
            
            # 压缩图片
            if compress:
                try:
                    compressed_path = await self.compress_image(file_path)
                    result["compressed_path"] = str(compressed_path.relative_to(self.upload_dir))
                    result["compressed_url"] = f"/uploads/{folder}/{datetime.now().strftime('%Y/%m')}/{compressed_path.name}"
                    result["compressed_size"] = compressed_path.stat().st_size
                except Exception as e:
                    logger.warning(f"图片压缩失败: {e}")
            
            # 生成缩略图
            if generate_thumbnail:
                thumbnail_info = await self._generate_thumbnail_async(file_path, target_dir, filename)
                result["thumbnail"] = thumbnail_info
            
            logger.info(f"文件上传成功: {file_path}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            # 清理失败文件
            if file_path.exists():
                file_path.unlink()
            logger.error(f"文件保存失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
        finally:
            await file.close()
    
    async def compress_image(
        self,
        image_path: Path,
        max_size: Tuple[int, int] = (1920, 1080),
        quality: int = None
    ) -> Path:
        """
        异步压缩图片
        
        Args:
            image_path: 原图路径
            max_size: 最大尺寸 (宽, 高)
            quality: 压缩质量 (默认使用类配置)
        
        Returns:
            Path: 压缩后图片路径
        """
        if quality is None:
            quality = self.COMPRESS_QUALITY
        
        def _compress():
            with Image.open(image_path) as img:
                # 转换为 RGB（处理透明背景）
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                
                # 调整尺寸
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 保存压缩后的图片
                compressed_path = image_path.parent / f"compressed_{image_path.name}"
                img.save(compressed_path, "JPEG", quality=quality, optimize=True)
                return compressed_path
        
        # 在线程池中执行（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _compress)
    
    async def _generate_thumbnail_async(
        self,
        original_path: Path,
        target_dir: Path,
        filename: str
    ) -> Dict[str, str]:
        """
        异步生成缩略图
        
        Args:
            original_path: 原图路径
            target_dir: 目标目录
            filename: 文件名（不含扩展名）
        
        Returns:
            Dict: 缩略图信息
        """
        def _generate():
            try:
                with Image.open(original_path) as img:
                    # 转换为 RGB（处理透明背景）
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    
                    # 生成缩略图
                    thumbnail = img.copy()
                    thumbnail.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                    thumbnail_filename = f"{filename}_thumb.jpg"
                    thumbnail_path = target_dir / thumbnail_filename
                    thumbnail.save(thumbnail_path, 'JPEG', quality=85)
                    
                    # 生成中等尺寸图
                    medium = img.copy()
                    medium.thumbnail(self.MEDIUM_SIZE, Image.Resampling.LANCZOS)
                    medium_filename = f"{filename}_medium.jpg"
                    medium_path = target_dir / medium_filename
                    medium.save(medium_path, 'JPEG', quality=90)
                    
                    folder = target_dir.relative_to(self.upload_dir)
                    
                    return {
                        "thumbnail_url": f"/uploads/{folder}/{thumbnail_filename}",
                        "thumbnail_path": str(thumbnail_path.relative_to(self.upload_dir)),
                        "medium_url": f"/uploads/{folder}/{medium_filename}",
                        "medium_path": str(medium_path.relative_to(self.upload_dir))
                    }
                    
            except Exception as e:
                logger.error(f"缩略图生成失败: {e}")
                return {}
        
        # 在线程池中执行
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _generate)
    
    # ========== 向后兼容的同步方法 ==========
    
    def save_upload_file(
        self,
        file: UploadFile,
        folder: str = "products",
        filename: Optional[str] = None,
        generate_thumbnail: bool = False
    ) -> Dict[str, str]:
        """
        保存上传的文件 (同步版本 - 向后兼容)
        
        Args:
            file: 上传的文件
            folder: 存储文件夹
            filename: 自定义文件名（不含扩展名）
            generate_thumbnail: 是否生成缩略图
        
        Returns:
            Dict: 包含文件URL和路径信息
        
        Raises:
            HTTPException: 验证失败或保存失败
        """
        # 验证图片
        is_valid, error_msg = self.validate_image(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 生成文件名
        if not filename:
            filename = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        
        file_ext = Path(file.filename).suffix.lower()
        final_filename = f"{filename}{file_ext}"
        
        # 确定存储路径
        target_dir = self.upload_dir / folder / datetime.now().strftime('%Y/%m')
        target_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = target_dir / final_filename
        
        try:
            # 保存原始文件
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            result = {
                "original_name": file.filename,
                "filename": final_filename,
                "path": str(file_path.relative_to(self.upload_dir)),
                "url": f"/uploads/{folder}/{datetime.now().strftime('%Y/%m')}/{final_filename}",
                "size": file_path.stat().st_size
            }
            
            # 生成缩略图
            if generate_thumbnail:
                thumbnail_info = self._generate_thumbnail(file_path, target_dir, filename)
                result["thumbnail"] = thumbnail_info
            
            logger.info(f"文件上传成功: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"文件保存失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
        finally:
            file.file.close()
    
    def _generate_thumbnail(
        self,
        original_path: Path,
        target_dir: Path,
        filename: str
    ) -> Dict[str, str]:
        """
        生成缩略图 (同步版本)
        
        Args:
            original_path: 原图路径
            target_dir: 目标目录
            filename: 文件名（不含扩展名）
        
        Returns:
            Dict: 缩略图信息
        """
        try:
            with Image.open(original_path) as img:
                # 转换为 RGB（处理透明背景）
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                
                # 生成缩略图
                thumbnail = img.copy()
                thumbnail.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                thumbnail_filename = f"{filename}_thumb.jpg"
                thumbnail_path = target_dir / thumbnail_filename
                thumbnail.save(thumbnail_path, 'JPEG', quality=85)
                
                # 生成中等尺寸图
                medium = img.copy()
                medium.thumbnail(self.MEDIUM_SIZE, Image.Resampling.LANCZOS)
                medium_filename = f"{filename}_medium.jpg"
                medium_path = target_dir / medium_filename
                medium.save(medium_path, 'JPEG', quality=90)
                
                folder = target_dir.relative_to(self.upload_dir)
                
                return {
                    "thumbnail_url": f"/uploads/{folder}/{thumbnail_filename}",
                    "thumbnail_path": str(thumbnail_path.relative_to(self.upload_dir)),
                    "medium_url": f"/uploads/{folder}/{medium_filename}",
                    "medium_path": str(medium_path.relative_to(self.upload_dir))
                }
                
        except Exception as e:
            logger.error(f"缩略图生成失败: {e}")
            return {}
    
    def delete_file(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径（相对于 upload_dir）
        
        Returns:
            bool: 是否删除成功
        """
        try:
            full_path = self.upload_dir / file_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"文件删除成功: {full_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"文件删除失败: {e}")
            return False
    
    def get_file_url(self, file_path: str) -> str:
        """
        获取文件访问 URL
        
        Args:
            file_path: 文件路径（相对于 upload_dir）
        
        Returns:
            str: 文件URL
        """
        return f"/uploads/{file_path}"


# 全局图片服务实例
image_service = ImageService()
