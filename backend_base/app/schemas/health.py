from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class DBHealthResponse(BaseModel):
    status: str
    database: str
