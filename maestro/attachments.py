"""Discord message attachments → local files for cursor-agent Read."""

from __future__ import annotations

import logging
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import discord

logger = logging.getLogger(__name__)

TTL_SECONDS = 72 * 3600
# Keep this much free space after planned downloads.
MIN_FREE_RESERVE_BYTES = 512 * 1024 * 1024
CLEANUP_INTERVAL_SECONDS = 3600

_IMAGE_CONTENT_PREFIX = "image/"
_IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}
_DOC_CONTENT_TYPES = {
    "application/pdf",
    "application/json",
    "application/xml",
    "application/x-yaml",
    "application/yaml",
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/html",
    "text/css",
    "text/javascript",
    "text/x-python",
    "text/x-shellscript",
    "text/x-log",
}
_DOC_SUFFIXES = {
    ".pdf",
    ".log",
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".csv",
    ".yml",
    ".yaml",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".py",
    ".sh",
    ".bash",
    ".conf",
    ".cfg",
    ".ini",
    ".toml",
    ".env.example",
    ".out",
    ".err",
}

_ATTACH_MARKERS = ("### Attached files", "### Attached images")


@dataclass(frozen=True)
class SavedAttachment:
    path: Path
    original_filename: str
    content_type: str
    size: int
    kind: str  # image | document


@dataclass(frozen=True)
class SaveAttachmentsResult:
    saved: list[SavedAttachment]
    errors: list[str]


def attachments_root(state_dir: Path) -> Path:
    root = state_dir / "attachments"
    root.mkdir(parents=True, exist_ok=True)
    return root


def thread_attachments_dir(state_dir: Path, thread_id: int) -> Path:
    path = attachments_root(state_dir) / str(thread_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def oneshot_attachments_dir(state_dir: Path, message_id: int) -> Path:
    path = attachments_root(state_dir) / "_oneshot" / str(message_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_image_attachment(att: discord.Attachment) -> bool:
    ct = (att.content_type or "").strip().casefold()
    if ct.startswith(_IMAGE_CONTENT_PREFIX):
        return True
    suffix = Path(att.filename or "").suffix.casefold()
    return suffix in _IMAGE_SUFFIXES


def is_document_attachment(att: discord.Attachment) -> bool:
    """PDF, logs, and other text-like files (not images)."""
    if is_image_attachment(att):
        return False
    ct = (att.content_type or "").strip().casefold()
    if ct in _DOC_CONTENT_TYPES or ct.startswith("text/"):
        return True
    name = (att.filename or "").casefold()
    suffix = Path(name).suffix
    if suffix in _DOC_SUFFIXES:
        return True
    # bare "*.log.1" style: last suffix check already; also name ends with .log
    return name.endswith(".log") or name.endswith(".txt")


def is_allowed_attachment(att: discord.Attachment) -> bool:
    return is_image_attachment(att) or is_document_attachment(att)


def list_allowed_attachments(message: discord.Message) -> list[discord.Attachment]:
    return [a for a in message.attachments if is_allowed_attachment(a)]


def list_image_attachments(message: discord.Message) -> list[discord.Attachment]:
    """Backward-compatible alias: all allowed attachments (images + docs)."""
    return list_allowed_attachments(message)


def safe_filename(name: str) -> str:
    base = Path(name or "file").name
    cleaned = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE).strip("._")
    return (cleaned[:180] if cleaned else "file")


def disk_free_bytes(path: Path) -> int:
    path.mkdir(parents=True, exist_ok=True)
    return int(shutil.disk_usage(path).free)


def check_disk_for_download(dest_dir: Path, needed_bytes: int) -> str | None:
    """Return an error message if download should be refused, else None."""
    if needed_bytes < 0:
        needed_bytes = 0
    free = disk_free_bytes(dest_dir)
    required = needed_bytes + MIN_FREE_RESERVE_BYTES
    if free < required:
        return (
            f"Not enough disk space (free `{_fmt_bytes(free)}`, "
            f"need `{_fmt_bytes(needed_bytes)}` + "
            f"`{_fmt_bytes(MIN_FREE_RESERVE_BYTES)}` reserve)."
        )
    return None


def format_attached_files_block(saved: list[SavedAttachment]) -> str:
    if not saved:
        return ""
    lines = [
        "### Attached files",
        "",
        "Local files on the Maestro host. Use the Read tool on these paths "
        "(images, PDFs, logs, and text).",
        "",
    ]
    for item in saved:
        ct = item.content_type or item.kind
        lines.append(
            f"- `{item.path}` ({item.original_filename}, {ct}, "
            f"{_fmt_bytes(item.size)}, {item.kind})"
        )
    return "\n".join(lines)


def merge_text_with_attachments(text: str, saved: list[SavedAttachment]) -> str:
    body = (text or "").strip()
    block = format_attached_files_block(saved)
    if body and block:
        return f"{body}\n\n{block}"
    if block:
        return block
    return body


# Compat aliases used by older call sites / tests
SavedImage = SavedAttachment
SaveImagesResult = SaveAttachmentsResult
format_attached_images_block = format_attached_files_block
merge_text_with_images = merge_text_with_attachments


def status_preview(text: str, *, file_count: int = 0, image_count: int = 0, limit: int = 200) -> str:
    """Short Discord status line without dumping local paths."""
    count = file_count or image_count
    body = (text or "").strip()
    for marker in _ATTACH_MARKERS:
        if marker in body:
            body = body.split(marker, 1)[0].strip()
            break
    if not body:
        body = f"{count} file(s)" if count else "(no text)"
    elif count > 0:
        body = f"{body} · {count} file(s)"
    return body[:limit]


def count_attached_files_in_prompt(text: str) -> int:
    for marker in _ATTACH_MARKERS:
        if marker in text:
            return sum(
                1
                for line in text.split(marker, 1)[1].splitlines()
                if line.startswith("- `")
            )
    return 0


def purge_thread_attachments(state_dir: Path, thread_id: int) -> None:
    path = attachments_root(state_dir) / str(thread_id)
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
        logger.info("purged thread attachments thread=%s path=%s", thread_id, path)
    except OSError:
        logger.exception("failed to purge thread attachments thread=%s", thread_id)


def purge_expired_attachments(
    state_dir: Path, *, ttl_seconds: int = TTL_SECONDS, now: float | None = None
) -> int:
    """Delete attachment files older than TTL. Returns number of paths removed."""
    root = attachments_root(state_dir)
    cutoff = (now if now is not None else time.time()) - ttl_seconds
    removed = 0
    if not root.is_dir():
        return 0
    for path in sorted(root.rglob("*"), reverse=True):
        try:
            if path.is_file():
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
                    removed += 1
            elif path.is_dir():
                try:
                    next(path.iterdir())
                except StopIteration:
                    path.rmdir()
                    removed += 1
        except OSError:
            logger.exception("TTL cleanup failed path=%s", path)
    return removed


async def save_message_attachments(
    message: discord.Message,
    dest_dir: Path,
) -> SaveAttachmentsResult:
    """Download allowed attachments into dest_dir after a disk-space check."""
    files = list_allowed_attachments(message)
    if not files:
        return SaveAttachmentsResult(saved=[], errors=[])

    dest_dir.mkdir(parents=True, exist_ok=True)
    needed = sum(max(int(a.size or 0), 0) for a in files)
    disk_err = check_disk_for_download(dest_dir, needed)
    if disk_err:
        return SaveAttachmentsResult(saved=[], errors=[disk_err])

    saved: list[SavedAttachment] = []
    errors: list[str] = []
    for att in files:
        name = safe_filename(att.filename)
        out = dest_dir / f"{message.id}-{att.id}-{name}"
        kind = "image" if is_image_attachment(att) else "document"
        try:
            await att.save(out)
            size = out.stat().st_size if out.is_file() else int(att.size or 0)
            saved.append(
                SavedAttachment(
                    path=out.resolve(),
                    original_filename=att.filename or name,
                    content_type=(att.content_type or kind).strip(),
                    size=size,
                    kind=kind,
                )
            )
        except Exception as e:
            logger.exception(
                "attachment save failed message=%s att=%s", message.id, att.id
            )
            errors.append(f"Failed to save `{att.filename or name}`: {type(e).__name__}")
            try:
                out.unlink(missing_ok=True)
            except OSError:
                pass

    return SaveAttachmentsResult(saved=saved, errors=errors)


async def save_message_images(
    message: discord.Message,
    dest_dir: Path,
) -> SaveAttachmentsResult:
    """Backward-compatible alias for save_message_attachments."""
    return await save_message_attachments(message, dest_dir)


def _fmt_bytes(n: int) -> str:
    value = float(max(0, n))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024.0 or unit == "TiB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{n} B"
