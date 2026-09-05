"""Persistent Discord thread ↔ Cursor chatId mapping."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionRecord:
    thread_id: int
    cursor_chat_id: str
    workspace: str
    project_id: str
    host: str
    owner_id: int
    parent_channel_id: int
    anchor_message_id: int
    status: str  # active | closed
    created_at: str
    closed_at: str | None = None
    thread_name: str = ""
    #: Redmine issue ids mentioned during the session (for MaestroBot notes).
    mentioned_issue_ids: list[int] | None = None

    @classmethod
    def from_dict(cls, raw: dict) -> SessionRecord:
        mentioned_raw = raw.get("mentioned_issue_ids") or []
        mentioned: list[int] = []
        if isinstance(mentioned_raw, list):
            for item in mentioned_raw:
                try:
                    n = int(item)
                except (TypeError, ValueError):
                    continue
                if n > 0 and n not in mentioned:
                    mentioned.append(n)
        return cls(
            thread_id=int(raw["thread_id"]),
            cursor_chat_id=str(raw["cursor_chat_id"]),
            workspace=str(raw["workspace"]),
            project_id=str(raw.get("project_id") or "none"),
            host=str(raw.get("host") or "lu-zero"),
            owner_id=int(raw["owner_id"]),
            parent_channel_id=int(raw["parent_channel_id"]),
            anchor_message_id=int(raw.get("anchor_message_id") or 0),
            status=str(raw.get("status") or "closed"),
            created_at=str(raw.get("created_at") or _utc_now()),
            closed_at=raw.get("closed_at"),
            thread_name=str(raw.get("thread_name") or ""),
            mentioned_issue_ids=mentioned or None,
        )


class SessionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, SessionRecord] = {}
        self.load()

    def load(self) -> None:
        if not self.path.is_file():
            self._sessions = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("sessions load failed: %s", e)
            self._sessions = {}
            return
        items = raw.get("sessions") if isinstance(raw, dict) else None
        out: dict[str, SessionRecord] = {}
        if isinstance(items, dict):
            for k, v in items.items():
                if not isinstance(v, dict):
                    continue
                try:
                    rec = SessionRecord.from_dict({**v, "thread_id": int(v.get("thread_id") or k)})
                    out[str(rec.thread_id)] = rec
                except (KeyError, TypeError, ValueError) as e:
                    logger.warning("skip bad session %s: %s", k, e)
        self._sessions = out

    def save(self) -> None:
        payload = {
            "updated_at": _utc_now(),
            "sessions": {k: asdict(v) for k, v in self._sessions.items()},
        }
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        fd, tmp = tempfile.mkstemp(
            dir=str(self.path.parent),
            prefix=".sessions.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fp:
                fp.write(text)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(tmp, self.path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def get(self, thread_id: int) -> SessionRecord | None:
        return self._sessions.get(str(thread_id))

    def get_active(self, thread_id: int) -> SessionRecord | None:
        rec = self.get(thread_id)
        if rec is None or rec.status != "active":
            return None
        return rec

    def upsert(self, rec: SessionRecord) -> None:
        self._sessions[str(rec.thread_id)] = rec
        self.save()

    def close(self, thread_id: int) -> SessionRecord | None:
        rec = self.get(thread_id)
        if rec is None:
            return None
        rec.status = "closed"
        rec.closed_at = _utc_now()
        self._sessions[str(thread_id)] = rec
        self.save()
        return rec

    def update_chat_id(self, thread_id: int, chat_id: str) -> SessionRecord | None:
        rec = self.get(thread_id)
        if rec is None:
            return None
        rec.cursor_chat_id = chat_id
        self._sessions[str(thread_id)] = rec
        self.save()
        return rec

    def add_mentioned_issues(
        self, thread_id: int, issue_ids: list[int]
    ) -> SessionRecord | None:
        """Merge Redmine issue ids into the session (deduped, first-seen order)."""
        rec = self.get(thread_id)
        if rec is None or not issue_ids:
            return rec
        current = list(rec.mentioned_issue_ids or [])
        changed = False
        for iid in issue_ids:
            n = int(iid)
            if n <= 0 or n in current:
                continue
            current.append(n)
            changed = True
        if not changed:
            return rec
        rec.mentioned_issue_ids = current
        self._sessions[str(thread_id)] = rec
        self.save()
        return rec