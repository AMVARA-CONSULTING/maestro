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


# Primary operator (Luipy). Always kept on the allowlist; sole restart authority.
LUIPY_DISCORD_ID = 488728568457854976


# Default persist-thread parent when config/env omit thread_home_channel_id.
_DEFAULT_THREAD_HOME_CHANNEL_ID = 1545493623259398284


@dataclass(frozen=True)
class Settings:
    token: str
    application_id: int
    public_key: str
    guild_id: int
    channel_id: int
    homes: tuple[DiscordHome, ...]
    thread_home_channel_id: int
    allowed_user_ids: frozenset[int]
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
    def allowed_user_id(self) -> int:
        """Primary operator (Luipy). Kept for callers that expect a single id."""
        return LUIPY_DISCORD_ID

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

    def is_listen_guild(self, guild_id: int | None) -> bool:
        """True if NL / ca_persist may run in this guild.

        Empty guild set = no guild gate. DMs (guild_id None/0) are never allowed.
        Channel id is not checked: listen is guild-wide for allowlisted users.
        """
        if guild_id is None or int(guild_id) <= 0:
            return False
        allowed = self.guild_ids
        if not allowed:
            return True
        return int(guild_id) in allowed

    def is_maestro_channel(self, channel_id: int) -> bool:
        """True if channel is a configured home channel (legacy helper).

        Prefer is_listen_guild for NL / ca_persist gates and
        thread_home_channel_id_for(guild_id) for persist thread parents.
        Empty channel set = no channel gate (legacy channel_id=0).
        """
        allowed = self.channel_ids
        if not allowed:
            return True
        return channel_id in allowed

    def home_for_guild(self, guild_id: int | None) -> DiscordHome | None:
        """First configured home for this guild, or None."""
        if guild_id is None or int(guild_id) <= 0:
            return None
        gid = int(guild_id)
        for home in self.homes:
            if home.guild_id == gid and home.channel_id > 0:
                return home
        return None

    def thread_home_channel_id_for(self, guild_id: int | None) -> int:
        """Persist-thread parent channel for the source guild.

        Prefer that guild's home channel from homes[]. Fall back to the
        legacy global thread_home_channel_id only when the guild has no home.
        """
        home = self.home_for_guild(guild_id)
        if home is not None:
            return home.channel_id
        return int(self.thread_home_channel_id or 0)

    def is_allowed_user(self, user_id: int) -> bool:
        return int(user_id) in self.allowed_user_ids

    def is_owner(self, user_id: int) -> bool:
        """True for Luipy (restart + privileged ops)."""
        return int(user_id) == LUIPY_DISCORD_ID


def _load_thread_home_channel_id(
    discord_cfg: dict, homes: tuple[DiscordHome, ...]
) -> int:
    """Legacy fallback channel when a source guild has no homes[] entry.

    Persist threads normally open under the home channel of the guild where
    the operator spoke (see Settings.thread_home_channel_id_for).

    Priority for this fallback:
    1. DISCORD_THREAD_HOME_CHANNEL_ID env
    2. config discord.thread_home_channel_id
    3. Default preferred id if present in homes
    4. First home channel_id
    """
    env_raw = (os.environ.get("DISCORD_THREAD_HOME_CHANNEL_ID") or "").strip()
    if env_raw.isdigit():
        return int(env_raw)

    cfg_raw = discord_cfg.get("thread_home_channel_id")
    if cfg_raw is not None and str(cfg_raw).strip() != "":
        try:
            cid = int(cfg_raw)
        except (TypeError, ValueError):
            cid = 0
        if cid > 0:
            return cid

    home_ids = {h.channel_id for h in homes if h.channel_id > 0}
    if _DEFAULT_THREAD_HOME_CHANNEL_ID in home_ids:
        return _DEFAULT_THREAD_HOME_CHANNEL_ID
    if homes and homes[0].channel_id > 0:
        return homes[0].channel_id
    return _DEFAULT_THREAD_HOME_CHANNEL_ID


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


def _parse_user_id(raw: object) -> int | None:
    try:
        uid = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if uid <= 0:
        return None
    return uid


def _load_allowed_user_ids(discord_cfg: dict) -> frozenset[int]:
    """Resolve Discord allowlist (multi-operator).

    Priority merge (all sources unioned; Luipy always included):
    1. MAESTRO_ALLOWED_USER_IDS env (comma-separated snowflakes)
    2. config discord.allowed_user_ids[]
    3. Legacy MAESTRO_ALLOWED_USER_ID / discord.allowed_user_id
    """
    ids: set[int] = {LUIPY_DISCORD_ID}

    env_multi = (os.environ.get("MAESTRO_ALLOWED_USER_IDS") or "").strip()
    if env_multi:
        for part in env_multi.split(","):
            uid = _parse_user_id(part.strip())
            if uid is not None:
                ids.add(uid)

    cfg_multi = discord_cfg.get("allowed_user_ids")
    if isinstance(cfg_multi, list):
        for item in cfg_multi:
            uid = _parse_user_id(item)
            if uid is not None:
                ids.add(uid)

    env_one = (os.environ.get("MAESTRO_ALLOWED_USER_ID") or "").strip()
    if env_one:
        uid = _parse_user_id(env_one)
        if uid is not None:
            ids.add(uid)

    cfg_one = discord_cfg.get("allowed_user_id")
    if cfg_one is not None:
        uid = _parse_user_id(cfg_one)
        if uid is not None:
            ids.add(uid)

    return frozenset(ids)


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
    default_timeout = float(ca_cfg.get("timeout_seconds") or 1200)

    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DISCORD_TOKEN is required in .env")

    allowed_user_ids = _load_allowed_user_ids(
        discord_cfg if isinstance(discord_cfg, dict) else {}
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
    discord_cfg_dict = discord_cfg if isinstance(discord_cfg, dict) else {}
    thread_home_channel_id = _load_thread_home_channel_id(discord_cfg_dict, homes)

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
        thread_home_channel_id=thread_home_channel_id,
        allowed_user_ids=allowed_user_ids,
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
