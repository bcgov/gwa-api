from starlette.config import Config
import os

# Config will be read from environment variables and/or ".env" files.
config = Config(env_file=".env" if os.path.exists(".env") else None)

log_level = config('LOG_LEVEL', default='DEBUG') 