"""
用户地址路由
提供收货地址的 API 接口
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db
from services.address_service import AddressService
from routers.auth import get_current_user
from models import User

router = APIRouter(prefix="/api/v1/addresses", tags=["收货地址"])


# ==================== Schemas ====================

class AddressCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="收件人姓名")
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    province: str = Field(..., min_length=1, max_length=50, description="省份")
    city: str = Field(..., min_length=1, max_length=50, description="城市")
    district: str = Field(..., min_length=1, max_length=50, description="区县")
    detail: str = Field(..., min_length=1, max_length=200, description="详细地址")
    zip_code: Optional[str] = Field(None, max_length=10, description="邮编")
    is_default: bool = Field(default=False, description="是否设为默认地址")


class AddressUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=11, max_length=11)
    province: Optional[str] = Field(None, min_length=1, max_length=50)
    city: Optional[str] = Field(None, min_length=1, max_length=50)
    district: Optional[str] = Field(None, min_length=1, max_length=50)
    detail: Optional[str] = Field(None, min_length=1, max_length=200)
    zip_code: Optional[str] = Field(None, max_length=10)
    is_default: Optional[bool] = None


class AddressResponse(BaseModel):
    id: str
    name: str
    phone: str
    province: str
    city: str
    district: str
    detail: str
    zip_code: Optional[str]
    is_default: bool
    full_address: str
    masked_phone: str
    
    class Config:
        from_attributes = True


class AddressListResponse(BaseModel):
    total: int
    items: List[AddressResponse]
    page: int
    page_size: int


# ==================== Helper Functions ====================

def convert_to_response(address) -> AddressResponse:
    """将地址模型转换为响应格式"""
    return AddressResponse(
        id=address.id,
        name=address.name,
        phone=address.phone,
        province=address.province,
        city=address.city,
        district=address.district,
        detail=address.detail,
        zip_code=address.zip_code,
        is_default=address.is_default,
        full_address=address.full_address,
        masked_phone=address.masked_phone
    )


# ==================== Routes ====================

@router.get("", response_model=AddressListResponse)
def get_addresses(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取地址列表"""
    result = AddressService.get_user_addresses(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
    
    return AddressListResponse(
        total=result["total"],
        items=[convert_to_response(addr) for addr in result["items"]],
        page=result["page"],
        page_size=result["page_size"]
    )


@router.post("", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    address: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加收货地址"""
    # 验证数据
    is_valid, error_msg = AddressService.validate_address_data(address.dict())
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    try:
        new_address = AddressService.create_address(
            db=db,
            user_id=current_user.id,
            name=address.name,
            phone=address.phone,
            province=address.province,
            city=address.city,
            district=address.district,
            detail=address.detail,
            zip_code=address.zip_code,
            is_default=address.is_default
        )
        return convert_to_response(new_address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{address_id}", response_model=AddressResponse)
def get_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取地址详情"""
    address = AddressService.get_address_by_id(db, address_id)
    if not address:
        raise HTTPException(status_code=404, detail="地址不存在")
    
    # 权限验证
    if address.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此地址")
    
    return convert_to_response(address)


@router.put("/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: str,
    address_update: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新收货地址"""
    # 验证数据
    update_data = address_update.dict(exclude_unset=True)
    if update_data:
        is_valid, error_msg = AddressService.validate_address_data(update_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
    
    address = AddressService.update_address(
        db=db,
        address_id=address_id,
        user_id=current_user.id,
        update_data=update_data
    )
    
    if not address:
        raise HTTPException(status_code=404, detail="地址不存在")
    
    return convert_to_response(address)


@router.delete("/{address_id}")
def delete_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除收货地址"""
    success = AddressService.delete_address(
        db=db,
        address_id=address_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="地址不存在")
    
    return {"message": "地址已删除"}


@router.put("/{address_id}/default", response_model=AddressResponse)
def set_default_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """设置默认地址"""
    address = AddressService.set_default_address(
        db=db,
        address_id=address_id,
        user_id=current_user.id
    )
    
    if not address:
        raise HTTPException(status_code=404, detail="地址不存在")
    
    return convert_to_response(address)


@router.get("/default", response_model=Optional[AddressResponse])
def get_default_address(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取默认地址"""
    address = AddressService.get_default_address(db, user_id=current_user.id)
    if not address:
        return None
    return convert_to_response(address)
