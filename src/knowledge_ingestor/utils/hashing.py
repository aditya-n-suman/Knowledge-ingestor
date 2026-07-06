import hashlib


def url_digest(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()
