from fastapi import APIRouter, HTTPException, Request, Depends
from ..schemas import SpeechTokenResponse
from ..services.speech_service import SpeechService
from ..dependencies import get_current_user
from ..models import User
from ..limiter import limiter
from ..middleware.usage_limiter import check_speech_limit
from ..database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/speech", tags=["speech"])
speech_service = SpeechService()


@router.get("/token", response_model=SpeechTokenResponse)
@limiter.limit("10/minute")
async def get_speech_token(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate temporary Azure Speech token for frontend.
    Token expires in 10 minutes.
    Requires authentication. Enforces speech quota and rate limit.
    """
    # Check speech quota (1 minute per token request)
    await check_speech_limit(request, current_user, db, minutes=1)
    try:
        token, region = speech_service.get_token()
        return SpeechTokenResponse(token=token, region=region)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token: {str(e)}")






