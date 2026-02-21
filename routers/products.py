"""
商品路由
提供商品和分类的 API 接口
"""
from typing import Optional, List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db
from services.product_service import ProductService
from services.image_service import image_service
from routers.auth import get_current_user
from models import User

router = APIRouter(prefix="/api/v1/products", tags=["商品"])


# ==================== Schemas ====================

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    parent_id: Optional[str]
    sort_order: int
    is_active: bool
    
    class Config:
        from_attributes = True


class ProductSpecCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    values: List[str]


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    stock: int = Field(default=0, ge=0)
    category_id: Optional[str] = None
    sort_order: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    category_id: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None


class ProductSpecResponse(BaseModel):
    id: str
    name: str
    values: List[str]
    
    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price: float
    original_price: Optional[float]
    stock: int
    category_id: Optional[str]
    images: List[dict]
    status: str
    sort_order: int
    sales_count: int
    specs: List[ProductSpecResponse] = []
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    total: int
    items: List[ProductResponse]
    page: int
    page_size: int


# ==================== Helper Functions ====================

async def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """获取当前管理员用户 - 检查用户是否具有管理员权限"""
    if not bool(current_user.is_admin):  # 转换为bool检查
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# ==================== Category Routes ====================

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建商品分类（管理员）"""
    try:
        return ProductService.create_category(
            db=db,
            name=category.name,
            description=category.description,
            parent_id=category.parent_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(
    parent_id: Optional[str] = None,
    is_active: bool = True,
    db: Session = Depends(get_db)
):
    """获取分类列表"""
    return ProductService.list_categories(db, parent_id=parent_id, is_active=is_active)


@router.get("/categories/{category_id}", response_model=CategoryResponse)
def get_category(category_id: str, db: Session = Depends(get_db)):
    """获取分类详情"""
    category = ProductService.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: str,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新分类（管理员）"""
    update_data = category_update.dict(exclude_unset=True)
    category = ProductService.update_category(db, category_id, update_data)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    return category


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除分类（管理员）"""
    success = ProductService.delete_category(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"message": "分类已删除"}


# ==================== Product Routes ====================

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建商品（管理员）"""
    try:
        return ProductService.create_product(
            db=db,
            name=product.name,
            price=product.price,
            category_id=product.category_id,
            description=product.description,
            original_price=product.original_price,
            stock=product.stock,
            sort_order=product.sort_order
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=ProductListResponse)
def list_products(
    category_id: Optional[str] = None,
    keyword: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    status: str = "active",
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    """获取商品列表（支持分页和筛选）"""
    result = ProductService.list_products(
        db=db,
        category_id=category_id,
        keyword=keyword,
        min_price=min_price,
        max_price=max_price,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return result


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    """获取商品详情"""
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新商品（管理员）"""
    update_data = product_update.dict(exclude_unset=True)
    product = ProductService.update_product(db, product_id, update_data)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    hard: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除商品（管理员）"""
    success = ProductService.delete_product(db, product_id, hard_delete=hard)
    if not success:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"message": "商品已删除"}


# ==================== Product Spec Routes ====================

@router.post("/{product_id}/specs", response_model=ProductSpecResponse)
def create_product_spec(
    product_id: str,
    spec: ProductSpecCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建商品规格（管理员）"""
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    return ProductService.create_product_spec(
        db=db,
        product_id=product_id,
        name=spec.name,
        values=spec.values
    )


@router.get("/{product_id}/specs", response_model=List[ProductSpecResponse])
def get_product_specs(product_id: str, db: Session = Depends(get_db)):
    """获取商品规格列表"""
    return ProductService.get_product_specs(db, product_id)


@router.put("/specs/{spec_id}", response_model=ProductSpecResponse)
def update_product_spec(
    spec_id: str,
    spec_update: ProductSpecCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新商品规格（管理员）"""
    update_data = spec_update.dict()
    spec = ProductService.update_product_spec(db, spec_id, update_data)
    if not spec:
        raise HTTPException(status_code=404, detail="规格不存在")
    return spec


@router.delete("/specs/{spec_id}")
def delete_product_spec(
    spec_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除商品规格（管理员）"""
    success = ProductService.delete_product_spec(db, spec_id)
    if not success:
        raise HTTPException(status_code=404, detail="规格不存在")
    return {"message": "规格已删除"}


# ==================== Image Routes ====================

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/{product_id}/images")
def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    sort: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """上传商品图片（管理员）"""
    # 验证文件类型
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，只允许: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 验证文件大小
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制，最大允许: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    file.file.seek(0)  # 重置文件指针
    
    # 检查商品是否存在
    product = ProductService.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    try:
        # 保存图片
        result = image_service.save_upload_file(
            file=file,
            folder="products",
            filename=f"product_{product_id}_{sort}",
            generate_thumbnail=True
        )
        
        # 添加到商品图片列表
        ProductService.add_product_image(db, product_id, result["url"], sort)
        
        return {
            "message": "图片上传成功",
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片上传失败: {str(e)}")
