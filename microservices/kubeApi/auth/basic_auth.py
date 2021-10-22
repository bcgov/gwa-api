from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status
import secrets
from config import settings

basic_auth = HTTPBasic()


def verify_credentials(creds: HTTPBasicCredentials = Depends(basic_auth)):
    correct_username = secrets.compare_digest(creds.username, settings.access_credentials["accessUser"])
    correct_password = secrets.compare_digest(creds.password, settings.access_credentials["accessSecret"])
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True
