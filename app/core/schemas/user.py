from pydantic import BaseModel, UUID4, Field
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class UserBase(BaseModel):
    name: str
    role: UserRole = UserRole.USER

class UserCreate(BaseModel):
    name: str

    class Config:
        extra = "forbid"

class User(UserBase):
    id: UUID4
    api_key: str

    class Config:
        from_attributes = True
