from starlette.config import Config
from starlette.datastructures import Secret

# Config will be read from environment variables and/or ".env" files.
config = Config(".env")

host_transformation = {
    "enabled": config('HOST_TRANSFORM_ENABLED', cast=bool, default=False)
}

log_level = config('LOG_LEVEL', default='DEBUG' )

access_credentials = {
    "accessUser": config('ACCESS_USER'),
    "accessSecret": config('ACCESS_SECRET')
}

defaultDataPlane = config('DEFAULT_DATA_PLANE', default='dp-silver-kong-proxy')
