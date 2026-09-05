"""Operator-driven maestro.service restarts (never auto from /ca agents)."""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

PENDING_NAME = "restart-pending"
SERVICE_NAME = "maestro.service"
DEFAULT_DELAY_SECONDS = 8
AGENT_ENV_FLAG = "MAESTRO_AGENT"


@dataclass(frozen=True)
class RestartDecision:
    action: str  # scheduled | blocked | pending | skipped | error | denied
    detail: str
    agent_count: int = 0
    busy_threads: int = 0


def pending_path(state_dir: Path) -> Path:
    return Path(state_dir) / PENDING_NAME


def is_restart_pending(state_dir: Path) -> bool:
    return pending_path(state_dir).is_file()


def is_maestro_agent_context() -> bool:
    """True when running under a Maestro-spawned cursor-agent (``MAESTRO_AGENT=1``)."""
    raw = (os.environ.get(AGENT_ENV_FLAG) or "").strip().casefold()
    return raw in {"1", "true", "yes", "on"}


def mark_restart_pending(state_dir: Path, *, reason: str = "") -> Path:
    path = pending_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = reason.strip() or "maestro restart requested"
    path.write_text(body + "\n", encoding="utf-8")
    logger.info("restart pending marked path=%s reason=%s", path, body)
    return path


def clear_restart_pending(state_dir: Path) -> bool:
    path = pending_path(state_dir)
    if not path.is_file():
        return False
    try:
        path.unlink()
    except OSError as e:
        logger.warning("could not clear restart-pending: %s", e)
        return False
    logger.info("restart pending cleared path=%s", path)
    return True


def list_cursor_agent_pids() -> list[int]:
    """PIDs of live Maestro-style cursor-agent /ca sessions (--print --workspace)."""
    return _list_cursor_agent_pids_proc()


def _list_cursor_agent_pids_proc() -> list[int]:
    found: list[int] = []
    proc = Path("/proc")
    if not proc.is_dir():
        return found
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if not raw:
            continue
        cmd = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace")
        if "cursor-agent" not in cmd and "/index.js" not in cmd:
            continue
        if "--print" not in cmd or "--workspace" not in cmd:
            continue
        if "worker-server" in cmd:
            continue
        found.append(int(entry.name))
    return found


def cursor_agent_count() -> int:
    return len(list_cursor_agent_pids())


def schedule_deferred_restart(*, delay_seconds: int = DEFAULT_DELAY_SECONDS) -> str:
    """Schedule restart outside the maestro cgroup via a transient systemd timer."""
    delay = max(1, int(delay_seconds))
    cmd = [
        "systemd-run",
        f"--on-active={delay}s",
        "--timer-property=AccuracySec=1s",
        "--property=Description=Maestro deferred restart (operator)",
        "/bin/systemctl",
        "restart",
        SERVICE_NAME,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"systemd-run deferred restart failed: {err}")
    note = (proc.stdout or proc.stderr or "").strip() or f"timer in {delay}s"
    logger.info("deferred restart scheduled delay=%ss note=%s", delay, note)
    return note


def operator_restart(
    *,
    state_dir: Path,
    force: bool = False,
    busy_threads: int = 0,
    delay_seconds: int = DEFAULT_DELAY_SECONDS,
) -> RestartDecision:
    """Slash `/restart_maestro`: schedule deferred restart, or block if busy unless force.

    Refuses when ``MAESTRO_AGENT=1`` (cursor-agent /ca must never restart the bot).
    """
    agents = cursor_agent_count()
    busy = max(0, int(busy_threads))
    if is_maestro_agent_context():
        logger.warning(
            "operator_restart denied: %s set (agents=%s busy=%s)",
            AGENT_ENV_FLAG,
            agents,
            busy,
        )
        mark_restart_pending(
            state_dir,
            reason=f"denied: {AGENT_ENV_FLAG}=1; operator must /restart_maestro",
        )
        return RestartDecision(
            action="denied",
            detail=(
                f"**Denied** · restart only via Discord `/restart_maestro` (operator).\n"
                f"This process has `{AGENT_ENV_FLAG}=1` (agent session). "
                f"Marked `{PENDING_NAME}`; tell Luipy to restart when ready."
            ),
            agent_count=agents,
            busy_threads=busy,
        )
    if not force and (agents > 0 or busy > 0):
        mark_restart_pending(
            state_dir,
            reason=f"blocked agents={agents} busy_threads={busy}; use force=True",
        )
        return RestartDecision(
            action="blocked",
            detail=(
                f"**Busy** · agents=`{agents}` · busy_threads=`{busy}`.\n"
                f"Marked `{PENDING_NAME}`. Re-run with **`force:True`** to restart anyway "
                f"(will **SIGKILL** in-flight `/ca` / persist threads), or wait until idle."
            ),
            agent_count=agents,
            busy_threads=busy,
        )
    try:
        note = schedule_deferred_restart(delay_seconds=delay_seconds)
        clear_restart_pending(state_dir)
        warn = ""
        if force and (agents > 0 or busy > 0):
            warn = (
                f"\n**force** · in-flight `/ca` and persist resumes will be **SIGKILL**'d "
                f"(agents=`{agents}`, busy_threads=`{busy}`)."
            )
        return RestartDecision(
            action="scheduled",
            detail=(
                f"**Restart scheduled** · ~{delay_seconds}s "
                f"(`systemd-run`).{warn}\n{note}"
            ),
            agent_count=agents,
            busy_threads=busy,
        )
    except Exception as e:
        mark_restart_pending(state_dir, reason=str(e))
        return RestartDecision(
            action="error",
            detail=f"**Restart failed** · `{type(e).__name__}: {e}` · marked `{PENDING_NAME}`.",
            agent_count=agents,
            busy_threads=busy,
        )


def agent_note_restart_needed(state_dir: Path, *, reason: str = "") -> RestartDecision:
    """Agents only: mark pending; never schedule. Operator must `/restart_maestro`."""
    mark_restart_pending(state_dir, reason=reason or "runtime code changed")
    return RestartDecision(
        action="pending",
        detail=(
            f"Marked `{PENDING_NAME}`. Do **not** restart from the agent. "
            f"Operator: run `/restart_maestro` when ready."
        ),
        agent_count=cursor_agent_count(),
    )


def main() -> None:
    """CLI: python -m maestro.restart_guard status|pending|operator [--force]

    ``operator`` is for a host shell (Luipy), never under ``MAESTRO_AGENT=1``.
    Prefer Discord ``/restart_maestro``.
    """
    import sys

    root = Path(__file__).resolve().parents[1]
    state = Path(os.environ.get("MAESTRO_STATE_DIR", root / "data"))
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    if cmd == "status":
        print(
            f"agents={cursor_agent_count()} pending={is_restart_pending(state)} "
            f"maestro_agent={is_maestro_agent_context()} "
            f"pids={list_cursor_agent_pids()}"
        )
        return
    if cmd == "pending":
        d = agent_note_restart_needed(state, reason="cli pending")
        print(f"{d.action}: {d.detail}")
        return
    if cmd == "operator":
        force = "--force" in args or "force" in args
        d = operator_restart(state_dir=state, force=force, busy_threads=0)
        print(f"{d.action}: {d.detail}")
        raise SystemExit(0 if d.action == "scheduled" else 1)
    if cmd in {"request", "drain"}:
        print(
            "obsolete: agents must not restart; use Discord /restart_maestro "
            "(host only: python -m maestro.restart_guard operator [--force])",
            file=sys.stderr,
        )
        raise SystemExit(2)
    print(
        "usage: python -m maestro.restart_guard status|pending|operator [--force]",
        file=sys.stderr,
    )
    raise SystemExit(2)


if __name__ == "__main__":
    main()
