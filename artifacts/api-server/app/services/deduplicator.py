import hashlib
import re


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\u0600-\u06FF]", "", text)
    return text


def compute_hash(title: str, description: str = "") -> str:
    normalized = normalize_text(f"{title} {description[:200]}")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
