from starlette.config import Config

# Config will be read from environment variables and/or ".env" files.
config = Config(".env")

log_level = config('LOG_LEVEL', default='DEBUG') 