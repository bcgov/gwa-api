from starlette.config import Config
import os

config = Config(env_file=".env" if os.path.exists(".env") else None)

log_level = config('LOG_LEVEL', default='DEBUG')
step_ca_url = config('STEP_CA_URL', default='')
step_ca_fingerprint = config('STEP_CA_FINGERPRINT', default='')

provisioner_password_file = config(
    'STEP_PROVISIONER_PASSWORD_FILE',
    default='/etc/step-provisioner/password'
)
provisioner_kid = config('STEP_PROVISIONER_KID', default='')
provisioner_issuer = config('STEP_PROVISIONER_ISSUER', default='')
