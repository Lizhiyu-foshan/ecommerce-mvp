#!/usr/bin/env python3
"""
数据库初始化脚本
创建管理员用户
"""
import sys
sys.path.insert(0, '/root/.openclaw/workspace/projects/ecommerce-mvp')

from database import SessionLocal, engine, Base
from models import User
from services.auth_service import AuthService

# 创建表
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 检查是否已有管理员
admin = db.query(User).filter(User.username == "admin").first()
if not admin:
    # 创建管理员用户
    admin_user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=AuthService.get_password_hash("admin123"),
        is_active=1,
        is_admin=1
    )
    db.add(admin_user)
    db.commit()
    print("✅ 管理员用户创建成功")
    print("   用户名: admin")
    print("   密码: admin123")
else:
    # 确保是管理员
    admin.is_admin = 1
    db.commit()
    print("✅ 管理员用户已存在并已设置为管理员")

# 检查是否已有测试用户
testuser = db.query(User).filter(User.username == "testuser").first()
if not testuser:
    test_user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=AuthService.get_password_hash("test123"),
        is_active=1,
        is_admin=0
    )
    db.add(test_user)
    db.commit()
    print("✅ 测试用户创建成功")
    print("   用户名: testuser")
    print("   密码: test123")
else:
    print("✅ 测试用户已存在")

db.close()
print("\n🎉 数据库初始化完成")
