import logging
from typing import Optional

logger = logging.getLogger(__name__)

CHUNK_SIZE = 4000

# Map standard ISO codes to Google Translate codes
LANG_MAP = {"he": "iw", "ar": "ar", "en": "en"}


def translate_text(text: str, source_lang: str = "ar", target_lang: str = "he") -> str:
    if not text or not text.strip():
        return text
    try:
        from deep_translator import GoogleTranslator

        src = LANG_MAP.get(source_lang, source_lang)
        tgt = LANG_MAP.get(target_lang, target_lang)
        translator = GoogleTranslator(source=src, target=tgt)

        if len(text) <= CHUNK_SIZE:
            result = translator.translate(text)
            return result or text

        chunks = [text[i : i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
        parts = [translator.translate(chunk) or chunk for chunk in chunks]
        return " ".join(parts)
    except Exception as e:
        logger.warning(f"Translation failed ({source_lang}->{target_lang}): {e}")
        return text


def translate_ar_to_he(text: str) -> str:
    return translate_text(text, "ar", "he")
