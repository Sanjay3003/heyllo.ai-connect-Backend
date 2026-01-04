"""Pydantic schemas package"""

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    Token,
    TokenData,
)

from app.schemas.lead import (
    LeadBase,
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
)

from app.schemas.campaign import (
    CampaignBase,
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignStats,
)

from app.schemas.call import (
    CallBase,
    CallCreate,
    CallUpdate,
    CallResponse,
    CallStats,
)

from app.schemas.analytics import (
    DashboardKPIs,
    CallsOverTime,
    OutcomeDistribution,
)

__all__ = [
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "Token",
    "TokenData",
    "LeadBase",
    "LeadCreate",
    "LeadUpdate",
    "LeadResponse",
    "LeadListResponse",
    "CampaignBase",
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignResponse",
    "CampaignStats",
    "CallBase",
    "CallCreate",
    "CallUpdate",
    "CallResponse",
    "CallStats",
    "DashboardKPIs",
    "CallsOverTime",
    "OutcomeDistribution",
]
