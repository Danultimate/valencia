import logging
import os

import deepl

logger = logging.getLogger(__name__)

_translator: deepl.Translator | None = None


def _get_translator() -> deepl.Translator | None:
    global _translator
    if _translator is None:
        key = os.environ.get("DEEPL_API_KEY")
        if not key:
            logger.warning("DEEPL_API_KEY not set — translation disabled")
            return None
        _translator = deepl.Translator(key)
    return _translator


def translate_nl_to_es(titles: list[str]) -> list[str | None]:
    """Batch-translate Dutch titles to Spanish. Returns None per item on failure."""
    if not titles:
        return []
    translator = _get_translator()
    if not translator:
        return [None] * len(titles)
    try:
        results = translator.translate_text(titles, source_lang="NL", target_lang="ES")
        return [r.text for r in results]
    except Exception as exc:
        logger.warning("DeepL batch translation failed: %s", exc)
        return [None] * len(titles)
