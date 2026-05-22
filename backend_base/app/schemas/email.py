from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic import BaseModel, ConfigDict


from pydantic import BaseModel

class EmailCategoryUpdate(BaseModel):
    category: str

class EmailClassifyIn(BaseModel):
    subject: str = Field(default="", max_length=255)
    body: str = Field(default="")
    sender: str = Field(default="desconocido", max_length=255)
    source_account: str = Field(default="local-demo", max_length=255)


class EmailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    linked_account_id: int | None
    graph_message_id: str | None
    subject: str
    body: str
    sender: str
    source_account: str
    predicted_category: str
    confidence: float
    is_synced_from_microsoft: bool
    received_at: datetime


class EmailClassifyResponse(BaseModel):
    email: EmailOut
    model_version: str

class EmailChatbotQuery(BaseModel):
    query: str


class EmailChatbotResponse(BaseModel):
    intent: str
    applied_filters: dict
    total_results: int
    summary: str
    emails: list[EmailOut]