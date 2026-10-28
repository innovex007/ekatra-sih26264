"""Optional multilingual-e5 embedder (USE_E5=auto|on|off). Returns None when unavailable;
the resolver then falls back to transliteration + phonetic fuzzy matching."""
import logging

from .config import USE_E5

log = logging.getLogger("ekatra.embedder")
_state = {"tried": False, "model": None, "reason": ""}


class E5:
    def __init__(self, model):
        self.model = model

    def encode(self, texts, kind="query"):
        return self.model.encode([f"{kind}: {t}" for t in texts], normalize_embeddings=True,
                                 batch_size=64, show_progress_bar=False)


def get_embedder():
    if not _state["tried"]:
        _state["tried"] = True
        if USE_E5 == "off":
            _state["reason"] = "USE_E5=off"
        else:
            try:
                from sentence_transformers import SentenceTransformer

                try:  # cached copy first: no network traffic
                    model = SentenceTransformer("intfloat/multilingual-e5-small", device="cpu", local_files_only=True)
                except Exception:  # noqa: BLE001 - not cached yet: allow a one-time download
                    model = SentenceTransformer("intfloat/multilingual-e5-small", device="cpu")
                _state["model"] = E5(model)
            except Exception as e:  # noqa: BLE001 - any failure means fallback
                _state["reason"] = f"{type(e).__name__}: {str(e)[:120]}"
                log.warning("e5 unavailable, using transliteration+fuzzy fallback (%s)", _state["reason"])
    return _state["model"]


def method_name() -> str:
    return "multilingual-e5-small" if get_embedder() else "transliteration+phonetic-fuzzy"
