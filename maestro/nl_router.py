"""Natural-language router: cursor-agent returns JSON; code validates and dispatches.

Fallback policy: if routing fails or is unclear, treat as ``ca_persist`` with the user text.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maestro.cursor_agent import call_cursor_agent_session, write_rendered_prompt

logger = logging.getLogger(__name__)

NL_ALLOWED_COMMANDS: frozenset[str] = frozenset(
    {"ping", "help", "ca", "ca_persist", "list_projects", "restart_maestro"}
)

_JSON_OBJ_RE = re.compile(r"\{[\s\S]*\}")


@dataclass(frozen=True)
class NLInvoke:
    command: str
    args: dict[str, Any]


@dataclass(frozen=True)
class NLParseError:
    detail: str


NLRouterOutcome = NLInvoke | NLParseError


def extract_json_text(raw: str) -> str:
    """Strip optional ```json fences and isolate the first JSON object."""
    t = raw.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    match = _JSON_OBJ_RE.search(t)
    if match:
        return match.group(0).strip()
    return t


def _as_nonempty_str(v: Any, field: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return v.strip()


def _validate_args(command: str, args: Any) -> dict[str, Any]:
    if not isinstance(args, dict):
        raise ValueError("args must be a JSON object")
    if command in ("ping", "help"):
        return {}
    if command == "restart_maestro":
        force = args.get("force", False)
        if isinstance(force, str):
            force = force.strip().casefold() in {"1", "true", "yes", "on"}
        return {"force": bool(force)}
    if command == "list_projects":
        host = args.get("host")
        if host is None or (isinstance(host, str) and not host.strip()):
            return {"host": "all"}
        return {"host": _as_nonempty_str(host, "host").casefold()}
    if command == "ca":
        return {"text": _as_nonempty_str(args.get("text"), "text")}
    if command == "ca_persist":
        return {"text": _as_nonempty_str(args.get("text"), "text")}
    raise ValueError(f"unknown command {command!r}")


def parse_router_json_text(text: str) -> NLRouterOutcome:
    try:
        obj = json.loads(extract_json_text(text))
    except json.JSONDecodeError as e:
        return NLParseError(f"invalid JSON: {e}")

    if not isinstance(obj, dict):
        return NLParseError("root JSON must be an object")

    kind = obj.get("kind")
    if kind != "invoke":
        return NLParseError("kind must be 'invoke'")

    cmd_raw = obj.get("command")
    if not isinstance(cmd_raw, str) or not cmd_raw.strip():
        return NLParseError("invoke.command missing")
    cmd = cmd_raw.strip().lower()
    if cmd not in NL_ALLOWED_COMMANDS:
        return NLParseError(f"command not allowed: {cmd!r}")

    args = obj.get("args", {})
    try:
        validated = _validate_args(cmd, args)
    except ValueError as e:
        return NLParseError(str(e))

    return NLInvoke(command=cmd, args=validated)


def strip_bot_mention(content: str, bot_user_id: int) -> str:
    text = content or ""
    text = re.sub(rf"<@!?{bot_user_id}>", " ", text)
    return " ".join(text.split()).strip()


def try_fast_route(user_text: str) -> NLInvoke | None:
    """Map obvious one-word help/ping/list without calling cursor."""
    t = user_text.strip().casefold()
    if t in {"ping", "pong", "/ping"}:
        return NLInvoke(command="ping", args={})
    if t in {"help", "/help", "ayuda", "ajuda"}:
        return NLInvoke(command="help", args={})
    if t in {
        "list_projects",
        "/list_projects",
        "list projects",
        "projects",
        "proyectos",
        "projectes",
        "lista proyectos",
        "llista projectes",
    }:
        return NLInvoke(command="list_projects", args={"host": "all"})

    if t in {
        "/restart_maestro",
        "restart_maestro",
        "restart maestro",
        "reinicia maestro",
        "reiniciar maestro",
    }:
        return NLInvoke(command="restart_maestro", args={"force": False})
    if t in {
        "/restart_maestro force",
        "restart_maestro force",
        "restart maestro force",
        "reinicia maestro force",
        "force restart maestro",
    }:
        return NLInvoke(command="restart_maestro", args={"force": True})

    # ca_persist: "persist …", "ca persist …", "/ca_persist …"
    for prefix in (
        "/ca_persist ",
        "ca_persist ",
        "ca persist ",
        "persist ",
        "persiste ",
        "sesión persistente ",
        "sesion persistente ",
    ):
        if t.startswith(prefix):
            rest = user_text.strip()[len(prefix) :].strip()
            if rest:
                return NLInvoke(command="ca_persist", args={"text": rest})
    if t in {"/ca_persist", "ca_persist", "ca persist", "persist"}:
        return NLInvoke(
            command="ca_persist",
            args={"text": "Continue in a persistent Maestro thread."},
        )
    return None


def fallback_ca(user_text: str) -> NLInvoke:
    """Default when NL is unclear / fails: open a persist session (prefer thread)."""
    text = user_text.strip() or "(empty message)"
    return NLInvoke(command="ca_persist", args={"text": text})


async def run_nl_router_cursor(
    *,
    bin_path: str,
    workspace: Path,
    prompts_dir: Path,
    state_dir: Path,
    user_text: str,
    via: str,
    timeout_seconds: float,
) -> NLRouterOutcome:
    """One cursor-agent call: model returns JSON; parsed and validated in code."""
    ut = user_text.strip() if user_text else "(empty message)"
    fast = try_fast_route(ut)
    if fast is not None:
        return fast

    template = prompts_dir / "nl-router.md"
    if not template.is_file():
        return NLParseError(f"router prompt missing: {template}")

    prompt_path = write_rendered_prompt(template)
    try:
        result = await call_cursor_agent_session(
            bin_path=bin_path,
            workspace=workspace,
            prompt_path=prompt_path,
            state_dir=state_dir,
            user_request=f"How should the bot respond?\n\nUser message (via={via}):\n{ut}",
            session_context=(
                "You are Maestro's NL router only. "
                "Do not edit files, run shell, or explore the repo. "
                "Output exactly one JSON object as specified in the system prompt."
            ),
            timeout_seconds=timeout_seconds,
        )
    finally:
        try:
            prompt_path.unlink(missing_ok=True)
        except OSError:
            pass

    raw = (result.stdout or "").strip()
    if not raw and result.stderr.strip():
        raw = result.stderr.strip()
    if not raw:
        return NLParseError("router returned empty output")
    return parse_router_json_text(raw)
