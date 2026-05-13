from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aether_api.services.rag.text import hashed_embedding

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_model: Any | None = None
_model_name: str | None = None


def _get_model(model_name: str, use_gpu: bool) -> Any | None:
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model
    try:
        from FlagEmbedding import BGEM3FlagModel

        logger.info("Loading embedding model: %s (gpu=%s)", model_name, use_gpu)
        _model = BGEM3FlagModel(model_name, use_fp16=use_gpu)
        _model_name = model_name
        logger.info("Embedding model loaded: %s", model_name)
        return _model
    except ImportError:
        logger.warning(
            "FlagEmbedding not installed. Install with: pip install FlagEmbedding"
        )
        return None
    except Exception:
        logger.exception("Failed to load embedding model: %s", model_name)
        return None


class BGEEmbedding:
    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        use_gpu: bool = False,
        dimensions: int = 1024,
    ) -> None:
        self._model_name = model_name
        self._use_gpu = use_gpu
        self._dimensions = dimensions

    def warm(self) -> None:
        """Force-load the model now, so the first request doesn't pay the
        several-second cold start. Safe to call multiple times."""
        _get_model(self._model_name, self._use_gpu)

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        model = _get_model(self._model_name, self._use_gpu)
        if model is None:
            return [hashed_embedding(text, self._dimensions) for text in texts]
        try:
            output = model.encode(texts, return_dense=True, return_sparse=False)
            return [vec.tolist() for vec in output["dense_vecs"]]
        except Exception:
            logger.exception("BGE-M3 encode failed, falling back to hash embedding")
            return [hashed_embedding(text, self._dimensions) for text in texts]

    def encode_query(self, query: str) -> list[float]:
        return self.encode_texts([query])[0]

    @property
    def is_real_model(self) -> bool:
        return _get_model(self._model_name, self._use_gpu) is not None

    @property
    def dimensions(self) -> int:
        if self.is_real_model:
            return 1024
        return self._dimensions
