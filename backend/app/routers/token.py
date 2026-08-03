from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.token import TokenRequest, TokenResponse
from app.services.livekit import create_livekit_token

router = APIRouter(tags=["token"])


@router.post("/token", response_model=TokenResponse)
async def mint_token(body: TokenRequest) -> TokenResponse:
    token = create_livekit_token(identity=body.identity, room_name=body.room_name)
    return TokenResponse(token=token, url=settings.livekit_url)
