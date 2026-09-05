from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _env_truthy(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    return raw.strip().casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DiscordHome:
    """One Maestro Discord home (guild + primary channel)."""

    guild_id: int
    channel_id: int


@dataclass(frozen=True)
class Settings:
    token: str
    application_id: int
    public_key: str
    guild_id: int
    channel_id: int
    homes: tuple[DiscordHome, ...]
    allowed_user_id: int
    timezone: str
    cursor_agent_bin: str
    cursor_agent_timeout: float
    workspace: Path
    state_dir: Path
    prompts_dir: Path
    repo_root: Path
    catalog_dir: Path
    local_host: str
    nl_commands: bool
    message_content_intent: bool
    nl_router_timeout: float
    redmine_url: str = ""
    redmine_api_key: str = ""
    redmine_default_issue_id: int | None = None

    @property
    def guild_ids(self) -> tuple[int, ...]:
        seen: list[int] = []
        for home in self.homes:
            if home.guild_id > 0 and home.guild_id not in seen:
                seen.append(home.guild_id)
        return tuple(seen)

    @property
    def channel_ids(self) -> frozenset[int]:
        return frozenset(h.channel_id for h in self.homes if h.channel_id > 0)

    def is_maestro_channel(self, channel_id: int) -> bool:
        """True if channel is allowed for NL / ca_persist.

        Empty channel set = no channel gate (legacy channel_id=0).
        """
        allowed = self.channel_ids
        if not allowed:
            return True
        return channel_id in allowed


# Hardcoded sole operator (Luipy). Env/config must match.
LUIPY_DISCORD_ID = 488728568457854976


def _parse_home_pair(guild_raw: object, channel_raw: object) -> DiscordHome | None:
    try:
        guild_id = int(guild_raw or 0)
        channel_id = int(channel_raw or 0)
    except (TypeError, ValueError):
        return None
    if guild_id <= 0:
        return None
    return DiscordHome(guild_id=guild_id, channel_id=channel_id)


def _parse_homes_env(raw: str) -> list[DiscordHome]:
    """Parse DISCORD_HOMES=guild:channel,guild:channel."""
    out: list[DiscordHome] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            continue
        g_s, c_s = part.split(":", 1)
        home = _parse_home_pair(g_s.strip(), c_s.strip())
        if home is not None:
            out.append(home)
    return out


def _parse_homes_cfg(raw: object) -> list[DiscordHome]:
    if not isinstance(raw, list):
        return []
    out: list[DiscordHome] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        home = _parse_home_pair(item.get("guild_id"), item.get("channel_id"))
        if home is not None:
            out.append(home)
    return out


def _dedupe_homes(homes: list[DiscordHome]) -> tuple[DiscordHome, ...]:
    seen: set[tuple[int, int]] = set()
    out: list[DiscordHome] = []
    for home in homes:
        key = (home.guild_id, home.channel_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(home)
    return tuple(out)


def _load_homes(discord_cfg: dict) -> tuple[DiscordHome, ...]:
    """Resolve Maestro Discord homes (dual-home capable).

    Priority:
    1. DISCORD_HOMES env (guild:channel,...)
    2. config discord.homes[]
    3. Legacy single DISCORD_GUILD_ID + DISCORD_CHANNEL_ID / config guild_id + channel_id
    """
    env_homes = (os.environ.get("DISCORD_HOMES") or "").strip()
    if env_homes:
        parsed = _parse_homes_env(env_homes)
        if parsed:
            return _dedupe_homes(parsed)

    cfg_homes = _parse_homes_cfg(discord_cfg.get("homes"))
    if cfg_homes:
        return _dedupe_homes(cfg_homes)

    legacy = _parse_home_pair(
        os.environ.get("DISCORD_GUILD_ID") or discord_cfg.get("guild_id") or 0,
        os.environ.get("DISCORD_CHANNEL_ID") or discord_cfg.get("channel_id") or 0,
    )
    if legacy is None:
        return ()
    return (legacy,)


def load_settings(repo_root: Path | None = None) -> Settings:
    root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
    load_dotenv(root / ".env")

    cfg_path = Path(os.environ.get("MAESTRO_CONFIG", str(root / "config.json")))
    raw: dict = {}
    if cfg_path.is_file():
        loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = loaded

    discord_cfg = raw.get("discord") or {}
    ca_cfg = raw.get("cursor_agent") or {}
    host_cfg = raw.get("host") or {}
    nl_cfg = raw.get("nl") or {}
    default_timeout = float(ca_cfg.get("timeout_seconds") or 900)

    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DISCORD_TOKEN is required in .env")

    allowed = int(
        os.environ.get("MAESTRO_ALLOWED_USER_ID")
        or discord_cfg.get("allowed_user_id")
        or LUIPY_DISCORD_ID
    )
    if allowed != LUIPY_DISCORD_ID:
        raise RuntimeError(
            f"Maestro is hard-locked to Luipy ({LUIPY_DISCORD_ID}); got allowed_user_id={allowed}"
        )

    ws_raw = str(ca_cfg.get("workspace") or "/root")
    workspace = Path(ws_raw).expanduser().resolve()

    state_dir = Path(
        os.environ.get("MAESTRO_STATE_DIR", str(root / "data"))
    ).expanduser().resolve()
    state_dir.mkdir(parents=True, exist_ok=True)

    env_nl = _env_truthy("MAESTRO_NL_COMMANDS")
    nl_commands = (
        env_nl
        if env_nl is not None
        else bool(discord_cfg.get("nl_commands", nl_cfg.get("enabled", True)))
    )

    env_mci = _env_truthy("DISCORD_MESSAGE_CONTENT_INTENT")
    message_content_intent = (
        env_mci
        if env_mci is not None
        else bool(discord_cfg.get("message_content_intent", True))
    )

    nl_router_timeout = float(
        os.environ.get("MAESTRO_NL_ROUTER_TIMEOUT")
        or nl_cfg.get("router_timeout_seconds")
        or 180
    )

    from maestro.redmine_notes import MAESTRO_LOST_FOUND_ISSUE_ID

    redmine_url = (os.environ.get("REDMINE_URL") or "").strip().rstrip("/")
    redmine_api_key = (os.environ.get("REDMINE_API_KEY") or "").strip()
    raw_rm_default = (os.environ.get("REDMINE_DEFAULT_ISSUE_ID") or "").strip()
    redmine_default_issue_id: int | None = (
        int(raw_rm_default) if raw_rm_default.isdigit() else MAESTRO_LOST_FOUND_ISSUE_ID
    )

    homes = _load_homes(discord_cfg if isinstance(discord_cfg, dict) else {})
    primary = homes[0] if homes else DiscordHome(guild_id=0, channel_id=0)

    return Settings(
        token=token,
        application_id=int(
            os.environ.get("DISCORD_APPLICATION_ID")
            or discord_cfg.get("application_id")
            or 0
        ),
        public_key=(os.environ.get("DISCORD_PUBLIC_KEY") or "").strip(),
        guild_id=primary.guild_id,
        channel_id=primary.channel_id,
        homes=homes,
        allowed_user_id=LUIPY_DISCORD_ID,
        timezone=str(raw.get("timezone") or "UTC"),
        cursor_agent_bin=str(
            os.environ.get("CURSOR_AGENT_BIN")
            or ca_cfg.get("bin_path")
            or "/root/.local/bin/cursor-agent"
        ),
        cursor_agent_timeout=default_timeout,
        workspace=workspace,
        state_dir=state_dir,
        prompts_dir=root / "prompts",
        repo_root=root,
        catalog_dir=root / "catalog",
        local_host=str(host_cfg.get("name") or "lu-zero").strip().casefold() or "lu-zero",
        nl_commands=nl_commands,
        message_content_intent=message_content_intent,
        nl_router_timeout=nl_router_timeout,
        redmine_url=redmine_url,
        redmine_api_key=redmine_api_key,
        redmine_default_issue_id=redmine_default_issue_id,
    )
