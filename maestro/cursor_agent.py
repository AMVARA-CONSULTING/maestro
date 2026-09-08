"""Run cursor-agent sessions for /ca."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from maestro.sanitize import sanitize_for_discord

logger = logging.getLogger(__name__)


class AgentCancelled(Exception):
    """Raised when the operator stops an in-flight cursor-agent run."""


@dataclass
class AgentProcSlot:
    """Mutable handle so Discord can kill one thread's cursor-agent only."""

    proc: asyncio.subprocess.Process | None = None
    cancelled: bool = False
    local_id: str = field(default="")

    def request_cancel(self) -> bool:
        """Mark cancelled and SIGKILL the process group if live. True if a proc was hit."""
        self.cancelled = True
        proc = self.proc
        if proc is None:
            return False
        kill_agent_process(proc)
        return True


def kill_agent_process(proc: asyncio.subprocess.Process) -> None:
    """Best-effort kill of cursor-agent (process group when started in a new session)."""
    if proc.returncode is not None:
        return
    pid = proc.pid
    if pid is None:
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except PermissionError:
        try:
            proc.kill()
        except ProcessLookupError:
            return
    except OSError:
        try:
            proc.kill()
        except ProcessLookupError:
            return


@dataclass(frozen=True)
class CursorAgentResult:
    session_id: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def discord_text(self, *, secret_literals: list[str] | None = None) -> str:
        body = (self.stdout or "").strip()
        if not body and self.stderr.strip():
            body = self.stderr.strip()
        if not body:
            body = f"cursor-agent finished with exit code {self.exit_code} and no output."
        if not self.ok:
            err = self.stderr.strip()
            if err and err not in body:
                body = f"{body}\n\n**stderr:**\n```\n{err[:1500]}\n```"
        return sanitize_for_discord(body, secret_literals=secret_literals)


def agent_subprocess_env() -> dict[str, str]:
    """Env for cursor-agent children: mark as agent so restart CLI refuses ``operator``."""
    env = os.environ.copy()
    env["MAESTRO_AGENT"] = "1"
    return env


def resolve_cursor_agent_bin(bin_path: str) -> str:
    env_bin = os.environ.get("CURSOR_AGENT_BIN", "").strip()
    if env_bin:
        p = Path(env_bin).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p.resolve())
        raise RuntimeError(f"CURSOR_AGENT_BIN is not executable: {p}")

    if bin_path.strip():
        p = Path(bin_path).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p.resolve())
        raise RuntimeError(f"cursor_agent.bin_path is not executable: {p}")

    found = shutil.which("cursor-agent") or shutil.which("agent")
    if found:
        return found
    local = Path.home() / ".local" / "bin" / "cursor-agent"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local.resolve())
    raise RuntimeError("cursor-agent not found on PATH")


def render_prompt_template(path: Path, **replacements: str) -> str:
    text = path.read_text(encoding="utf-8")
    for key, val in replacements.items():
        text = text.replace("{" + key + "}", val)
    return text.strip()


def write_rendered_prompt(template: Path, **variables: str) -> Path:
    rendered = render_prompt_template(template, **variables)
    fp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-{template.name}",
        delete=False,
        encoding="utf-8",
    )
    fp.write(rendered)
    fp.close()
    return Path(fp.name)


def build_agent_prompt(
    *,
    prompt_path: Path,
    user_request: str,
    session_context: str | None = None,
) -> str:
    base = prompt_path.read_text(encoding="utf-8").strip()
    parts = [base, "", "---", "", "### Operator request", "", user_request.strip()]
    if session_context and session_context.strip():
        parts.extend(["", "### Session context", "", session_context.strip()])
    return "\n".join(parts)


async def create_cursor_chat(*, bin_path: str, timeout_seconds: float = 60.0) -> str:
    """Create an empty Cursor chat and return its chatId."""
    binary = resolve_cursor_agent_bin(bin_path)
    proc = await asyncio.create_subprocess_exec(
        binary,
        "create-chat",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=agent_subprocess_env(),
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError("cursor-agent create-chat timed out") from None
    out = stdout_b.decode("utf-8", errors="replace").strip()
    err = stderr_b.decode("utf-8", errors="replace").strip()
    if proc.returncode not in (0, None) and not out:
        raise RuntimeError(f"create-chat failed (exit {proc.returncode}): {err or out}")
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError(f"create-chat returned empty id (stderr={err[:300]!r})")
    chat_id = lines[-1]
    logger.info("cursor-agent create-chat id=%s", chat_id)
    return chat_id


async def call_cursor_agent_session(
    *,
    bin_path: str,
    workspace: Path,
    prompt_path: Path | None,
    state_dir: Path,
    user_request: str,
    session_context: str | None = None,
    timeout_seconds: float = 1200.0,
    resume_chat_id: str | None = None,
    inject_prompt_template: bool = True,
    proc_slot: AgentProcSlot | None = None,
) -> CursorAgentResult:
    if not user_request.strip():
        raise ValueError("user_request must not be empty")
    if not workspace.is_dir():
        raise RuntimeError(f"Workspace is not a directory: {workspace}")

    binary = resolve_cursor_agent_bin(bin_path)
    local_id = uuid4().hex[:12]
    chat_label = resume_chat_id or local_id
    started = datetime.now(timezone.utc)
    if proc_slot is not None:
        proc_slot.local_id = local_id
        if proc_slot.cancelled:
            raise AgentCancelled(
                f"cursor-agent cancelled before start (local {local_id}, chat {chat_label})"
            )

    if inject_prompt_template:
        if prompt_path is None or not prompt_path.is_file():
            raise RuntimeError("prompt_path is required when inject_prompt_template=True")
        # For resume, still build from template on first persist turn;
        # follow-ups pass inject_prompt_template=False.
        full_prompt = build_agent_prompt(
            prompt_path=prompt_path,
            user_request=user_request,
            session_context=session_context,
        )
    else:
        parts = [user_request.strip()]
        if session_context and session_context.strip():
            parts.extend(["", "### Session context", "", session_context.strip()])
        full_prompt = "\n".join(parts)

    log_dir = state_dir / "cursor-agent"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    run_log = log_dir / f"{stamp}-{local_id}.log"
    run_log.write_text(
        "\n".join(
            [
                f"session_id={local_id}",
                f"resume_chat_id={resume_chat_id or ''}",
                f"started_utc={started.isoformat()}",
                f"workspace={workspace}",
                f"prompt={prompt_path}",
                f"binary={binary}",
                "",
                "=== prompt ===",
                full_prompt,
                "",
            ]
        ),
        encoding="utf-8",
    )

    cmd = [binary, "--yolo", "--print", "--trust"]
    if resume_chat_id:
        cmd.extend(["--resume", resume_chat_id])
    cmd.extend(["--workspace", str(workspace), full_prompt])
    logger.info(
        "cursor-agent local=%s resume=%s workspace=%s",
        local_id,
        resume_chat_id or "-",
        workspace,
    )

    if proc_slot is not None and proc_slot.cancelled:
        raise AgentCancelled(
            f"cursor-agent cancelled before start (local {local_id}, chat {chat_label})"
        )

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(workspace),
        env=agent_subprocess_env(),
        start_new_session=True,
    )
    if proc_slot is not None:
        proc_slot.proc = proc
        if proc_slot.cancelled:
            kill_agent_process(proc)
            proc_slot.proc = None
            try:
                await proc.communicate()
            except Exception:
                pass
            raise AgentCancelled(
                f"cursor-agent cancelled at start (local {local_id}, chat {chat_label})"
            )

    stdout_b = b""
    stderr_b = b""
    try:
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_seconds
            )
        except TimeoutError:
            kill_agent_process(proc)
            try:
                await proc.communicate()
            except Exception:
                pass
            raise TimeoutError(
                f"cursor-agent timed out after {timeout_seconds}s "
                f"(local {local_id}, chat {chat_label})"
            ) from None
        except asyncio.CancelledError:
            kill_agent_process(proc)
            try:
                await proc.communicate()
            except Exception:
                pass
            raise
    finally:
        if proc_slot is not None:
            proc_slot.proc = None

    if proc_slot is not None and proc_slot.cancelled:
        duration = (datetime.now(timezone.utc) - started).total_seconds()
        with run_log.open("a", encoding="utf-8") as fp:
            fp.write("cancelled=1\n")
            fp.write(f"duration_seconds={duration:.1f}\n")
        logger.info(
            "cursor-agent local=%s resume=%s cancelled duration=%.1fs",
            local_id,
            resume_chat_id or "-",
            duration,
        )
        raise AgentCancelled(
            f"cursor-agent stopped (local {local_id}, chat {chat_label})"
        )

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")
    exit_code = proc.returncode if proc.returncode is not None else -1

    with run_log.open("a", encoding="utf-8") as fp:
        fp.write(f"exit_code={exit_code}\n")
        fp.write(f"duration_seconds={duration:.1f}\n\n")
        fp.write("=== stdout ===\n")
        fp.write(stdout)
        fp.write("\n\n=== stderr ===\n")
        fp.write(stderr)
        fp.write("\n")

    logger.info(
        "cursor-agent local=%s resume=%s exit=%s duration=%.1fs",
        local_id,
        resume_chat_id or "-",
        exit_code,
        duration,
    )
    return CursorAgentResult(
        session_id=chat_label,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=duration,
    )
