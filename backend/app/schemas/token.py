from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    identity: str = Field(min_length=1, max_length=255)
    room_name: str = Field(min_length=1, max_length=255)


class TokenResponse(BaseModel):
    token: str
    url: str
