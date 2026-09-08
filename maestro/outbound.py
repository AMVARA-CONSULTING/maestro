"""Agent → Discord outbound file attachments."""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Keep under Discord ~25 MiB hard limit.
_MAX_FILES_PER_MESSAGE = 10
_MAX_FILE_BYTES = 24 * 1024 * 1024

_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})
# Docs / artifacts agents commonly produce for Luipy (never secrets: no .env, keys, pem).
_DOC_SUFFIXES = frozenset(
    {
        ".json",
        ".html",
        ".htm",
        ".txt",
        ".md",
        ".csv",
        ".log",
        ".pdf",
        ".svg",
        ".xml",
        ".yaml",
        ".yml",
        ".red",
        ".zip",
        ".webm",
    }
)
_ALLOWED_SUFFIXES = _IMAGE_SUFFIXES | _DOC_SUFFIXES

_OUTBOUND_MARKER_RE = re.compile(
    r"(?im)^###\s*Outbound files\s*$([\s\S]*?)(?=^###\s|\Z)"
)


def outbound_root(state_dir: Path) -> Path:
    root = state_dir / "outbound"
    root.mkdir(parents=True, exist_ok=True)
    return root


def thread_outbound_dir(state_dir: Path, thread_id: int) -> Path:
    path = outbound_root(state_dir) / str(int(thread_id))
    path.mkdir(parents=True, exist_ok=True)
    return path


def oneshot_outbound_dir(state_dir: Path, message_id: int) -> Path:
    path = outbound_root(state_dir) / "_oneshot" / str(int(message_id))
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_allowed_outbound(path: Path) -> bool:
    """True if path looks like a safe outbound artifact (by suffix)."""
    return path.suffix.casefold() in _ALLOWED_SUFFIXES


def list_outbound_files(directory: Path) -> list[Path]:
    """Return allowed outbound files in directory (non-recursive), oldest first."""
    if not directory.is_dir():
        return []
    files: list[Path] = []
    for p in sorted(directory.iterdir(), key=lambda x: x.stat().st_mtime):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        if not is_allowed_outbound(p):
            logger.warning("skip outbound disallowed suffix path=%s", p)
            continue
        try:
            size = p.stat().st_size
            if size <= 0 or size > _MAX_FILE_BYTES:
                logger.warning("skip outbound file size path=%s bytes=%s", p, size)
                continue
        except OSError:
            continue
        files.append(p)
    return files


def list_outbound_images(directory: Path) -> list[Path]:
    """Backward-compatible alias: images only."""
    return [
        p
        for p in list_outbound_files(directory)
        if p.suffix.casefold() in _IMAGE_SUFFIXES
    ]


def parse_outbound_paths_from_text(text: str) -> list[Path]:
    """Optional ### Outbound files block with absolute paths (one per line)."""
    if not text:
        return []
    m = _OUTBOUND_MARKER_RE.search(text)
    if not m:
        return []
    out: list[Path] = []
    for line in m.group(1).splitlines():
        raw = line.strip().strip("`").strip()
        if not raw or raw.startswith("#") or raw.startswith("-"):
            # allow "- /path" bullets
            raw = raw.lstrip("-").strip().strip("`").strip()
        if not raw.startswith("/"):
            continue
        p = Path(raw)
        if p.is_file() and is_allowed_outbound(p):
            try:
                size = p.stat().st_size
            except OSError:
                continue
            if size <= 0 or size > _MAX_FILE_BYTES:
                logger.warning("skip outbound marker size path=%s bytes=%s", p, size)
                continue
            out.append(p)
        elif p.is_file():
            logger.warning("skip outbound marker disallowed suffix path=%s", p)
    return out


def collect_outbound_files(
    *,
    state_dir: Path,
    scope_dir: Path | None,
    agent_text: str = "",
) -> list[Path]:
    """Merge scope-dir files + explicit paths from agent text (deduped)."""
    _ = state_dir  # reserved for future global outbound scopes
    seen: set[Path] = set()
    ordered: list[Path] = []
    for p in list_outbound_files(scope_dir) if scope_dir is not None else []:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        ordered.append(p)
    for p in parse_outbound_paths_from_text(agent_text):
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        ordered.append(p)
    return ordered


def collect_outbound_images(
    *,
    state_dir: Path,
    scope_dir: Path | None,
    agent_text: str = "",
) -> list[Path]:
    """Backward-compatible alias for collect_outbound_files."""
    return collect_outbound_files(
        state_dir=state_dir,
        scope_dir=scope_dir,
        agent_text=agent_text,
    )


def mark_outbound_sent(paths: list[Path]) -> None:
    """Move sent files aside so the next turn does not re-upload them."""
    for p in paths:
        try:
            sent_dir = p.parent / ".sent"
            sent_dir.mkdir(parents=True, exist_ok=True)
            dest = sent_dir / p.name
            if dest.exists():
                dest = sent_dir / f"{p.stem}-{p.stat().st_mtime_ns}{p.suffix}"
            shutil.move(str(p), str(dest))
        except OSError:
            logger.exception("failed to archive outbound file path=%s", p)


def purge_thread_outbound(state_dir: Path, thread_id: int) -> None:
    path = outbound_root(state_dir) / str(int(thread_id))
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
        logger.info("purged thread outbound thread=%s", thread_id)
    except OSError:
        logger.exception("failed to purge outbound thread=%s", thread_id)


def chunk_paths(paths: list[Path], size: int = _MAX_FILES_PER_MESSAGE) -> list[list[Path]]:
    return [paths[i : i + size] for i in range(0, len(paths), size)]
