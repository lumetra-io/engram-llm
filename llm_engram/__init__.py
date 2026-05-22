"""llm-engram — Engram memory tools for the `llm` CLI.

Registers six tools with the `llm` plugin system:

  * engram_store_memory
  * engram_query_memory
  * engram_list_memories
  * engram_list_buckets
  * engram_delete_memory
  * engram_clear_memories

Authentication is read from the ``LLM_ENGRAM_API_KEY`` (preferred) or
``ENGRAM_API_KEY`` environment variable. The default bucket can be set via
``LLM_ENGRAM_DEFAULT_BUCKET`` (falling back to ``"default"``). The REST base
URL defaults to ``https://api.lumetra.io`` and can be overridden with
``LLM_ENGRAM_API_BASE``.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
import llm

__all__ = [
    "engram_store_memory",
    "engram_query_memory",
    "engram_list_memories",
    "engram_list_buckets",
    "engram_delete_memory",
    "engram_clear_memories",
    "register_tools",
]

_DEFAULT_BASE_URL = "https://api.lumetra.io"
# Query responses can take 30-60s on cold paths; give them headroom.
_TIMEOUT = 120.0


# --- helpers ----------------------------------------------------------------


def _api_key() -> str:
    key = os.environ.get("LLM_ENGRAM_API_KEY") or os.environ.get("ENGRAM_API_KEY")
    if not key:
        raise RuntimeError(
            "Engram API key not configured. Set LLM_ENGRAM_API_KEY "
            "(or ENGRAM_API_KEY) in your environment. Get one at "
            "https://lumetra.io."
        )
    return key


def _base_url() -> str:
    return (os.environ.get("LLM_ENGRAM_API_BASE") or _DEFAULT_BASE_URL).rstrip("/")


def _default_bucket() -> str:
    return (os.environ.get("LLM_ENGRAM_DEFAULT_BUCKET") or "default").strip() or "default"


def _resolve_bucket(bucket: Optional[str]) -> str:
    if bucket is None:
        return _default_bucket()
    bucket = bucket.strip()
    return bucket or _default_bucket()


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
        "User-Agent": "llm-engram/0.1.0",
    }


def _request(method: str, path: str, **kwargs: Any) -> Any:
    url = f"{_base_url()}{path}"
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            response = client.request(method, url, headers=_headers(), **kwargs)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Engram request failed: {exc}") from exc

    if response.status_code >= 400:
        body = response.text[:500]
        raise RuntimeError(
            f"Engram API returned HTTP {response.status_code}: {body}"
        )

    if not response.content:
        return {"status_code": response.status_code}
    try:
        return response.json()
    except ValueError:
        return {"status_code": response.status_code, "text": response.text}


# --- tools ------------------------------------------------------------------


def engram_store_memory(content: str, bucket: Optional[str] = None) -> dict:
    """Store a fact, preference, or observation in Engram long-term memory.

    Use this to remember anything the user shares that should persist across
    sessions: names, preferences, project details, decisions, deadlines.

    Args:
        content: The atomic fact or note to remember (one concept per call
            works best). Required.
        bucket: Optional bucket name (e.g. project or topic). Defaults to the
            ``LLM_ENGRAM_DEFAULT_BUCKET`` env var or ``"default"``.

    Returns:
        The Engram store response including ``memory_id`` and ``bucket_name``.
    """
    text = (content or "").strip()
    if not text:
        raise ValueError("engram_store_memory requires non-empty `content`.")
    bucket_name = _resolve_bucket(bucket)
    return _request(
        "POST",
        f"/v1/buckets/{bucket_name}/memories",
        json={"content": text},
    )


def engram_query_memory(question: str, bucket: Optional[str] = None) -> dict:
    """Query Engram memory with a natural-language question.

    Performs semantic + knowledge-graph retrieval over stored memories and
    returns a synthesized answer plus supporting context.

    Args:
        question: The natural-language question to answer from memory.
            Required.
        bucket: Optional bucket to scope retrieval. Defaults to the
            ``LLM_ENGRAM_DEFAULT_BUCKET`` env var or ``"default"``.

    Returns:
        The Engram query response, including ``answer`` text and metadata.
    """
    q = (question or "").strip()
    if not q:
        raise ValueError("engram_query_memory requires non-empty `question`.")
    bucket_name = _resolve_bucket(bucket)
    # NOTE: REST field is `query`, not `question`.
    return _request(
        "POST",
        "/v1/query",
        json={"query": q, "buckets": [bucket_name]},
    )


def engram_list_memories(
    bucket: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List raw memories stored in an Engram bucket.

    Args:
        bucket: Bucket to list. Defaults to the ``LLM_ENGRAM_DEFAULT_BUCKET``
            env var or ``"default"``.
        limit: Maximum number of memories to return (default 50).
        offset: Pagination offset (default 0).

    Returns:
        A dict with ``memories``, ``total``, ``limit``, and ``offset`` keys.
    """
    bucket_name = _resolve_bucket(bucket)
    params = {"limit": int(limit), "offset": int(offset)}
    return _request(
        "GET",
        f"/v1/buckets/{bucket_name}/memories",
        params=params,
    )


def engram_list_buckets(limit: int = 50, offset: int = 0) -> dict:
    """List all Engram buckets available to this API key.

    Args:
        limit: Maximum number of buckets to return (default 50).
        offset: Pagination offset (default 0).

    Returns:
        A dict with a ``buckets`` array, each entry including ``name`` and
        ``memory_count``.
    """
    params = {"limit": int(limit), "offset": int(offset)}
    return _request("GET", "/v1/buckets", params=params)


def engram_delete_memory(memory_id: str, bucket: Optional[str] = None) -> dict:
    """Delete a single memory by its ``memory_id``.

    Args:
        memory_id: The id returned by ``engram_store_memory`` or
            ``engram_list_memories``. Required.
        bucket: Bucket the memory lives in. Defaults to the
            ``LLM_ENGRAM_DEFAULT_BUCKET`` env var or ``"default"``.

    Returns:
        The Engram delete response.
    """
    mid = (memory_id or "").strip()
    if not mid:
        raise ValueError("engram_delete_memory requires `memory_id`.")
    bucket_name = _resolve_bucket(bucket)
    return _request(
        "DELETE",
        f"/v1/buckets/{bucket_name}/memories/{mid}",
    )


def engram_clear_memories(bucket: Optional[str] = None) -> dict:
    """Delete ALL memories in a bucket. Destructive — confirm before calling.

    Args:
        bucket: Bucket to clear. Defaults to the ``LLM_ENGRAM_DEFAULT_BUCKET``
            env var or ``"default"``.

    Returns:
        The Engram clear response, including ``cleared_count``.
    """
    bucket_name = _resolve_bucket(bucket)
    return _request(
        "DELETE",
        f"/v1/buckets/{bucket_name}/memories",
    )


# --- plugin hook ------------------------------------------------------------


@llm.hookimpl
def register_tools(register):
    register(engram_store_memory)
    register(engram_query_memory)
    register(engram_list_memories)
    register(engram_list_buckets)
    register(engram_delete_memory)
    register(engram_clear_memories)
