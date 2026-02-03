from fastapi import APIRouter, HTTPException
from ..schemas import SpeechTokenResponse
from ..services.speech_service import SpeechService

router = APIRouter(prefix="/api/speech", tags=["speech"])
speech_service = SpeechService()

@router.get("/token", response_model=SpeechTokenResponse)
def get_speech_token():
    """
    Generate temporary Azure Speech token for frontend.
    Token expires in 10 minutes.
    """
    try:
        token, region = speech_service.get_token()
        return SpeechTokenResponse(token=token, region=region)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token: {str(e)}")






