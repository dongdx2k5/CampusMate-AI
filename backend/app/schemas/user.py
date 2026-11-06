import uuid
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.enums import UserRole

class UserBase(BaseModel):
    email: EmailStr
    fullName: str
    role: UserRole = UserRole.STUDENT
    unitId: Optional[str] = None
    cohort: Optional[str] = None
    major: Optional[str] = None
    isActive: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdateRole(BaseModel):
    role: UserRole

class UserResponse(BaseModel):
    id: str
    email: str
    fullName: str
    role: UserRole
    unitId: Optional[str] = None
    unitName: Optional[str] = None
    cohort: Optional[str] = None
    major: Optional[str] = None
    isActive: bool

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    accessToken: str
    tokenType: str = "Bearer"
    user: UserResponse

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

