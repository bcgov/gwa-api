from starlette.config import Config
from starlette.datastructures import Secret

# Config will be read from environment variables and/or ".env" files.
config = Config(".env")

resourceAuthServer = {
    "serverUrl": config('KC_SERVER_URL'),
    "realm": config('KC_REALM'),
    "clientId": config('KC_RES_SVR_CLIENT_ID'),
    "clientSecret": config('KC_RES_SVR_CLIENT_SECRET', cast=Secret)
}

keycloak = {
    "serverUrl": config('KC_SERVER_URL'),
    "realm": config('KC_REALM'),
    "clientId": config('KC_CLIENT_ID'),
    "clientSecret": "",
    "userRealm": config('KC_USER_REALM'),
    "username": config('KC_USERNAME'),
    "password": config('KC_PASSWORD', cast=Secret)
}

hostTransformation = {
    "enabled": config('HOST_TRANSFORM_ENABLED', cast=bool, default=False),
    "baseUrl": config('HOST_TRANSFORM_BASE_URL')
}

logLevel = config('LOG_LEVEL')

tokenMatch = {
    "aud": config('TOKEN_MATCH_AUD', default="gwa"),
    "admin-aud": config('TOKEN_MATCH_ADMIN_AUD')
}

dataPlane = config('DATA_PLANE')

syncConfig = {
    "interval": config('SYNC_INTERVAL', default="1"),
}

gwaAdmin = {
    "clientId": config('GWA_ADMIN_CLIENT_ID', default="gwa-admin"),
    "namespace": config('GWA_ADMIN_NAMESPACE', default="platform")
}
