from clients.step import bootstrap, generate_token
import pytest


def mock_runner_success(args):
    """Simulates a successful step CLI invocation."""
    if "bootstrap" in args:
        return 0, "The root certificate has been saved.\n", ""
    return 0, "eyJhbGciOiJFUzI1NiJ9.test-token-payload.signature\n", ""


def mock_runner_failure(args):
    """Simulates a failed step CLI invocation."""
    if "bootstrap" in args:
        return 1, "", "error connecting to CA: dial tcp: connection refused\n"
    return 1, "", "error generating token: unauthorized\n"


class TestBootstrap:
    def test_bootstrap_success(self):
        bootstrap(
            ca_url="https://ca.example.com:443",
            fingerprint="abc123",
            runner=mock_runner_success,
        )

    def test_bootstrap_failure_raises(self):
        with pytest.raises(RuntimeError, match="step ca bootstrap failed"):
            bootstrap(
                ca_url="https://ca.example.com:443",
                fingerprint="abc123",
                runner=mock_runner_failure,
            )

    def test_bootstrap_args(self):
        captured_args = []

        def capturing_runner(args):
            captured_args.extend(args)
            return 0, "ok\n", ""

        bootstrap(
            ca_url="https://ca.example.com:443",
            fingerprint="abc123",
            runner=capturing_runner,
        )
        assert "step" in captured_args
        assert "bootstrap" in captured_args
        assert "--ca-url" in captured_args
        assert "https://ca.example.com:443" in captured_args
        assert "--fingerprint" in captured_args
        assert "abc123" in captured_args
        assert "--force" in captured_args


class TestGenerateToken:
    def test_generate_token_success(self):
        token = generate_token(
            subject="my-service.clients.sdx",
            runner=mock_runner_success,
        )
        assert token == "eyJhbGciOiJFUzI1NiJ9.test-token-payload.signature"

    def test_generate_token_failure_raises(self):
        with pytest.raises(RuntimeError, match="Failed to generate token"):
            generate_token(
                subject="my-service.clients.sdx",
                runner=mock_runner_failure,
            )

    def test_generate_token_with_san(self):
        captured_args = []

        def capturing_runner(args):
            captured_args.extend(args)
            return 0, "test-token\n", ""

        generate_token(
            subject="my-service.clients.sdx",
            san=["alt.clients.sdx", "10.0.0.5"],
            runner=capturing_runner,
        )
        san_indices = [i for i, a in enumerate(captured_args) if a == "--san"]
        assert len(san_indices) == 2
        assert captured_args[san_indices[0] + 1] == "alt.clients.sdx"
        assert captured_args[san_indices[1] + 1] == "10.0.0.5"

    def test_generate_token_without_san(self):
        captured_args = []

        def capturing_runner(args):
            captured_args.extend(args)
            return 0, "test-token\n", ""

        generate_token(
            subject="my-service.clients.sdx",
            runner=capturing_runner,
        )
        assert "--san" not in captured_args

    def test_generate_token_with_provisioner_flags(self):
        captured_args = []

        def capturing_runner(args):
            captured_args.extend(args)
            return 0, "test-token\n", ""

        generate_token(
            subject="my-service.clients.sdx",
            provisioner_kid="my-key-id",
            provisioner_issuer="my-issuer",
            runner=capturing_runner,
        )
        assert "--kid" in captured_args
        assert "my-key-id" in captured_args
        assert "--issuer" in captured_args
        assert "my-issuer" in captured_args

    def test_generate_token_without_provisioner_flags(self):
        captured_args = []

        def capturing_runner(args):
            captured_args.extend(args)
            return 0, "test-token\n", ""

        generate_token(
            subject="my-service.clients.sdx",
            runner=capturing_runner,
        )
        assert "--kid" not in captured_args
        assert "--issuer" not in captured_args

    def test_generate_token_subject_in_args(self):
        captured_args = []

        def capturing_runner(args):
            captured_args.extend(args)
            return 0, "test-token\n", ""

        generate_token(
            subject="my-service.clients.sdx",
            runner=capturing_runner,
        )
        assert "my-service.clients.sdx" in captured_args
        assert "--provisioner-password-file" in captured_args
