from livekit import api

from app.config import settings


def create_livekit_token(*, identity: str, room_name: str) -> str:
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )
    return token.to_jwt()


async def dispatch_stt_agent(*, room_name: str) -> None:
    lkapi = api.LiveKitAPI(
        settings.livekit_url.replace("wss://", "https://").replace("ws://", "http://"),
        settings.livekit_api_key,
        settings.livekit_api_secret,
    )
    try:
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=settings.livekit_agent_name,
                room=room_name,
            )
        )
    finally:
        await lkapi.aclose()
