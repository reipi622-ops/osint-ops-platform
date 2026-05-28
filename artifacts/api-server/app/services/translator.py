import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

CHUNK_SIZE = 3500  # Slightly smaller to avoid API limits

# Map standard ISO codes to Google Translate codes
LANG_MAP = {"he": "iw", "ar": "ar", "en": "en"}

# Emoji pattern for stripping before translation
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"   # Misc symbols, emoticons, transport
    "\U0001FA00-\U0001FA6F"   # Chess symbols etc
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)

# Common Arabic punctuation / ligatures that can confuse the translator
_NORMALISE_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]+")


def _preprocess(text: str) -> str:
    """Strip emojis and invisible chars; normalise whitespace."""
    text = _EMOJI_RE.sub(" ", text)
    text = _NORMALISE_RE.sub("", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def translate_text(text: str, source_lang: str = "ar", target_lang: str = "he") -> str:
    if not text or not text.strip():
        return text

    clean = _preprocess(text)
    if not clean:
        return text

    try:
        from deep_translator import GoogleTranslator

        src = LANG_MAP.get(source_lang, source_lang)
        tgt = LANG_MAP.get(target_lang, target_lang)
        translator = GoogleTranslator(source=src, target=tgt)

        if len(clean) <= CHUNK_SIZE:
            result = translator.translate(clean)
            return result or text

        # Split on sentence boundaries for better quality
        chunks: list[str] = []
        current = ""
        for sentence in re.split(r"(?<=[.!?،؟])\s+", clean):
            if len(current) + len(sentence) + 1 <= CHUNK_SIZE:
                current = f"{current} {sentence}".strip() if current else sentence
            else:
                if current:
                    chunks.append(current)
                current = sentence
        if current:
            chunks.append(current)

        parts = [translator.translate(chunk) or chunk for chunk in chunks]
        return " ".join(parts)

    except Exception as e:
        logger.warning(f"Translation failed ({source_lang}->{target_lang}): {e}")
        return text


def translate_ar_to_he(text: str) -> str:
    return translate_text(text, "ar", "he")
