import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, get_current_user
from app.models.user import User
from app.models.unit import Unit
from app.models.enums import UserRole, UnitKind
from app.schemas.user import TokenResponse, LoginRequest, UserResponse, UserCreate

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn đã bị khóa."
        )

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        accessToken=token,
        tokenType="Bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            fullName=user.full_name,
            role=user.role,
            unitId=str(user.unit_id) if user.unit_id else None,
            cohort=user.cohort,
            major=user.major,
            isActive=user.is_active
        )
    )

@router.post("/demo-token", response_model=TokenResponse)
async def get_demo_token(role: UserRole = UserRole.STUDENT, db: AsyncSession = Depends(get_db)):
    """
    Tạo hoặc lấy tài khoản demo tức thì cho các vai trò STUDENT, LECTURER, STAFF, ADMIN
    để hỗ trợ người dùng và ban giám khảo kiểm thử hệ thống trực tiếp trên giao diện.
    Ưu tiên lấy người dùng từ bộ dữ liệu seed vận hành (seed_operational_data.json).
    """
    role_seed_emails = {
        UserRole.STUDENT: "sv.cntt@uni.edu.vn",
        UserRole.LECTURER: "gv.cntt@uni.edu.vn",
        UserRole.STAFF: "canbo.daotao@uni.edu.vn",
        UserRole.ADMIN: "admin@uni.edu.vn"
    }
    target_email = role_seed_emails.get(role, f"demo.{role.value.lower()}@uni.edu.vn")
    
    # 1. Tìm theo email seed chuẩn
    stmt = select(User).where(User.email == target_email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    # 2. Nếu chưa có, tìm bất kỳ user nào có role này
    if not user:
        stmt2 = select(User).where(User.role == role)
        res2 = await db.execute(stmt2)
        user = res2.scalar_one_or_none()

    # 3. Nếu vẫn chưa có, tạo mới
    if not user:
        # Đảm bảo có sẵn 1 Unit mẫu
        unit_stmt = select(Unit).limit(1)
        unit_res = await db.execute(unit_stmt)
        demo_unit = unit_res.scalar_one_or_none()
        if not demo_unit:
            demo_unit = Unit(
                name="Khoa Công nghệ Thông tin",
                kind=UnitKind.FACULTY,
                contact_email="fit@uni.edu.vn",
                phone="024-3869-1234",
                office_location="Nhà B1, Phòng 302"
            )
            db.add(demo_unit)
            await db.flush()

        role_names = {
            UserRole.STUDENT: "Trần Minh Quân (Sinh viên K68)",
            UserRole.LECTURER: "TS. Lê Hoàng Nam (Giảng viên)",
            UserRole.STAFF: "Nguyễn Thị Lan (Cán bộ Phòng Đào tạo)",
            UserRole.ADMIN: "Quản trị viên Hệ thống"
        }
        user = User(
            email=target_email,
            hashed_password=get_password_hash("CampusMate2026!"),
            full_name=role_names.get(role, f"Người dùng {role.value}"),
            role=role,
            unit_id=demo_unit.id,
            cohort="K68" if role == UserRole.STUDENT else None,
            major="Khoa học Máy tính" if role == UserRole.STUDENT else None,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        accessToken=token,
        tokenType="Bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            fullName=user.full_name,
            role=user.role,
            unitId=str(user.unit_id) if user.unit_id else None,
            cohort=user.cohort,
            major=user.major,
            isActive=user.is_active
        )
    )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        fullName=current_user.full_name,
        role=current_user.role,
        unitId=str(current_user.unit_id) if current_user.unit_id else None,
        cohort=current_user.cohort,
        major=current_user.major,
        isActive=current_user.is_active
    )

