"""
购物车路由
提供购物车的 API 接口
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db
from services.cart_service import CartService
from routers.auth import get_current_user
from models import User, Cart

router = APIRouter(prefix="/api/v1/cart", tags=["购物车"])


# ==================== Schemas ====================

class CartItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1)
    spec_combo: Optional[dict] = Field(default_factory=dict)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=0)


class CartItemResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    spec_combo: dict
    subtotal: float
    product: dict
    
    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total_amount: float
    total_quantity: int
    item_count: int


class CartCheckoutResponse(BaseModel):
    valid: bool
    message: str
    invalid_items: List[dict]


# ==================== Helper Functions ====================

def get_cart_items_response(items: List[Cart]) -> List[CartItemResponse]:
    """转换购物车项为响应格式"""
    result = []
    for item in items:
        if item.product:
            result.append(CartItemResponse(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                spec_combo=item.spec_combo or {},
                subtotal=item.subtotal,
                product={
                    "id": item.product.id,
                    "name": item.product.name,
                    "price": item.product.price,
                    "images": item.product.images or [],
                    "stock": item.product.stock,
                    "status": item.product.status
                }
            ))
    return result


def get_optional_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """获取当前用户（可选，用于支持匿名购物车）"""
    if not authorization:
        return None
    try:
        # 尝试解析 token
        from routers.auth import oauth2_scheme
        from services.auth_service import AuthService
        
        token = authorization.replace("Bearer ", "")
        payload = AuthService.verify_token(token)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            if user_id:
                return AuthService.get_user_by_id(db, int(user_id))
    except Exception:
        pass
    return None


# ==================== Routes ====================

@router.get("", response_model=CartResponse)
def get_cart(
    x_session_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """获取购物车"""
    user_id = current_user.id if current_user else None
    session_id = x_session_id if not current_user else None
    
    items = CartService.get_cart(db, user_id=user_id, session_id=session_id)
    cart_info = CartService.calculate_cart_total(db, user_id=user_id, session_id=session_id)
    
    return CartResponse(
        items=get_cart_items_response(cart_info["valid_items"]),
        total_amount=cart_info["total_amount"],
        total_quantity=cart_info["total_quantity"],
        item_count=cart_info["item_count"]
    )


@router.post("/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    item: CartItemCreate,
    x_session_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """添加商品到购物车"""
    user_id = current_user.id if current_user else None
    session_id = x_session_id if not current_user else None
    
    if not user_id and not session_id:
        raise HTTPException(
            status_code=400, 
            detail="需要提供用户认证或 Session ID"
        )
    
    try:
        cart_item = CartService.add_to_cart(
            db=db,
            product_id=item.product_id,
            quantity=item.quantity,
            spec_combo=item.spec_combo,
            user_id=user_id,
            session_id=session_id
        )
        
        # 转换为响应格式
        return CartItemResponse(
            id=cart_item.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            spec_combo=cart_item.spec_combo or {},
            subtotal=cart_item.subtotal,
            product={
                "id": cart_item.product.id,
                "name": cart_item.product.name,
                "price": cart_item.product.price,
                "images": cart_item.product.images or [],
                "stock": cart_item.product.stock,
                "status": cart_item.product.status
            }
        ) if cart_item.product else None
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/items/{cart_id}", response_model=CartItemResponse)
def update_cart_item(
    cart_id: str,
    item_update: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改购物车商品数量"""
    try:
        cart_item = CartService.update_cart_item(
            db=db,
            cart_id=cart_id,
            quantity=item_update.quantity,
            user_id=current_user.id
        )
        
        if not cart_item:
            raise HTTPException(status_code=404, detail="购物车项不存在")
        
        return CartItemResponse(
            id=cart_item.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            spec_combo=cart_item.spec_combo or {},
            subtotal=cart_item.subtotal,
            product={
                "id": cart_item.product.id,
                "name": cart_item.product.name,
                "price": cart_item.product.price,
                "images": cart_item.product.images or [],
                "stock": cart_item.product.stock,
                "status": cart_item.product.status
            }
        ) if cart_item.product else None
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/items/{cart_id}")
def remove_from_cart(
    cart_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除购物车商品"""
    success = CartService.remove_from_cart(db, cart_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    return {"message": "商品已从购物车移除"}


@router.delete("")
def clear_cart(
    x_session_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """清空购物车"""
    user_id = current_user.id if current_user else None
    session_id = x_session_id if not current_user else None
    
    count = CartService.clear_cart(db, user_id=user_id, session_id=session_id)
    return {"message": f"购物车已清空，共删除 {count} 项"}


@router.post("/merge")
def merge_cart(
    x_session_id: str = Header(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """合并匿名购物车到用户购物车（登录时调用）"""
    if not x_session_id:
        raise HTTPException(status_code=400, detail="需要提供 Session ID")
    
    merged_count = CartService.merge_cart(db, user_id=current_user.id, session_id=x_session_id)
    return {
        "message": f"购物车合并成功，共合并 {merged_count} 项",
        "merged_count": merged_count
    }


@router.get("/checkout/validate", response_model=CartCheckoutResponse)
def validate_cart_for_checkout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """验证购物车是否可结算"""
    result = CartService.validate_cart_for_checkout(db, user_id=current_user.id)
    return CartCheckoutResponse(**result)


@router.post("/checkout")
def checkout_cart(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    购物车结算
    
    此接口会创建订单，实际支付流程请使用订单支付接口
    """
    from services.order_service import OrderService
    from services.address_service import AddressService
    from models.schemas import OrderItem
    
    # 验证购物车
    validation = CartService.validate_cart_for_checkout(db, user_id=current_user.id)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])
    
    # 获取地址
    address = AddressService.get_address_by_id(db, address_id)
    if not address or address.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="收货地址不存在")
    
    # 获取购物车商品
    cart_items = CartService.get_cart(db, user_id=current_user.id)
    
    # 转换为订单项
    order_items = []
    for item in cart_items:
        if item.product:
            order_items.append(OrderItem(
                product_id=item.product_id,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.product.price
            ))
    
    if not order_items:
        raise HTTPException(status_code=400, detail="购物车为空")
    
    # 创建订单
    from models.schemas import OrderCreate
    order_data = OrderCreate(items=order_items)
    
    try:
        order = OrderService.create_order(db, user_id=current_user.id, order_data=order_data)
        
        # 清空购物车
        CartService.clear_cart(db, user_id=current_user.id)
        
        return {
            "message": "订单创建成功",
            "order_id": order.id,
            "order_no": order.order_no,
            "total_amount": order.total_amount
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"订单创建失败: {str(e)}")
