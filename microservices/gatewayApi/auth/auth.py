from functools import wraps
from flask import request, abort, Response, jsonify
from config import Config

from authlib.integrations.flask_oauth2 import ResourceProtector
from auth.token import RemoteToken, OIDCTokenValidator

def admin_jwt(f):
    """
        @param f: flask function
        @return: decorator, return the wrapped function or abort json object.
        """
    require_oauth = ResourceProtector()
    if Config.environment != "test":
        require_oauth.register_token_validator(OIDCTokenValidator(RemoteToken))

    @wraps(f)
    def decorated(*args, **kwargs):
        oauth = require_oauth(f)
        return oauth(*args, **kwargs)

    return decorated
