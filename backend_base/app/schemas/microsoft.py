from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MicrosoftConnectResponse(BaseModel):
    authorization_url: str
    state: str
    redirect_uri: str
    scopes: list[str]


class MicrosoftAccountOut(BaseModel):
    id: int
    provider: str
    account_email: str
    display_name: str
    microsoft_user_id: str
    tenant_id: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MicrosoftCallbackResponse(BaseModel):
    message: str
    account: MicrosoftAccountOut
