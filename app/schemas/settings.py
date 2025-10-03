from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.user_preferences import (
    EmergencyContactRead, 
    EmergencyContactCreate, 
    EmergencyContactUpdate,
    UserPreferencesRead,
    UserPreferencesUpdate
)


class ProfileUpdate(BaseModel):
    """Schema for updating user profile and notification preferences"""
    notify_flood_alerts: Optional[bool] = Field(default=None, description="Receive flood alert notifications")
    notify_capacity_updates: Optional[bool] = Field(default=None, description="Receive evacuation center capacity updates")
    email: Optional[str] = Field(default=None, max_length=100, description="Email address")
    full_name: Optional[str] = Field(default=None, max_length=100, description="Full name")


class ContactPublic(EmergencyContactRead):
    """Public schema for emergency contacts"""
    pass


class ContactCreate(EmergencyContactCreate):
    """Schema for creating emergency contacts"""
    pass


class ContactUpdate(EmergencyContactUpdate):
    """Schema for updating emergency contacts"""
    pass


class ContactListResponse(BaseModel):
    """Response schema for list of emergency contacts"""
    contacts: List[ContactPublic]
    total_contacts: int
    primary_contact: Optional[ContactPublic] = None


class ContactCreateResponse(BaseModel):
    """Response schema for contact creation"""
    message: str
    contact_id: int
    contact: ContactPublic


class ContactDeleteResponse(BaseModel):
    """Response schema for contact deletion"""
    message: str
    contact_id: int


class SafetyResourcePublic(BaseModel):
    """Schema for public safety resources and tips"""
    id: int
    title: str
    content: str
    category: str
    priority: str
    link: Optional[str] = None
    created_at: datetime


class SafetyResourceListResponse(BaseModel):
    """Response schema for list of safety resources"""
    resources: List[SafetyResourcePublic]
    total_resources: int
    categories: List[str]


class UserProfileResponse(BaseModel):
    """Complete user profile response"""
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    notify_flood_alerts: bool
    notify_capacity_updates: bool
    created_at: datetime
    updated_at: Optional[datetime]


class ProfileUpdateResponse(BaseModel):
    """Response schema for profile updates"""
    message: str
    updated_fields: List[str]
    profile: UserProfileResponse


class SettingsSummaryResponse(BaseModel):
    """Summary of user settings and preferences"""
    profile: UserProfileResponse
    emergency_contacts_count: int
    primary_contact: Optional[ContactPublic]
    notification_preferences: dict
    safety_resources_count: int


class NotificationPreferences(BaseModel):
    """Detailed notification preferences"""
    flood_alerts: bool
    capacity_updates: bool
    emergency_reports: bool
    weather_updates: bool
    language: str
    timezone: str


class UserSettingsResponse(BaseModel):
    """Complete user settings response"""
    profile: UserProfileResponse
    emergency_contacts: List[ContactPublic]
    notification_preferences: NotificationPreferences
    safety_resources: List[SafetyResourcePublic]


# Re-export the core schemas for convenience
__all__ = [
    "ProfileUpdate",
    "ContactPublic",
    "ContactCreate", 
    "ContactUpdate",
    "ContactListResponse",
    "ContactCreateResponse",
    "ContactDeleteResponse",
    "SafetyResourcePublic",
    "SafetyResourceListResponse",
    "UserProfileResponse",
    "ProfileUpdateResponse",
    "SettingsSummaryResponse",
    "NotificationPreferences",
    "UserSettingsResponse",
    "EmergencyContactRead",
    "EmergencyContactCreate",
    "EmergencyContactUpdate",
    "UserPreferencesRead",
    "UserPreferencesUpdate"
]
