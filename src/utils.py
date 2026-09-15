import base64
import hashlib
import json


def compute_etag(row: dict) -> str:
    digest = hashlib.sha1(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16]
    return f'"{digest}"'


def encode_cursor(*parts) -> str:
    raw = "|".join(str(p) for p in parts)
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(token: str) -> list:
    return base64.urlsafe_b64decode(token.encode()).decode().split("|")
