from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime
from app.database import get_session
from app.models.user import User
from app.models.user_preferences import EmergencyContact
from app.schemas.settings import (
    ProfileUpdate,
    ContactPublic,
    ContactCreate,
    ContactListResponse,
    ContactCreateResponse,
    ContactDeleteResponse,
    SafetyResourcePublic,
    SafetyResourceListResponse,
    UserProfileResponse,
    ProfileUpdateResponse,
    SettingsSummaryResponse,
    NotificationPreferences,
    UserSettingsResponse
)
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])

# Static safety resources data (in production, this would come from a database)
SAFETY_RESOURCES = [
    SafetyResourcePublic(
        id=1,
        title="Flood Safety Tips",
        content="During floods: 1) Move to higher ground immediately 2) Avoid walking through floodwaters 3) Turn off electricity and gas 4) Keep emergency supplies ready 5) Stay informed through official channels",
        category="FLOOD_SAFETY",
        priority="HIGH",
        link="https://example.com/flood-safety",
        created_at=datetime.utcnow()
    ),
    SafetyResourcePublic(
        id=2,
        title="Emergency Kit Checklist",
        content="Essential items: Water (1 gallon per person per day), Non-perishable food (3-day supply), Flashlight with extra batteries, First aid kit, Medications, Important documents, Cash, Phone charger",
        category="EMERGENCY_PREPAREDNESS",
        priority="HIGH",
        link="https://example.com/emergency-kit",
        created_at=datetime.utcnow()
    ),
    SafetyResourcePublic(
        id=3,
        title="Evacuation Plan",
        content="Create a family evacuation plan: 1) Identify multiple evacuation routes 2) Choose meeting points 3) Prepare emergency contacts 4) Practice the plan regularly 5) Keep important documents ready",
        category="EVACUATION",
        priority="MEDIUM",
        link="https://example.com/evacuation-plan",
        created_at=datetime.utcnow()
    ),
    SafetyResourcePublic(
        id=4,
        title="Weather Monitoring",
        content="Stay informed: 1) Monitor weather forecasts regularly 2) Sign up for emergency alerts 3) Use reliable weather apps 4) Listen to local radio/TV 5) Follow official social media accounts",
        category="WEATHER_AWARENESS",
        priority="MEDIUM",
        link="https://example.com/weather-monitoring",
        created_at=datetime.utcnow()
    ),
    SafetyResourcePublic(
        id=5,
        title="Community Resources",
        content="Local resources: Barangay Hall, Emergency hotlines, Nearest hospitals, Evacuation centers, Community leaders, Neighbor support network",
        category="COMMUNITY_RESOURCES",
        priority="LOW",
        link="https://example.com/community-resources",
        created_at=datetime.utcnow()
    )
]


@router.put("/profile", response_model=ProfileUpdateResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update user profile and notification preferences.
    Protected endpoint requiring JWT authentication.
    """
    updated_fields = []
    
    # Update notification preferences
    if profile_update.notify_flood_alerts is not None:
        current_user.notify_flood_alerts = profile_update.notify_flood_alerts
        updated_fields.append("notify_flood_alerts")
    
    if profile_update.notify_capacity_updates is not None:
        current_user.notify_capacity_updates = profile_update.notify_capacity_updates
        updated_fields.append("notify_capacity_updates")
    
    # Update profile information
    if profile_update.email is not None:
        # Check if email is already taken by another user
        result = await session.execute(
            select(User).where(User.email == profile_update.email, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered to another user"
            )
        current_user.email = profile_update.email
        updated_fields.append("email")
    
    if profile_update.full_name is not None:
        current_user.full_name = profile_update.full_name
        updated_fields.append("full_name")
    
    # Update timestamp
    current_user.updated_at = datetime.utcnow()
    updated_fields.append("updated_at")
    
    await session.commit()
    await session.refresh(current_user)
    
    # Create response
    profile_response = UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        notify_flood_alerts=current_user.notify_flood_alerts,
        notify_capacity_updates=current_user.notify_capacity_updates,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )
    
    return ProfileUpdateResponse(
        message="Profile updated successfully",
        updated_fields=updated_fields,
        profile=profile_response
    )


@router.get("/contacts", response_model=ContactListResponse)
async def get_emergency_contacts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all emergency contacts for the authenticated user.
    """
    result = await session.execute(
        select(EmergencyContact)
        .where(EmergencyContact.user_id == current_user.id)
        .order_by(desc(EmergencyContact.is_primary), EmergencyContact.name)
    )
    contacts = result.scalars().all()
    
    # Transform to public format
    contact_publics = []
    primary_contact = None
    
    for contact in contacts:
        contact_public = ContactPublic(**contact.model_dump())
        contact_publics.append(contact_public)
        
        if contact.is_primary:
            primary_contact = contact_public
    
    return ContactListResponse(
        contacts=contact_publics,
        total_contacts=len(contacts),
        primary_contact=primary_contact
    )


@router.post("/contacts", response_model=ContactCreateResponse)
async def create_emergency_contact(
    contact_data: ContactCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new emergency contact for the authenticated user.
    """
    # If this is set as primary, unset other primary contacts
    if contact_data.is_primary:
        await session.execute(
            select(EmergencyContact)
            .where(EmergencyContact.user_id == current_user.id, EmergencyContact.is_primary == True)
            .update({"is_primary": False})
        )
    
    # Create new contact
    db_contact = EmergencyContact(
        **contact_data.model_dump(),
        user_id=current_user.id,
        updated_at=datetime.utcnow()
    )
    
    session.add(db_contact)
    await session.commit()
    await session.refresh(db_contact)
    
    # Create response
    contact_public = ContactPublic(**db_contact.model_dump())
    
    return ContactCreateResponse(
        message="Emergency contact created successfully",
        contact_id=db_contact.id,
        contact=contact_public
    )


@router.delete("/contacts/{contact_id}", response_model=ContactDeleteResponse)
async def delete_emergency_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete an emergency contact belonging to the authenticated user.
    """
    # Get the contact and verify ownership
    result = await session.execute(
        select(EmergencyContact).where(
            EmergencyContact.id == contact_id,
            EmergencyContact.user_id == current_user.id
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency contact not found or you don't have permission to delete it"
        )
    
    # Delete the contact
    await session.delete(contact)
    await session.commit()
    
    return ContactDeleteResponse(
        message="Emergency contact deleted successfully",
        contact_id=contact_id
    )


@router.get("/safety-resources", response_model=SafetyResourceListResponse)
async def get_safety_resources(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get safety resources and tips.
    """
    # Filter resources by category if provided
    resources = SAFETY_RESOURCES
    if category:
        resources = [r for r in resources if r.category == category.upper()]
    
    # Get unique categories
    categories = list(set([r.category for r in SAFETY_RESOURCES]))
    
    return SafetyResourceListResponse(
        resources=resources,
        total_resources=len(resources),
        categories=categories
    )


@router.get("/summary", response_model=SettingsSummaryResponse)
async def get_settings_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get summary of user settings and preferences.
    """
    # Get emergency contacts
    contacts_result = await session.execute(
        select(EmergencyContact)
        .where(EmergencyContact.user_id == current_user.id)
        .order_by(desc(EmergencyContact.is_primary))
    )
    contacts = contacts_result.scalars().all()
    
    # Find primary contact
    primary_contact = None
    for contact in contacts:
        if contact.is_primary:
            primary_contact = ContactPublic(**contact.model_dump())
            break
    
    # Create profile response
    profile = UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        notify_flood_alerts=current_user.notify_flood_alerts,
        notify_capacity_updates=current_user.notify_capacity_updates,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )
    
    # Create notification preferences
    notification_preferences = {
        "flood_alerts": current_user.notify_flood_alerts,
        "capacity_updates": current_user.notify_capacity_updates,
        "language": "en",
        "timezone": "Asia/Manila"
    }
    
    return SettingsSummaryResponse(
        profile=profile,
        emergency_contacts_count=len(contacts),
        primary_contact=primary_contact,
        notification_preferences=notification_preferences,
        safety_resources_count=len(SAFETY_RESOURCES)
    )


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get current user's profile information.
    """
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        notify_flood_alerts=current_user.notify_flood_alerts,
        notify_capacity_updates=current_user.notify_capacity_updates,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.get("/all", response_model=UserSettingsResponse)
async def get_all_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get complete user settings including profile, contacts, and preferences.
    """
    # Get emergency contacts
    contacts_result = await session.execute(
        select(EmergencyContact)
        .where(EmergencyContact.user_id == current_user.id)
        .order_by(desc(EmergencyContact.is_primary), EmergencyContact.name)
    )
    contacts = contacts_result.scalars().all()
    
    # Transform contacts
    contact_publics = [ContactPublic(**contact.model_dump()) for contact in contacts]
    
    # Create profile response
    profile = UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        notify_flood_alerts=current_user.notify_flood_alerts,
        notify_capacity_updates=current_user.notify_capacity_updates,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )
    
    # Create notification preferences
    notification_preferences = NotificationPreferences(
        flood_alerts=current_user.notify_flood_alerts,
        capacity_updates=current_user.notify_capacity_updates,
        emergency_reports=True,
        weather_updates=False,
        language="en",
        timezone="Asia/Manila"
    )
    
    return UserSettingsResponse(
        profile=profile,
        emergency_contacts=contact_publics,
        notification_preferences=notification_preferences,
        safety_resources=SAFETY_RESOURCES
    )
