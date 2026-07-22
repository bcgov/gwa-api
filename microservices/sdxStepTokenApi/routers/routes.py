from fastapi import APIRouter, HTTPException

from clients.step import generate_token
from config import settings
from models import HTTPValidationError, TokenRequest, TokenResponse

router = APIRouter(
    prefix="",
    tags=["token"],
)


@router.post(
    "/tokens",
    operation_id="createToken",
    response_model=TokenResponse,
    responses={
        200: {"description": "Token generated successfully."},
        422: {"model": HTTPValidationError, "description": "Request validation failed."},
    },
)
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
