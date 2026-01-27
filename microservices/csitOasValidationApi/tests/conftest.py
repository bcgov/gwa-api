"""
Shared test fixtures and utilities for the entire test suite
"""

import json
import logging
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 

import pytest
from httpx import Request, Response
import respx

from fastapi import FastAPI
from fastapi.testclient import TestClient

from csit_validation.main import app as application


# ── Your existing app/client fixtures ───────────────────────────────────────

@pytest.fixture
def app() -> FastAPI:
    application.dependency_overrides = {}
    return application


@pytest.fixture
def client(app) -> TestClient:
    class LoggingTestClient(TestClient):
        def request(self, method, url, **kwargs):
            # ── Log REQUEST ─────────────────────────────────────────────────────
            headers = kwargs.get("headers") or {}
            sorted_headers = sorted(headers.items(), key=lambda x: x[0].lower())

            message = f"→ REQUEST:\n{method.upper()} {url}\n"
            message += "  Headers:\n"
            message += "\n".join(f"    {key}: {value}" for key, value in sorted_headers)

            # Handle request body
            body_raw = kwargs.get("content") or kwargs.get("data") or kwargs.get("json")
            if body_raw:
                body_str = self._format_body(body_raw)
                message += f"\n  Body:\n{body_str}"

            http_logger.debug(message)

            # ── Send request ─────────────────────────────────────────────────────
            response = super().request(method, url, **kwargs)

            # ── Log RESPONSE ─────────────────────────────────────────────────────
            sorted_headers = sorted(response.headers.items(), key=lambda x: x[0].lower())

            message = f"← RESPONSE:\n{response.status_code} {response.reason_phrase or ''}\n"
            message += "  Headers:\n"
            message += "\n".join(f"    {key}: {value}" for key, value in sorted_headers)

            # Handle response body
            if response.content:
                body_str = self._format_body(response.content)
                message += f"\n  Body:\n{body_str}"

            http_logger.debug(message)

            return response

        def _format_body(self, raw_body: any) -> str:
            """Format body for logging: pretty-print JSON when possible"""
            if isinstance(raw_body, (dict, list)):
                # Already parsed data (e.g. json=...)
                try:
                    return "    " + json.dumps(raw_body, indent=2, ensure_ascii=False).replace("\n", "\n    ")
                except Exception:
                    return f"    <unserializable object: {type(raw_body).__name__}>"

            if isinstance(raw_body, (bytes, bytearray)):
                try:
                    text = raw_body.decode("utf-8", errors="replace").strip()
                except Exception:
                    return f"    <binary — {len(raw_body)} bytes>"

                # Try to parse as JSON and pretty-print
                try:
                    data = json.loads(text)
                    pretty = json.dumps(data, indent=2, ensure_ascii=False)
                    return "    " + pretty.replace("\n", "\n    ")
                except json.JSONDecodeError:
                    # Not JSON → return plain text (indented)
                    return "    " + text.replace("\n", "\n    ")

            # Fallback for other types
            return f"    {str(raw_body)}"

    return LoggingTestClient(app)


# ── HTTP request/response logging helper ─────────────────────────────────────

http_logger = logging.getLogger("test.http.detail")
http_logger.setLevel(logging.DEBUG)


def log_request(request: Request):
    body_str = None
    if request.content:
        try:
            body_str = request.content.decode("utf-8")
        except UnicodeDecodeError:
            body_str = f"<binary {len(request.content)} bytes>"

    # Sort headers alphabetically for deterministic output
    sorted_headers = sorted(request.headers.items())

    message = f"→ REQUEST: {request.method} {request.url}\n"
    message += "  Headers:\n"
    message += "\n".join(f"    {key}: {value}" for key, value in sorted_headers)
    if body_str:
        message += f"\n  Body:\n    {body_str}"

    http_logger.debug(message)


def log_response(response: Response):
    body_str = None
    if response.content:
        try:
            body_str = response.content.decode("utf-8")
        except UnicodeDecodeError:
            body_str = f"<binary {len(response.content)} bytes>"

    # Sort headers alphabetically for deterministic output
    sorted_headers = sorted(response.headers.items())

    message = f"← RESPONSE: {response.status_code} {response.reason_phrase}\n"
    message += "  Headers:\n"
    message += "\n".join(f"    {key}: {value}" for key, value in sorted_headers)
    if body_str:
        message += f"\n  Body:\n    {body_str}"

    http_logger.debug(message)


@pytest.fixture
def enable_http_logging():
    """
    Fixture to enable detailed HTTP logging for all mocked routes in the test.
    Use with @pytest.mark.usefixtures("enable_http_logging")
    """
    original_side_effect = None

    def _wrap_side_effect(original):
        async def wrapped(request, **kwargs):
            resp = kwargs.get("response") or original(request, **kwargs)
            log_request(request)
            log_response(resp)
            return resp
        return wrapped

    # Apply logging to any new route created during this test
    def logged_route(*args, **kwargs):
        route = respx.route(*args, **kwargs)
        if route._side_effect:
            original_side_effect = route._side_effect
            route.side_effect = _wrap_side_effect(original_side_effect)
        else:
            # If no side effect, wrap the default response
            route.side_effect = _wrap_side_effect(lambda r: route.default_response)
        return route

    original_route = respx.route
    respx.route = logged_route

    yield

    # Cleanup after test
    respx.route = original_route


# fixture to force debug logging output
@pytest.fixture
def http_debug(caplog):
    caplog.set_level(logging.DEBUG, logger="test.http.detail")
    logging.getLogger("httpx").setLevel(logging.DEBUG)