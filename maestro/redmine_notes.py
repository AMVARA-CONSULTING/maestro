"""MaestroBot Redmine journal helpers (notes + issue id extraction)."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import aiohttp

logger = logging.getLogger("maestro.redmine")

# KM0 catalog projects: if no per-project redmine_doc_issue_id, use this hub.
KM0_FALLBACK_ISSUE_ID = 7594
KM0_PROJECT_IDS = frozenset(
    {
        "km0-web",
        "km0-mail",
        "km0-auth",
        "opencloud",
        "sunday-updates",
    }
)

# How many leading hex chars of the Cursor chat UUID go in collapse titles.
CURSOR_STAMP_LEN = 8

# Global orphan sink when close-note targets are empty (project none, no #issue).
# Overridden at runtime by REDMINE_DEFAULT_ISSUE_ID (Maestro Lost & Found).
MAESTRO_LOST_FOUND_ISSUE_ID = 8077

# Catalog / family hubs. Prefer a work ticket over these when picking one mention.
DOC_HUB_ISSUE_IDS = frozenset(
    {
        8066,  # maestro
        7530,  # opencloud
        7529,  # km0-web
        7605,  # km0-mail
        7594,  # KM0 family fallback
        8077,  # Lost & Found
    }
)

# #8066, issue 8066, ticket 8066, /issues/8066, redmine…/issues/8066
_ISSUE_ID_RE = re.compile(
    r"(?:"
    r"https?://[^\s]/issues/"
    r"|/(?:issues?)/"
    r"|(?:^|[^\w])(?:#|rm\s*#?|ticket\s+|issue\s+|issues?\s+)"
    r")"
    r"(\d{3,6})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RedmineConfig:
    url: str
    api_key: str
    default_issue_id: int | None = None

    @property
    def configured(self) -> bool:
        return bool(self.url.strip() and self.api_key.strip())


def load_redmine_config_from_env() -> RedmineConfig:
    url = (os.environ.get("REDMINE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("REDMINE_API_KEY") or "").strip()
    raw_default = (os.environ.get("REDMINE_DEFAULT_ISSUE_ID") or "").strip()
    default_id: int | None = None
    if raw_default.isdigit():
        default_id = int(raw_default)
    elif MAESTRO_LOST_FOUND_ISSUE_ID > 0:
        default_id = MAESTRO_LOST_FOUND_ISSUE_ID
    return RedmineConfig(url=url, api_key=key, default_issue_id=default_id)


def extract_issue_ids(*texts: str) -> list[int]:
    """Return unique Redmine issue ids in first-seen order."""
    seen: set[int] = set()
    out: list[int] = []
    for text in texts:
        if not text:
            continue
        for m in _ISSUE_ID_RE.finditer(text):
            iid = int(m.group(1))
            if iid in seen:
                continue
            seen.add(iid)
            out.append(iid)
    return out


def merge_issue_ids(*groups: list[int] | tuple[int, ...] | None) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for group in groups:
        if not group:
            continue
        for iid in group:
            n = int(iid)
            if n in seen:
                continue
            seen.add(n)
            out.append(n)
    return out


def wrap_collapse(*, title: str, body: str) -> str:
    """Textile collapse wrapper for Redmine journals."""
    t = " ".join((title or "Note").split())
    b = (body or "").strip()
    return f"{{{{collapse({t})\n\n{b}\n\n}}}}"


def cursor_session_stamp(
    cursor_chat_id: str, *, length: int = CURSOR_STAMP_LEN
) -> str:
    """Leading hex chars of the Cursor chat UUID (collapse title stamp).

    Example: ``9b24dbfe-9335-…`` → ``9b24dbfe``. Not the Discord thread HHMM
    and not the Redmine issue id.
    """
    raw = re.sub(r"[^0-9a-fA-F]", "", (cursor_chat_id or "").strip())
    if not raw:
        return "0" * length
    return raw[:length].lower()


def collapse_title(
    *,
    topic: str,
    project_id: str,
    cursor_chat_id: str,
) -> str:
    """Build ``Topic · project · <cursor-stamp>`` for Redmine collapse headers."""
    topic_s = " ".join((topic or "Note").split()) or "Note"
    project_s = " ".join((project_id or "none").split()) or "none"
    stamp = cursor_session_stamp(cursor_chat_id)
    return f"{topic_s} · {project_s} · {stamp}"


def resolve_catalog_doc_issue_id(
    *,
    project_id: str,
    redmine_doc_issue_id: int | None,
) -> int | None:
    """Per-project doc ticket, or KM0 fallback #7594 when the project is KM0."""
    if redmine_doc_issue_id is not None and int(redmine_doc_issue_id) > 0:
        return int(redmine_doc_issue_id)
    if project_id.strip().casefold() in KM0_PROJECT_IDS:
        return KM0_FALLBACK_ISSUE_ID
    return None


def resolve_orphan_fallback_issue_id(default_issue_id: int | None) -> int | None:
    """Last-resort Lost & Found ticket when no catalog/mentioned targets exist."""
    if default_issue_id is not None and int(default_issue_id) > 0:
        return int(default_issue_id)
    if MAESTRO_LOST_FOUND_ISSUE_ID > 0:
        return MAESTRO_LOST_FOUND_ISSUE_ID
    return None


def pick_primary_mentioned_issue_id(
    mentioned_issue_ids: list[int] | tuple[int, ...] | None,
) -> int | None:
    """Pick one coherent work ticket from mentions (never fan-out).

    Prefer the first id that is *not* a known doc/hub/L&F ticket.
    If every mention is a hub, use the first mention.
    """
    ids = merge_issue_ids(mentioned_issue_ids)
    if not ids:
        return None
    for iid in ids:
        if iid not in DOC_HUB_ISSUE_IDS:
            return iid
    return ids[0]


def resolve_close_note_issue_id(
    *,
    project_id: str,
    redmine_doc_issue_id: int | None,
    mentioned_issue_ids: list[int] | tuple[int, ...] | None,
    default_issue_id: int | None,
) -> int | None:
    """Single close-note target.

    Hierarchy (exactly one destination):
    1. Catalog project hub (or KM0 fallback #7594)
    2. One primary mentioned work ticket
    3. Lost & Found (#8077 / REDMINE_DEFAULT_ISSUE_ID)
    """
    hub = resolve_catalog_doc_issue_id(
        project_id=project_id,
        redmine_doc_issue_id=redmine_doc_issue_id,
    )
    if hub is not None:
        return hub
    primary = pick_primary_mentioned_issue_id(mentioned_issue_ids)
    if primary is not None:
        return primary
    return resolve_orphan_fallback_issue_id(default_issue_id)


_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_MD_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_MD_CODE_RE = re.compile(r"`([^`]+)`")
_MD_HEADING_RE = re.compile(r"(?m)^#{1,6}\s+")
_MD_BULLET_RE = re.compile(r"^(\s*)(?:[-•]|\d+\.)\s+(.*)$")


def discord_summary_to_textile_safe(summary: str) -> str:
    """Normalize Discord/Markdown-ish summary into Textile (mid-session style).

    Converts common Markdown to Textile. Keeps ASD-STE100 bullets as a list.
    """
    text = (summary or "").strip()
    if not text:
        return ""
    # [label](url) → "label":url (Textile link); bare URLs stay as text
    text = _MD_LINK_RE.sub(r'"\1":\2', text)
    # Protect **bold** before single-* italic so Textile *strong* is not re-wrapped.
    bold_parts: list[str] = []

    def _hold_bold(m: re.Match[str]) -> str:
        bold_parts.append(m.group(1))
        return f"\x00B{len(bold_parts) - 1}\x00"

    text = _MD_BOLD_RE.sub(_hold_bold, text)
    text = _MD_ITALIC_RE.sub(r"_\1_", text)
    for i, content in enumerate(bold_parts):
        text = text.replace(f"\x00B{i}\x00", f"*{content}*")
    text = _MD_CODE_RE.sub(r"@\1@", text)
    text = _MD_HEADING_RE.sub("h3. ", text)
    out: list[str] = []
    for line in text.splitlines():
        m = _MD_BULLET_RE.match(line)
        if m:
            indent, rest = m.group(1), m.group(2)
            depth = len(indent.replace("\t", "  ")) // 2
            prefix = "*" * max(1, depth + 1)
            out.append(f"{prefix} {rest}")
        else:
            out.append(line)
    return "\n".join(out).strip()


def build_session_close_note(
    *,
    project_id: str,
    host: str,
    issue_id: int,
    thread_name: str,
    cursor_chat_id: str,
    discord_summary: str,
) -> str:
    """Close note in the same Textile / ASD-STE100 style as mid-session notes.

    No metadata dump, no ``<pre>``, no automatic footer. Title stamp carries
    the Cursor chat id; project id is in the collapse title.
    """
    _ = (issue_id, thread_name)  # signature kept for call-site compatibility
    title = collapse_title(
        topic="Session update",
        project_id=project_id,
        cursor_chat_id=cursor_chat_id,
    )
    proj = (project_id or "none").strip() or "none"
    host_s = (host or "unknown").strip() or "unknown"
    if proj.casefold() == "none":
        lead = f"Closed the Discord persist session on @{host_s}@."
    else:
        lead = (
            f"Closed the Discord persist session for @{proj}@ "
            f"on @{host_s}@."
        )
    summary = discord_summary_to_textile_safe(discord_summary)
    if summary:
        body = f"{lead}\n\n{summary}"
    else:
        body = f"{lead}\n\nNo session summary was available."
    return wrap_collapse(title=title, body=body)


class RedmineNotesClient:
    """Minimal Redmine REST client for MaestroBot journal notes."""

    def __init__(self, cfg: RedmineConfig, *, timeout: float = 30.0) -> None:
        self.cfg = cfg
        self.timeout = timeout

    def issue_url(self, issue_id: int) -> str:
        return f"{self.cfg.url.rstrip('/')}/issues/{int(issue_id)}"

    async def add_note(self, issue_id: int, notes: str) -> None:
        if not self.cfg.configured:
            raise RuntimeError("Redmine is not configured (REDMINE_URL / REDMINE_API_KEY)")
        url = f"{self.cfg.url.rstrip('/')}/issues/{int(issue_id)}.json"
        payload = {"issue": {"notes": notes}}
        headers = {
            "Content-Type": "application/json",
            "X-Redmine-API-Key": self.cfg.api_key,
        }
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.put(url, json=payload, headers=headers) as resp:
                if resp.status in {200, 204}:
                    return
                body = (await resp.text())[:500]
                raise RuntimeError(
                    f"Redmine PUT issue {issue_id} failed: HTTP {resp.status} {body}"
                )


async def post_session_close_notes(
    *,
    cfg: RedmineConfig,
    issue_ids: list[int],
    project_id: str,
    host: str,
    thread_name: str,
    cursor_chat_id: str,
    discord_summary: str,
) -> list[tuple[int, str | None]]:
    """Post a close note to each issue. Returns (issue_id, error_or_None)."""
    if not cfg.configured or not issue_ids:
        return []
    client = RedmineNotesClient(cfg)
    results: list[tuple[int, str | None]] = []
    for iid in issue_ids:
        note = build_session_close_note(
            project_id=project_id,
            host=host,
            issue_id=iid,
            thread_name=thread_name,
            cursor_chat_id=cursor_chat_id,
            discord_summary=discord_summary,
        )
        try:
            await client.add_note(iid, note)
            results.append((iid, None))
            logger.info("redmine close note ok issue=%s", iid)
        except Exception as e:
            logger.warning("redmine close note failed issue=%s: %s", iid, e)
            results.append((iid, str(e)))
    return results
