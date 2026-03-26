import os
import sys

os.environ["STEP_PROVISIONER_PASSWORD_FILE"] = "/etc/step-provisioner/password"
os.environ["STEP_PROVISIONER_KID"] = ""
os.environ["STEP_PROVISIONER_ISSUER"] = ""
os.environ["STEP_CA_URL"] = "https://test-ca.invalid"
os.environ["STEP_CA_FINGERPRINT"] = "00" * 32

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
