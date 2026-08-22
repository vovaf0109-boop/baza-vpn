import secrets
import re


SUBSCRIPTION_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")


def generate_subscription_token() -> str:
    return secrets.token_urlsafe(32)


def is_valid_subscription_token(token: str) -> bool:
    return bool(SUBSCRIPTION_TOKEN_RE.fullmatch(token))


def generate_device_identifier() -> str:
    return secrets.token_hex(12)
