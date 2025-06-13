from pydantic import BaseModel, UUID4, constr
from enum import Enum

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class UserBase(BaseModel):
    name: constr(max_length=50)
    role: UserRole = UserRole.USER

class UserCreate(BaseModel):
    name: constr(max_length=50)

    class Config:
        extra = "forbid"

class User(UserBase):
    id: UUID4
    api_key: str

    class Config:
        from_attributes = True
