from subprocess import Popen, PIPE, TimeoutExpired
from typing import Callable
import logging
import re

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30


def run_step_command(
    args: list[str], timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> tuple[int, str, str]:
    """Runs a step CLI command and returns (return_code, stdout, stderr).

    Raises:
        RuntimeError: If the command times out or fails to execute.
    """
    process = Popen(args, stdout=PIPE, stderr=PIPE)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        raise RuntimeError(
            f"step command timed out after {timeout}s: {' '.join(args)}"
        )
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


def _validate_subject_and_san(subject: str, san: list[str] | None) -> None:
    """Validate subject and SAN values before invoking the step CLI.

    This limits the characters and length of user-controlled values that are
    passed as command-line arguments, reducing the risk of abuse.
    """
    if not subject:
        raise RuntimeError("subject must not be empty")

    if len(subject) > 255:
        raise RuntimeError("subject is too long")

    # Allow common characters used in DNS names, emails, and IPs.
    pattern = re.compile(r"^[A-Za-z0-9_.*:@\-]+$")
    if not pattern.match(subject):
        raise RuntimeError("subject contains invalid characters")

    if san:
        if len(san) > 100:
            raise RuntimeError("too many SAN entries")
        for entry in san:
            if not entry:
                raise RuntimeError("SAN entries must not be empty")
            if len(entry) > 255:
                raise RuntimeError("SAN entry is too long")
            if not pattern.match(entry):
                raise RuntimeError("SAN entry contains invalid characters")


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
    _validate_subject_and_san(subject, san)

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
