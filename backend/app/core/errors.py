"""Типізовані помилки взаємодії з 1С MCBP_AI.

Кожен підклас має машинний `code` і `http_status`; обробник у `main.py`
перетворює їх на відповідь `{ "error": {"code","message"} }` з потрібним кодом.
"""

from __future__ import annotations


class MCBPError(Exception):
    code: str = "UPSTREAM_ERROR"
    http_status: int = 502

    def __init__(self, message: str, *, code: str | None = None, http_status: int | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status


class UpstreamError(MCBPError):
    code = "UPSTREAM_ERROR"
    http_status = 502


class NotFoundError(MCBPError):
    code = "NOT_FOUND"
    http_status = 404


class ParameterError(MCBPError):
    code = "BAD_PARAMETER"
    http_status = 400


class KeyMismatchError(MCBPError):
    """Внутрішній «ключ» бази не збігся (legacy `Key not found!`)."""

    code = "KEY_MISMATCH"
    http_status = 502


class PlusRequiredError(MCBPError):
    """Метод потребує зовнішнього розширення «MCBP Plus» (legacy `MCBP Plus not found!`)."""

    code = "PLUS_REQUIRED"
    http_status = 501
