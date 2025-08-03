from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from app.models import User
from app.schemas import UserCreate, UserLoginSchema, UserUpdate, ChangePasswordRequest
from app.crud import create_user, authenticate_user, get_user_by_email
from app.utils.database import get_db
from app.utils.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()


# 注册用户
@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # 检查邮箱是否已注册
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 这里调用 hash_password(user.password)
    hashed_password = hash_password(user.password)

    new_user = User(
        email=user.email,
        hashed_password=hashed_password,  # 存储加密后的密码
        username=user.username,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}


# 用户登录
@router.post("/login")
async def login(user: UserLoginSchema, db: Session = Depends(get_db)):
    stored_user = authenticate_user(db, user.email, user.password)
    if not stored_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": stored_user.email})
    print(f"Generated token: {token}")  # 打印 token 看是否生成正确
    return {
        "token": token,
        "username": stored_user.username,
        "email": stored_user.email,
        "id": stored_user.id  # 返回用户的 ID
    }


# 获取当前用户信息
@router.get("/me")
def get_current_user_data(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """自动获取当前登录用户的 email"""
    return {"email": current_user.email, "username": current_user.username}


# 修改用户名
@router.put("/update-user")
async def update_user(user_update: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 确保只有当前用户可以更新自己的信息
    if current_user.email != user_update.email:
        raise HTTPException(status_code=403, detail="You can only update your own user information.")

    # 查询当前用户
    db_user = db.query(User).filter(User.email == current_user.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 更新用户名
    if user_update.username:
        db_user.username = user_update.username

    db.commit()
    db.refresh(db_user)
    return {"message": "Username updated successfully"}


# 修改密码
@router.put("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 确保只有当前用户可以修改自己的密码
    if current_user.email != request.email:
        raise HTTPException(status_code=403, detail="You can only change your own password.")

    # 查询用户
    user = db.query(User).filter(User.email == current_user.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 验证旧密码是否正确
    if not verify_password(request.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    # 更新密码
    user.hashed_password = hash_password(request.new_password)
    db.commit()
    db.refresh(user)

    return {"message": "Password updated successfully"}
