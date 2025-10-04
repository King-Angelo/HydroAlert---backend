from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum
import bcrypt


class UserRole(str, Enum):
    RESIDENT = "resident"
    ADMIN = "admin"


class UserBase(SQLModel):
    username: str = Field(unique=True, index=True, max_length=50)
    email: Optional[str] = Field(default=None, unique=True, index=True)
    full_name: Optional[str] = Field(default=None, max_length=100)
    role: UserRole = Field(default=UserRole.RESIDENT)
    is_active: bool = Field(default=True)
    notify_flood_alerts: bool = Field(default=True, description="Receive flood alert notifications")
    notify_capacity_updates: bool = Field(default=True, description="Receive evacuation center capacity updates")


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    # reports: List["EmergencyReport"] = Relationship(back_populates="user")  # Temporarily disabled due to foreign key ambiguity
    emergency_contacts: List["EmergencyContact"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=100)


class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]


class UserUpdate(SQLModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=100)
    is_active: Optional[bool] = None


class UserLogin(SQLModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
