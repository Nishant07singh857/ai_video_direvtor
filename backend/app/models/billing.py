from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class UserSubscription(BaseModel):
    user_id: UUID
    tier: SubscriptionTier
    start_date: datetime
    end_date: Optional[datetime] = None
    is_active: bool = True
