from subprocess import Popen, PIPE, STDOUT
from typing import Callable
import logging

logger = logging.getLogger(__name__)


def run_step_command(args: list[str]) -> tuple[int, str, str]:
    """Runs a step CLI command and returns (return_code, stdout, stderr)."""
    process = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    return (
        process.returncode,
        stdout.decode('utf-8') if stdout else "",
        stderr.decode('utf-8') if stderr else "",
    )


def bootstrap(
    ca_url: str,
    fingerprint: str,
    runner: Callable = run_step_command,
) -> None:
    """Bootstrap the Step CA root certificate.

    Must succeed before the app can serve requests.
    Raises RuntimeError on failure.
    """
    args = [
        "step", "ca", "bootstrap",
        "--ca-url", ca_url,
        "--fingerprint", fingerprint,
        "--force",
    ]
    logger.info("Bootstrapping Step CA from %s", ca_url)

    return_code, stdout, stderr = runner(args)
    if return_code != 0:
        msg = f"step ca bootstrap failed (rc={return_code}): {stderr or stdout}"
        logger.error(msg)
        raise RuntimeError(msg)

    logger.info("Step CA bootstrap succeeded")


def generate_token(
    subject: str,
    san: list[str] | None = None,
    provisioner_password_file: str = "/etc/step-provisioner/password",
    provisioner_kid: str = "",
    provisioner_issuer: str = "",
    runner: Callable = run_step_command,
) -> str:
    """Generate a one-time token via ``step ca token``.

    Returns the token string on success.
    Raises RuntimeError on failure.
    """
    args = [
        "step", "ca", "token", subject,
        "--provisioner-password-file", provisioner_password_file,
    ]

    if san:
        for s in san:
            args.extend(["--san", s])

    if provisioner_kid:
        args.extend(["--kid", provisioner_kid])

    if provisioner_issuer:
        args.extend(["--issuer", provisioner_issuer])

    logger.debug("step ca token: subject=%s san=%s", subject, san)

    return_code, stdout, stderr = runner(args)
    if return_code != 0:
        msg = f"Failed to generate token: {stderr or stdout}"
        logger.debug("step ca token failed: %s", msg)
        raise RuntimeError(msg)

    token = stdout.strip()
    logger.debug("step ca token succeeded for subject=%s", subject)
    return token
