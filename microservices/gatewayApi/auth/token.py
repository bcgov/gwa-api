import requests
import time
from authlib.jose import jwt
from authlib.jose.errors import JoseError, ExpiredTokenError
from authlib.oauth2.rfc6749 import TokenMixin
from authlib.oauth2.rfc6750 import BearerTokenValidator
from flask import current_app, g
from config import Config

def OIDCDiscovery(base_url):
    conf = Config()

    # Fetch the openid metadata so we may know the jwk endpoint uri
    server_metadata_url = f"{base_url}/.well-known/openid-configuration"
    server_metadata_r = requests.get(server_metadata_url)
    if server_metadata_r.status_code != 200:
        raise Exception(
            f"Error getting auth server metadata from url: {server_metadata_url}"
            + ", status_code: {server_metadata_r.status_code}"
        )
    server_metadata = server_metadata_r.json()
    return server_metadata

class OIDCTokenValidator(BearerTokenValidator):

    def __init__(self, token_cls, realm=None):
        super().__init__(realm)
        self.token_cls = token_cls

        conf = Config()

        server_url = conf.data['keycloak']['serverUrl']
        realm = conf.data['keycloak']['realm']
        baseUrl = "%srealms/%s" % (server_url, realm)

        self.aud = conf.data['tokenMatch']['aud']

        server_metadata = OIDCDiscovery(baseUrl)

        # Fetch the public key for validating Bearer token
        jwk_r = requests.get(server_metadata['jwks_uri'])
        if jwk_r.status_code != 200:
            raise Exception(
                f"Error getting jwk from url: {server_metadata['jwks_uri']}"
                + ", status_code: {jwk_r.status_code}"
            )
        self.jwk = jwk_r.json()

    def authenticate_token(self, token_string):
        token = jwt.decode(token_string, self.jwk)
        token.validate()

        g.principal = token

        #if self.aud not in token.get("aud"):
        #    return None
        return self.token_cls(token)

    def request_invalid(self, request):
        return False

    def token_revoked(self, token):
        return token.is_revoked()

class RemoteToken(TokenMixin):

    def __init__(self, token):
        self.token = token

    def get_client_id(self):
        return self.token.get('client_id', None)

    def get_scope(self):
        return self.token.get('scope', None)

    def get_expires_in(self):
        return self.token.get('exp', 0)

    def get_expires_at(self):
        expires_at = self.get_expires_in() + self.token.get('iat', 0)
        if expires_at == 0:
            expires_at = time.time() + 3600  # Expires in an hour
        return expires_at

    def is_revoked(self):
        return False
        #return not self.token.get('active', False)