from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from clients.step import generate_token
from config import settings

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
    try:
        token = generate_token(
            subject=request.subject,
            san=request.san,
            provisioner_password_file=settings.provisioner_password_file,
            provisioner_kid=settings.provisioner_kid,
            provisioner_issuer=settings.provisioner_issuer,
        )
        return TokenResponse(token=token)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
