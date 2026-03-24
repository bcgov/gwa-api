from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from clients.step import generate_token
from config import settings
import logging

logger = logging.getLogger(__name__)


def _token_request_log_extra(
    subject: str,
    san: list[str] | None,
    status: str,
) -> dict:
    extra: dict = {
        "subject": subject,
        "token_request_status": status,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if san is not None:
        extra["san"] = san
    return extra

router = APIRouter(
    prefix="",
    tags=["token"],
)


class TokenRequest(BaseModel):
    subject: str
    san: list[str] | None = None


class TokenResponse(BaseModel):
    token: str


@router.post("/token", response_model=TokenResponse)
async def create_token(request: TokenRequest) -> TokenResponse:
    """Generate a one-time token for the Step CA."""
    subject = request.subject
    san = request.san
    try:
        token = generate_token(
            subject=subject,
            san=san,
            provisioner_password_file=settings.provisioner_password_file,
            provisioner_kid=settings.provisioner_kid,
            provisioner_issuer=settings.provisioner_issuer,
        )
        logger.info(
            "token_request",
            extra=_token_request_log_extra(subject, san, "success"),
        )
        return TokenResponse(token=token)
    except RuntimeError as e:
        logger.warning(
            "token_request",
            extra=_token_request_log_extra(subject, san, "failure"),
        )
        raise HTTPException(status_code=500, detail=str(e))
