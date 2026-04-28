"""Checkpoint storage factory for multi-agent workflows.

This module exposes a single ``create_checkpoint_storage`` helper that returns
a ``CheckpointStorage`` instance using the storages shipped with
``agent-framework`` 1.2.1:

* ``InMemoryCheckpointStorage``  — default; in-process, lost on restart.
* ``FileCheckpointStorage``      — JSON-on-disk with atomic writes and
  path-traversal protection.
* ``CosmosCheckpointStorage``    — durable, partitioned by ``workflow_name``,
  shipped in ``agent_framework_azure_cosmos``.

Selection is driven by the ``WORKFLOW_CHECKPOINT_BACKEND`` environment
variable (``memory`` | ``file`` | ``cosmos``) so deployments can opt into
durable checkpointing without touching agent code.

Storage instances are cached per (backend, session) tuple so successive
agent invocations within the same process share the same in-memory state
(matching the behaviour of the previous hand-rolled ``DictCheckpointStorage``).

Helpers:

* ``prune_checkpoints`` — bound the number of saved checkpoints per workflow
  using only the public ``CheckpointStorage`` protocol, replacing the
  ``_RETENTION`` cap that lived inside the old custom storage classes.
"""

from __future__ import annotations

import logging
import os
from threading import Lock
from typing import Any, Dict, Optional, Tuple

from agent_framework import CheckpointStorage, FileCheckpointStorage, InMemoryCheckpointStorage

logger = logging.getLogger(__name__)


_BACKEND_ENV = "WORKFLOW_CHECKPOINT_BACKEND"
_FILE_DIR_ENV = "WORKFLOW_CHECKPOINT_DIR"
_DEFAULT_FILE_DIR = ".checkpoints"

_storage_cache: Dict[Tuple[str, str], CheckpointStorage] = {}
_cache_lock = Lock()


def _resolve_backend() -> str:
    backend = (os.getenv(_BACKEND_ENV) or "memory").strip().lower()
    if backend not in {"memory", "file", "cosmos"}:
        logger.warning(
            "Unknown %s=%r; falling back to 'memory'. Allowed values: memory, file, cosmos.",
            _BACKEND_ENV,
            backend,
        )
        backend = "memory"
    return backend


def _build_file_storage(session_id: str) -> CheckpointStorage:
    base_dir = os.getenv(_FILE_DIR_ENV) or _DEFAULT_FILE_DIR
    # Scope per session so concurrent sessions cannot accidentally read each
    # other's checkpoint files. Session IDs are sanitized by collapsing any
    # path-traversal characters before joining.
    safe_session = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in session_id)
    storage_path = os.path.join(base_dir, safe_session)
    return FileCheckpointStorage(storage_path)


def _build_cosmos_storage() -> CheckpointStorage:
    # Imported lazily so the cosmos extra is only required when actually used.
    try:
        from agent_framework_azure_cosmos import CosmosCheckpointStorage
    except ImportError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "WORKFLOW_CHECKPOINT_BACKEND=cosmos requires the "
            "'agent-framework-azure-cosmos' package to be installed."
        ) from exc

    # Try managed-identity first when no AZURE_COSMOS_KEY is configured. The
    # CosmosCheckpointStorage already reads endpoint / database / container /
    # key from AZURE_COSMOS_* environment variables, so we only need to
    # supply a credential for the keyless case.
    if os.getenv("AZURE_COSMOS_KEY"):
        return CosmosCheckpointStorage()

    try:
        from azure.identity.aio import DefaultAzureCredential
    except ImportError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "WORKFLOW_CHECKPOINT_BACKEND=cosmos without AZURE_COSMOS_KEY "
            "requires 'azure-identity' to be installed for managed-identity auth."
        ) from exc

    return CosmosCheckpointStorage(credential=DefaultAzureCredential())


def create_checkpoint_storage(session_id: str) -> CheckpointStorage:
    """Return a per-session ``CheckpointStorage`` from configuration.

    Args:
        session_id: Used to scope file-backed storage to a per-session
            directory and to key the in-process cache so successive calls
            within the same process share state.

    Returns:
        A storage instance compatible with the 1.2.x ``CheckpointStorage``
        protocol.
    """
    backend = _resolve_backend()
    cache_key = (backend, session_id)

    with _cache_lock:
        existing = _storage_cache.get(cache_key)
        if existing is not None:
            return existing

        if backend == "file":
            storage: CheckpointStorage = _build_file_storage(session_id)
        elif backend == "cosmos":
            storage = _build_cosmos_storage()
        else:
            storage = InMemoryCheckpointStorage()

        _storage_cache[cache_key] = storage
        logger.info("Created %s checkpoint storage for session=%s", backend, session_id)
        return storage


def reset_storage_cache() -> None:
    """Clear the in-process storage cache. Intended for tests."""
    with _cache_lock:
        _storage_cache.clear()


async def prune_checkpoints(
    storage: CheckpointStorage,
    workflow_name: str,
    *,
    retain: int,
) -> None:
    """Bound the number of checkpoints retained for ``workflow_name``.

    Only the most recent ``retain`` checkpoints (by ``timestamp``) are kept;
    older ones are deleted via the public ``CheckpointStorage.delete`` method.
    Failures are logged and swallowed so checkpoint hygiene cannot break a
    chat turn.
    """
    if retain <= 0:
        return
    try:
        checkpoints = await storage.list_checkpoints(workflow_name=workflow_name)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Unable to list checkpoints for pruning (%s): %s", workflow_name, exc)
        return

    if len(checkpoints) <= retain:
        return

    # Most-recent-first ordering using the timestamp field of WorkflowCheckpoint.
    checkpoints.sort(key=lambda cp: getattr(cp, "timestamp", "") or "", reverse=True)
    for stale in checkpoints[retain:]:
        try:
            await storage.delete(stale.checkpoint_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to prune checkpoint %s: %s", stale.checkpoint_id, exc)


async def purge_checkpoints(storage: CheckpointStorage, workflow_name: Optional[str]) -> None:
    """Delete every checkpoint for ``workflow_name`` using the public protocol.

    No-ops when ``workflow_name`` is missing (the protocol cannot enumerate
    across workflows).
    """
    if not workflow_name:
        return
    try:
        ids = await storage.list_checkpoint_ids(workflow_name=workflow_name)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Unable to list checkpoint ids for purge (%s): %s", workflow_name, exc)
        return
    for checkpoint_id in ids:
        try:
            await storage.delete(checkpoint_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Failed to delete checkpoint %s during purge: %s", checkpoint_id, exc)


__all__ = [
    "create_checkpoint_storage",
    "prune_checkpoints",
    "purge_checkpoints",
    "reset_storage_cache",
]


def _coerce_checkpoint_storage(candidate: Any) -> Optional[CheckpointStorage]:
    """Validate that ``candidate`` looks like a ``CheckpointStorage`` instance.

    Used by callers that accept storage overrides from configuration so that
    test doubles can be substituted without inheriting from the protocol class.
    """
    if candidate is None:
        return None
    for method_name in ("save", "load", "delete", "get_latest", "list_checkpoints", "list_checkpoint_ids"):
        if not callable(getattr(candidate, method_name, None)):
            return None
    return candidate  # type: ignore[return-value]
