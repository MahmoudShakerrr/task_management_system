from enum import Enum
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime


class UserRole(str, Enum):
    admin = "admin"
    project_manager = "project_manager"
    employee = "employee"


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole = UserRole.employee


class UserCreate(UserBase):
    password: str


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    name: str
    email: EmailStr
    role: UserRole


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)