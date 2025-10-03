from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


class EmergencyContactBase(SQLModel):
    name: str = Field(max_length=100, description="Contact person's name")
    relationship: str = Field(max_length=50, description="Relationship to user (e.g., Mother, Neighbor)")
    phone_number: str = Field(max_length=20, description="Contact's phone number")
    is_primary: bool = Field(default=False, description="Primary emergency contact")
    notes: Optional[str] = Field(default=None, max_length=200, description="Additional notes about the contact")


class EmergencyContact(EmergencyContactBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", description="ID of the user who owns this contact")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Contact creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="emergency_contacts")


class EmergencyContactCreate(EmergencyContactBase):
    pass


class EmergencyContactRead(EmergencyContactBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]


class EmergencyContactUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    relationship: Optional[str] = Field(default=None, max_length=50)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    is_primary: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=200)


class UserPreferencesBase(SQLModel):
    """Base class for user preferences"""
    notify_flood_alerts: bool = Field(default=True, description="Receive flood alert notifications")
    notify_capacity_updates: bool = Field(default=True, description="Receive evacuation center capacity updates")
    notify_emergency_reports: bool = Field(default=True, description="Receive emergency report notifications")
    notify_weather_updates: bool = Field(default=False, description="Receive weather update notifications")
    language_preference: str = Field(default="en", max_length=5, description="Preferred language (en, fil, etc.)")
    timezone: str = Field(default="Asia/Manila", max_length=50, description="User's timezone")


class UserPreferences(UserPreferencesBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, description="ID of the user")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Preferences creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # Relationships
    user: Optional["User"] = Relationship()


class UserPreferencesCreate(UserPreferencesBase):
    pass


class UserPreferencesRead(UserPreferencesBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]


class UserPreferencesUpdate(SQLModel):
    notify_flood_alerts: Optional[bool] = None
    notify_capacity_updates: Optional[bool] = None
    notify_emergency_reports: Optional[bool] = None
    notify_weather_updates: Optional[bool] = None
    language_preference: Optional[str] = Field(default=None, max_length=5)
    timezone: Optional[str] = Field(default=None, max_length=50)
