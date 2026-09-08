from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands

from maestro import __version__
from maestro.attachments import (
    CLEANUP_INTERVAL_SECONDS,
    count_attached_files_in_prompt,
    list_allowed_attachments,
    merge_text_with_attachments,
    oneshot_attachments_dir,
    purge_expired_attachments,
    purge_thread_attachments,
    save_message_attachments,
    status_preview,
    thread_attachments_dir,
)
from maestro.catalog import (
    CatalogIndex,
    ProjectEntry,
    format_list_projects,
    load_catalog_index,
    read_context_markdown,
)
from maestro.cursor_agent import (
    AgentCancelled,
    AgentProcSlot,
    call_cursor_agent_session,
    create_cursor_chat,
    write_rendered_prompt,
)
from maestro.discord_interaction_errors import is_unknown_interaction_error
from maestro.nl_router import (
    NLInvoke,
    NLParseError,
    fallback_ca,
    run_nl_router_cursor,
    strip_bot_mention,
)
from maestro.outbound import (
    chunk_paths,
    collect_outbound_files,
    mark_outbound_sent,
    oneshot_outbound_dir,
    purge_thread_outbound,
    thread_outbound_dir,
)
from maestro.persist_views import ResumeFailView, StopCaView
from maestro.redmine_notes import (
    RedmineConfig,
    cursor_session_stamp,
    extract_issue_ids,
    post_session_close_notes,
    resolve_catalog_doc_issue_id,
    resolve_close_note_issue_id,
)
from maestro.restart_guard import (
    is_restart_pending,
    operator_restart,
)
from maestro.sanitize import chunk_discord, sanitize_for_discord
from maestro.sessions import SessionRecord, SessionStore
from maestro.settings import Settings
from maestro.status_heartbeat import StatusHeartbeat
from maestro.thread_queue import ThreadQueueManager

logger = logging.getLogger("maestro")
chat_log = logging.getLogger("maestro.chat")

_HELP = f"""**Maestro v{__version__}** — MVP · **allowlist** (restart: Luipy only)

**What** — Discord ultra-orchestrator. Runs **cursor-agent** on lu-zero against a multi-host catalog (remote work via SSH). Persist threads keep one Cursor chat.

**Quick start**
1. `/list_projects` — hosts & projects
2. `/ca_persist` `task` — open a work thread in **that guild's** Maestro home channel (or **@Maestro** / reply from any listen guild channel)
3. Keep chatting **inside** the thread — same session (queue if busy; **Stop** on busy status)
4. `/thread_end` — summary → parent channel, then thread deleted (`clean` skips Redmine)

**Commands**
• `/help` — This guide · `/ping` — latency
• `/list_projects` `[host]` — catalog (`all` or omit = every host)
• `/ca` `text` — one-shot (no thread)
• `/ca_persist` `text` — thread + resume
• `/stop_ca` — **inside** thread: abort that resume + clear **its** queue
• `/thread_end` `[clean]` — **inside** thread: close session (`clean` = no Redmine close note)
• `/restart_maestro` `[force]` — restart bot (**Luipy only**; `force` kills busy `/ca`)

**Also**
• Attachments (images, PDF, logs/text) → cached for the agent; purge on `/thread_end` (TTL 72h)
• Outbound files: agent saves under `data/outbound/…` (images, JSON, HTML, PDF, logs, …); Maestro **attaches** them after the turn
• Redmine (MaestroBot): **one** close note — project hub → else one primary ticket → else #8077 (skip with `/thread_end clean:True`)
• **No secrets** on Discord · never wipe end-user data without scoped OK from Luipy
"""

_DENY = "Maestro only responds to **allowlisted** operators."
_DENY_RESTART = "`/restart_maestro` is **Luipy only**."
_CA_PROMPT = "ca-lu-zero.md"
_DISCORD_MSG_MAX = 2000
_NL_STATUS_ROUTING = "Routing your message…"
_HEARTBEAT_INTERVAL = 8.0
_CONTEXT_INJECT_MAX = 6000
_QUEUE_MAX = 5
_CLOSE_SUMMARY_TIMEOUT = 120.0
_CLOSE_SUMMARY_PROMPT = """Summarize this Maestro Discord persist session for the operator.

Write 5-10 short bullets of what was done or decided. Use English only (ASD-STE100 style: short sentences). The same text is posted to Discord and embedded in the MaestroBot Redmine close note, which must never mix languages. No secrets, tokens, passwords, or credential-bearing paths. Plain Discord markdown only. No preamble before the bullets."""


async def _message_addresses_bot(
    client: discord.Client, message: discord.Message
) -> tuple[bool, str]:
    me = client.user
    if me is None:
        return False, ""
    if me in message.mentions or me.id in message.raw_mentions:
        return True, "mention"
    ref = message.reference
    if ref is None or ref.message_id is None:
        return False, ""
    resolved = ref.resolved
    if resolved is None:
        try:
            resolved = await message.channel.fetch_message(ref.message_id)
        except (discord.NotFound, discord.HTTPException):
            return False, ""
    try:
        author = resolved.author
    except AttributeError:
        return False, ""
    if author.id == me.id:
        return True, "reply_to_bot"
    return False, ""


async def _nl_edit_or_reply(
    message: discord.Message,
    status_msg: discord.Message | None,
    content: str,
) -> discord.Message | None:
    text = content[:_DISCORD_MSG_MAX]
    if status_msg is not None:
        try:
            await status_msg.edit(content=text)
            return status_msg
        except discord.HTTPException:
            pass
    try:
        return await message.reply(text, mention_author=False)
    except discord.HTTPException:
        return None


async def _reply_chunked(
    message: discord.Message,
    text: str,
    *,
    edit_first: discord.Message | None = None,
) -> None:
    parts = chunk_discord(text)
    first, *rest = parts
    await _nl_edit_or_reply(message, edit_first, first)
    for part in rest:
        try:
            await message.channel.send(part[:_DISCORD_MSG_MAX])
        except discord.HTTPException as e:
            logger.warning("NL chunk send failed: %s", e)
            break


def _slug_from_request(text: str, *, max_words: int = 6, max_len: int = 48) -> str:
    """Short human label from the first persist turn when no catalog project is bound."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""
    for prefix in (
        "/ca_persist ",
        "/ca ",
        "ca_persist ",
        "ca persist ",
        "persist ",
    ):
        if cleaned.casefold().startswith(prefix):
            cleaned = cleaned[len(prefix) :].lstrip()
            break
    if not cleaned:
        return ""
    words = cleaned.split(" ")
    if len(words) > max_words:
        cleaned = " ".join(words[:max_words])
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[: max_len + 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    else:
        cut = cleaned[:max_len]
    return cut.rstrip(" ·.,;:!-") or cleaned[:max_len]


def _thread_label(project_id: str, text: str = "") -> str:
    if project_id and project_id.casefold() != "none":
        return project_id
    return _slug_from_request(text) or "general"


def _thread_name(
    project_id: str,
    host: str,
    *,
    cursor_chat_id: str,
    text: str = "",
    label: str | None = None,
) -> str:
    """Discord thread title: ``label · host · <cursor-stamp>``.

    Third field matches Redmine collapse stamps: first 8 hex chars of the
    Cursor chat UUID (not Discord HHMM).
    """
    stamp = cursor_session_stamp(cursor_chat_id)
    lab = (label or "").strip() or _thread_label(project_id, text)
    return f"{lab} · {host} · {stamp}"[:100]


class MaestroBot(discord.Client):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        intents.dm_messages = True
        if settings.message_content_intent:
            intents.message_content = True
        super().__init__(intents=intents)
        self.settings = settings
        self.catalog: CatalogIndex = load_catalog_index(
            settings.catalog_dir, settings.local_host
        )
        self.sessions = SessionStore(settings.state_dir / "sessions.json")
        self.thread_queues = ThreadQueueManager(max_queue=_QUEUE_MAX)
        self.thread_queues.set_handler(self._handle_queued_thread_turn)
        self._last_thread_text: dict[int, str] = {}
        self._thread_slots: dict[int, AgentProcSlot] = {}
        self._attachment_cleanup_task: asyncio.Task[None] | None = None
        self.tree = app_commands.CommandTree(self)
        self._register_commands()

    def _is_allowed(self, user_id: int) -> bool:
        return self.settings.is_allowed_user(user_id)

    def _is_luipy(self, user_id: int) -> bool:
        return self.settings.is_owner(user_id)

    async def _prepare_message_text(
        self,
        message: discord.Message,
        text: str,
        *,
        dest: Path,
        empty_fallback: str = "Review the attached file(s).",
    ) -> tuple[str, list[str], int]:
        """Download allowed attachments and merge paths into agent text.

        Returns (enriched_text, user-facing errors, file_count_saved).
        """
        files = list_allowed_attachments(message)
        if not files:
            return text.strip(), [], 0
        result = await save_message_attachments(message, dest)
        errors = list(result.errors)
        body = text.strip()
        if result.saved and not body:
            body = empty_fallback
        enriched = merge_text_with_attachments(body, result.saved)
        return enriched, errors, len(result.saved)

    def _secret_literals(self) -> list[str]:
        out = [self.settings.token]
        if self.settings.redmine_api_key:
            out.append(self.settings.redmine_api_key)
        return out

    def _redmine_config(self) -> RedmineConfig:
        return RedmineConfig(
            url=self.settings.redmine_url,
            api_key=self.settings.redmine_api_key,
            default_issue_id=self.settings.redmine_default_issue_id,
        )

    def _track_mentioned_issues(self, thread_id: int, *texts: str) -> None:
        ids = extract_issue_ids(*texts)
        if not ids:
            return
        self.sessions.add_mentioned_issues(thread_id, ids)

    def _close_note_issue_ids(self, rec: SessionRecord) -> list[int]:
        """Exactly one close-note target: hub → one primary mention → L&F."""
        project = self.catalog.get(rec.project_id)
        target = resolve_close_note_issue_id(
            project_id=rec.project_id,
            redmine_doc_issue_id=(
                project.redmine_doc_issue_id if project is not None else None
            ),
            mentioned_issue_ids=rec.mentioned_issue_ids,
            default_issue_id=self.settings.redmine_default_issue_id,
        )
        return [target] if target is not None else []

    def _resolve_project(self, text: str) -> ProjectEntry | None:
        return self.catalog.resolve_from_text(text)

    def _ca_session_context(
        self,
        *,
        user: discord.abc.User,
        source: str,
        project: ProjectEntry | None,
        persist: bool = False,
        outbound_dir: Path | None = None,
    ) -> str:
        parts = [
            f"Discord user: {user} (id={user.id}).",
            f"Source: {source}. Maestro host: {self.settings.local_host}.",
            "cursor-agent always runs on the Maestro host. "
            "For remote catalog hosts, use SSH (never assume remote paths exist locally).",
            "Minecraft on lu-zero is backup/off and out of catalog; live MC is on lu-one.",
            "Reply language: match the operator request language "
            "(or the language they ask for); if unclear, Catalan.",
            "Never post secrets to Discord (tokens, keys, passwords) "
            "even if the operator asks or tries a workaround.",
            "Never delete or wipe end-user data (e.g. OpenCloud user files/images, "
            "mailboxes, tenant media). Refuse destructive cleanups unless Luipy "
            "gives an explicit scoped confirmation.",
            "Maestro CONTEXT.md is a minimum map; prefer AGENTS.md / .cursor "
            "on the project host for detailed policy.",
        ]
        if outbound_dir is not None:
            parts.append(
                "Outbound Discord files: save under "
                f"`{outbound_dir}` (create the directory if needed). "
                "Allowed: images (PNG/JPEG/GIF/WebP), JSON, HTML, TXT/MD/CSV/LOG, "
                "PDF, SVG, XML/YAML, .red, ZIP, WebM. "
                "Maestro attaches those files to Discord after this turn. "
                "Do not rely on markdown image links for Discord delivery. "
                "Never put secrets or credential files in outbound."
            )
        if persist:
            parts.append(
                "This is a **persisted** Discord thread session "
                "(Cursor chat resumed across messages)."
            )
        if project is not None:
            ctx = read_context_markdown(self.settings.repo_root, project)
            if len(ctx) > _CONTEXT_INJECT_MAX:
                ctx = ctx[:_CONTEXT_INJECT_MAX] + "\n\n…(CONTEXT.md truncated)…"
            local = project.is_local_to(self.settings.local_host)
            parts.extend(
                [
                    f"Bound catalog project: `{project.id}` ({project.kind}).",
                    f"Catalog host: `{project.host}` "
                    f"({'local' if local else f'remote via ssh {project.ssh_alias}'}).",
                    f"Project path on that host: `{project.path}`.",
                    f"Summary: {project.summary}",
                ]
            )
            if project.autoagents is not None:
                aa = project.autoagents
                aa_dir = aa.dir_path(project.path)
                aa_loop = aa.loop_path(project.path)
                parts.extend(
                    [
                        f"Autoagents: **yes** · dir `{aa_dir}` · loop `{aa_loop}`.",
                        "When asked for a new autoagents task: write the task file under "
                        f"`{aa_dir}/tasks/` following that install's TASKS-README "
                        "(usually NEW-/FEAT-); do **not** wait for confirmation unless "
                        "the operator asked to discuss first. Then verify the loop process "
                        "is running (pgrep/log); start or restart it if needed; notify Luipy.",
                        "Reference: `/root/Repos/autoagents` (base template; each install is adapted).",
                    ]
                )
            if project.redmine_doc_issue_id is not None:
                rid = project.redmine_doc_issue_id
                parts.extend(
                    [
                        f"Catalog Redmine doc ticket: **#{rid}** "
                        f"(https://redmine.amvara.de/issues/{rid}).",
                        "When this session has material work on a specific Redmine ticket, "
                        "post *one* MaestroBot mid-session note to that work ticket "
                        "(ASD-STE100 English + Textile collapse; never Markdown). "
                        "On `/thread_end`, MaestroBot posts *one* automatic close note to "
                        f"the catalog hub #{rid} only (not to every mentioned id). "
                        "Collapse title stamp = first 8 hex chars of the Cursor chat id "
                        "(not Discord HHMM, not the issue number). "
                        "Skill: `/root/bots/maestro/.cursor/skills/redmine-notes/SKILL.md`.",
                    ]
                )
            else:
                fallback = resolve_catalog_doc_issue_id(
                    project_id=project.id, redmine_doc_issue_id=None
                )
                if fallback is not None:
                    parts.extend(
                        [
                            f"No per-project Redmine doc ticket; KM0 close-note hub "
                            f"**#{fallback}** (https://redmine.amvara.de/issues/{fallback}). "
                            "Mid-session: one Textile note to the primary work ticket when "
                            "material. `/thread_end`: one close note to that hub (or one "
                            "primary mention if no hub applies). Never Markdown in notes. "
                            "Skill: `/root/bots/maestro/.cursor/skills/redmine-notes/SKILL.md`.",
                        ]
                    )
                else:
                    parts.extend(
                        [
                            "No catalog Redmine hub for this project. `/thread_end` posts "
                            "one close note to the primary mentioned work ticket, else "
                            "Lost & Found #8077. Notes: ASD-STE100 English + Textile only. "
                            "Skill: `/root/bots/maestro/.cursor/skills/redmine-notes/SKILL.md`.",
                        ]
                    )
            if not local:
                parts.append(
                    f"Operate with `ssh {project.ssh_alias} '…'` targeting `{project.path}`. "
                    "Do not edit lu-zero backup Minecraft trees for live WN work."
                )
            parts.extend(["", "### CONTEXT.md", ctx])
        else:
            parts.append(
                "Bound catalog project: none "
                f"(general {self.settings.local_host} workspace)."
            )
        return "\n".join(parts)

    def _resolve_workspace(self, text: str) -> tuple[Path, str, ProjectEntry | None]:
        """Return (agent_cwd_on_maestro_host, project_id, project)."""
        project = self._resolve_project(text)
        project_id = "none"
        # Agent always executes on Maestro's host.
        workspace = self.settings.workspace
        if project is not None:
            project_id = project.id
            if project.is_local_to(self.settings.local_host):
                if not project.path.is_dir():
                    raise FileNotFoundError(
                        f"Catalog `{project.id}` path missing on disk: `{project.path}`"
                    )
                workspace = project.path.resolve()
            # Remote: keep agent cwd on Maestro host (default workspace /root).
        return workspace, project_id, project

    def _register_commands(self) -> None:
        bot = self

        @self.tree.command(name="help", description="Short Maestro guide + commands")
        async def help_cmd(interaction: discord.Interaction) -> None:
            if not bot._is_allowed(interaction.user.id):
                await interaction.response.send_message(_DENY, ephemeral=True)
                return
            await interaction.response.send_message(
                (_HELP + bot._restart_pending_note())[:_DISCORD_MSG_MAX],
                ephemeral=True,
            )

        @self.tree.command(name="ping", description="Connectivity check")
        async def ping_cmd(interaction: discord.Interaction) -> None:
            if not bot._is_allowed(interaction.user.id):
                await interaction.response.send_message(_DENY, ephemeral=True)
                return
            latency_ms = round(bot.latency * 1000)
            note = bot._restart_pending_note().replace("\n\n", " · ").strip()
            extra = f" · {note}" if note else ""
            await interaction.response.send_message(
                f"Pong · `{latency_ms} ms`{extra}", ephemeral=False
            )

        host_choices = [
            app_commands.Choice(name="all", value="all"),
            *[
                app_commands.Choice(name=h, value=h)
                for h in bot.catalog.list_hosts()
            ],
        ]

        @self.tree.command(
            name="list_projects",
            description="List catalogued Maestro projects (omit host = all)",
        )
        @app_commands.describe(host="Host filter (omit = list all hosts)")
        @app_commands.choices(host=host_choices)
        async def list_projects_cmd(
            interaction: discord.Interaction,
            host: app_commands.Choice[str] | None = None,
        ) -> None:
            if not bot._is_allowed(interaction.user.id):
                await interaction.response.send_message(_DENY, ephemeral=True)
                return
            filt = host.value if host is not None else "all"
            body = format_list_projects(bot.catalog, host_filter=filt)
            await interaction.response.send_message(body[:_DISCORD_MSG_MAX], ephemeral=False)

        @self.tree.command(
            name="ca",
            description="One-shot cursor-agent (no persistent thread)",
        )
        @app_commands.describe(text="Prompt / task for cursor-agent")
        async def ca_cmd(interaction: discord.Interaction, text: str) -> None:
            await bot._run_ca_slash(interaction, text=text)

        @self.tree.command(
            name="ca_persist",
            description="Start a persistent Cursor session in a Discord thread",
        )
        @app_commands.describe(text="First prompt / task for the persisted session")
        async def ca_persist_cmd(interaction: discord.Interaction, text: str) -> None:
            await bot._run_ca_persist_slash(interaction, text=text)

        @self.tree.command(
            name="stop_ca",
            description="Stop this persist thread's running resume (queue cleared; thread kept)",
        )
        async def stop_ca_cmd(interaction: discord.Interaction) -> None:
            await bot._run_stop_ca(interaction)

        @self.tree.command(
            name="thread_end",
            description="Destroy this Maestro persist thread (use inside the thread)",
        )
        @app_commands.describe(
            clean="If true, close without posting a Redmine close note",
        )
        async def thread_end_cmd(
            interaction: discord.Interaction,
            clean: bool = False,
        ) -> None:
            await bot._run_thread_end(interaction, clean=clean)

        @self.tree.command(
            name="restart_maestro",
            description="Restart Maestro (deferred; use force if /ca jobs are busy)",
        )
        @app_commands.describe(
            force="If true, restart even when other /ca sessions are running (kills them)",
        )
        async def restart_maestro_cmd(
            interaction: discord.Interaction,
            force: bool = False,
        ) -> None:
            await bot._run_restart_maestro(interaction, force=force)

    async def _edit_interaction(self, interaction: discord.Interaction, content: str) -> None:
        text = content[:_DISCORD_MSG_MAX]
        try:
            await interaction.edit_original_response(content=text)
            return
        except discord.HTTPException as e:
            if is_unknown_interaction_error(e):
                logger.warning("edit_original failed (unknown interaction): %s", e)
            else:
                logger.warning("edit_original_response failed: %s", e)
        try:
            await interaction.followup.send(text)
        except discord.HTTPException as e:
            logger.warning("could not deliver reply: %s", e)

    async def _run_ca_core(
        self,
        *,
        text: str,
        user: discord.abc.User,
        source: str,
        set_status: Callable[[str], Awaitable[None]],
        send_extra: Callable[[str], Awaitable[None]],
        channel: discord.abc.Messageable | None = None,
        resume_chat_id: str | None = None,
        inject_prompt_template: bool = True,
        persist: bool = False,
        workspace: Path | None = None,
        project: ProjectEntry | None = None,
        project_id: str | None = None,
        proc_slot: AgentProcSlot | None = None,
        outbound_dir: Path | None = None,
    ) -> None:
        task = text.strip()
        if not task:
            await set_status("Provide a non-empty prompt / task.")
            return

        if workspace is None or project_id is None:
            try:
                workspace, project_id, project = self._resolve_workspace(task)
            except FileNotFoundError as e:
                await set_status(str(e))
                return

        assert workspace is not None and project_id is not None

        logger.info(
            "/ca source=%s user=%s project=%s persist=%s resume=%s text_len=%s",
            source,
            user.id,
            project_id,
            persist,
            resume_chat_id or "-",
            len(task),
        )
        bound = f" · `{project_id}`" if project_id != "none" else ""
        cat_host = project.host if project is not None else self.settings.local_host
        mode = "persist" if persist or resume_chat_id else "ca"
        headline = (
            f"**Maestro /{mode}** · `{cat_host}`{bound} · cursor-agent"
            f" (runner `{self.settings.local_host}`)"
        )
        beat = StatusHeartbeat(
            set_status,
            headline=headline,
            detail="Starting",
            interval_seconds=_HEARTBEAT_INTERVAL,
            channel=channel,
        )
        await beat.start()

        template = self.settings.prompts_dir / _CA_PROMPT
        prompt_path: Path | None = None
        if inject_prompt_template:
            if not template.is_file():
                await beat.stop()
                await set_status(f"Prompt template missing: `{template}`")
                return
            project_path = str(project.path) if project is not None else str(workspace)
            prompt_path = write_rendered_prompt(
                template,
                host_name=cat_host,
                maestro_host=self.settings.local_host,
                workspace=str(workspace),
                project_id=project_id,
                project_path=project_path,
                ssh_alias=project.ssh_alias if project is not None else self.settings.local_host,
                is_remote="false" if project is None or project.is_local_to(self.settings.local_host) else "true",
            )

        result = None
        try:
            beat.update_detail(
                f"Running cursor-agent ({project_id})"
                if project_id != "none"
                else "Running cursor-agent"
            )
            try:
                result = await call_cursor_agent_session(
                    bin_path=self.settings.cursor_agent_bin,
                    workspace=workspace,
                    prompt_path=prompt_path,
                    state_dir=self.settings.state_dir,
                    user_request=task,
                    session_context=self._ca_session_context(
                        user=user,
                        source=source,
                        project=project,
                        persist=persist or bool(resume_chat_id),
                        outbound_dir=outbound_dir,
                    ),
                    timeout_seconds=self.settings.cursor_agent_timeout,
                    resume_chat_id=resume_chat_id,
                    inject_prompt_template=inject_prompt_template,
                    proc_slot=proc_slot,
                )
            except AgentCancelled as e:
                await beat.stop()
                await set_status(
                    f"**Stopped** · this thread only · ready for a new prompt.\n`{e}`"
                )
                if persist or resume_chat_id:
                    raise
                return
            except TimeoutError as e:
                await beat.stop()
                await set_status(f"**Timed out**\n{e}")
                if persist or resume_chat_id:
                    raise
                return
            except Exception as e:
                logger.exception("/ca failed source=%s", source)
                await beat.stop()
                await set_status(f"**Error**\n{type(e).__name__}: {e}")
                if persist or resume_chat_id:
                    raise
                return
        finally:
            await beat.stop()
            if prompt_path is not None:
                try:
                    prompt_path.unlink(missing_ok=True)
                except OSError:
                    pass

        if result is None:
            return

        # Do not scrape agent replies for close-note issue ids (caused hub/exam fan-out).
        # Operator messages are tracked separately when they arrive.

        header = (
            f"**Maestro /{mode}** · `{self.settings.local_host}` · `{project_id}` · "
            f"cursor-agent · chat `{result.session_id}` · exit {result.exit_code}\n\n"
        )
        body = header + result.discord_text(secret_literals=self._secret_literals())
        parts = chunk_discord(body)
        await set_status(parts[0])
        for part in parts[1:]:
            await send_extra(part[:_DISCORD_MSG_MAX])
        if channel is not None:
            await self._send_outbound_files(
                channel,
                outbound_dir=outbound_dir,
                agent_text=result.stdout or "",
            )
        logger.info(
            "/ca done source=%s project=%s ok=%s chat=%s",
            source,
            project_id,
            result.ok,
            result.session_id,
        )

    async def _send_outbound_files(
        self,
        channel: discord.abc.Messageable,
        *,
        outbound_dir: Path | None,
        agent_text: str = "",
    ) -> int:
        """Attach agent-produced outbound files to Discord. Returns count sent."""
        paths = collect_outbound_files(
            state_dir=self.settings.state_dir,
            scope_dir=outbound_dir,
            agent_text=agent_text,
        )
        if not paths:
            return 0
        sent = 0
        for batch in chunk_paths(paths):
            files: list[discord.File] = []
            opened: list[Path] = []
            try:
                for p in batch:
                    files.append(discord.File(p, filename=p.name))
                    opened.append(p)
                label = (
                    f"**Attachment** · `{opened[0].name}`"
                    if len(opened) == 1
                    else f"**Attachments** · {len(opened)} file(s)"
                )
                await channel.send(label, files=files)
                mark_outbound_sent(opened)
                sent += len(opened)
            except discord.HTTPException as e:
                logger.warning("outbound file send failed: %s", e)
                try:
                    await channel.send(
                        "**Attachment failed** · could not upload file(s) "
                        "(check bot **Attach Files** permission / size limits)."
                    )
                except discord.HTTPException:
                    pass
                break
            except OSError as e:
                logger.warning("outbound file open failed: %s", e)
                break
        if sent:
            logger.info("outbound files sent count=%s dir=%s", sent, outbound_dir)
        return sent

    async def _run_restart_maestro(
        self,
        interaction: discord.Interaction,
        *,
        force: bool = False,
    ) -> None:
        if not self._is_luipy(interaction.user.id):
            await interaction.response.send_message(_DENY_RESTART, ephemeral=True)
            return
        try:
            await interaction.response.defer(ephemeral=False, thinking=False)
        except discord.HTTPException as e:
            if is_unknown_interaction_error(e):
                logger.warning("/restart_maestro defer failed: %s", e)
                return
            raise
        decision = operator_restart(
            state_dir=self.settings.state_dir,
            force=force,
            busy_threads=self.thread_queues.busy_count(),
        )
        logger.info(
            "restart_maestro force=%s action=%s agents=%s busy=%s",
            force,
            decision.action,
            decision.agent_count,
            decision.busy_threads,
        )
        await self._edit_interaction(interaction, decision.detail)

    def _restart_pending_note(self) -> str:
        if is_restart_pending(self.settings.state_dir):
            return "\n\n_Note: `restart-pending` is set — runtime changes wait for `/restart_maestro`._"
        return ""

    async def _run_ca_slash(self, interaction: discord.Interaction, *, text: str) -> None:
        if not self._is_allowed(interaction.user.id):
            await interaction.response.send_message(_DENY, ephemeral=True)
            return

        if not text.strip():
            await interaction.response.send_message(
                "Provide a **text** argument with your prompt / task.",
                ephemeral=True,
            )
            return

        try:
            await interaction.response.defer(ephemeral=False, thinking=True)
        except discord.HTTPException as e:
            if is_unknown_interaction_error(e):
                logger.warning("/ca defer failed (unknown interaction): %s", e)
                return
            raise

        async def set_status(content: str) -> None:
            await self._edit_interaction(interaction, content)

        async def send_extra(content: str) -> None:
            try:
                await interaction.followup.send(content[:_DISCORD_MSG_MAX])
            except discord.HTTPException as e:
                logger.warning("followup chunk failed: %s", e)

        await self._run_ca_core(
            text=text,
            user=interaction.user,
            source="slash",
            set_status=set_status,
            send_extra=send_extra,
            channel=interaction.channel,
            outbound_dir=oneshot_outbound_dir(
                self.settings.state_dir, interaction.id
            ),
        )

    async def _run_ca_persist_slash(
        self, interaction: discord.Interaction, *, text: str
    ) -> None:
        if not self._is_allowed(interaction.user.id):
            await interaction.response.send_message(_DENY, ephemeral=True)
            return
        if not text.strip():
            await interaction.response.send_message(
                "Provide a **text** argument for the first persist turn.",
                ephemeral=True,
            )
            return
        guild_id = interaction.guild_id
        if not self.settings.is_listen_guild(guild_id):
            await interaction.response.send_message(
                "Use `/ca_persist` in a Maestro guild channel (not DM).",
                ephemeral=True,
            )
            return

        try:
            await interaction.response.defer(ephemeral=False, thinking=True)
        except discord.HTTPException as e:
            if is_unknown_interaction_error(e):
                return
            raise

        await self._edit_interaction(interaction, "Creating Cursor chat + Discord thread…")
        try:
            await self._start_persist_session(
                user=interaction.user,
                text=text.strip(),
                notify_message=await interaction.original_response(),
                source="slash-persist",
                guild_id=guild_id,
            )
        except Exception as e:
            logger.exception("ca_persist failed")
            await self._edit_interaction(
                interaction, f"**ca_persist failed**\n{type(e).__name__}: {e}"
            )

    async def _post_original_msg(self, thread: discord.Thread, text: str) -> None:
        """Echo the operator's first prompt into the new persist thread."""
        clean = sanitize_for_discord((text or "").strip())
        if not clean:
            return
        body = f"**Original msg:**\n{clean}"
        for part in chunk_discord(body, limit=_DISCORD_MSG_MAX):
            try:
                await thread.send(part)
            except discord.HTTPException as e:
                logger.warning("could not post Original msg in thread: %s", e)
                return

    async def _get_thread_home_channel(
        self, guild_id: int | None
    ) -> discord.TextChannel:
        """Resolve the persist-thread parent for the source guild's home channel."""
        cid = int(self.settings.thread_home_channel_id_for(guild_id) or 0)
        if cid <= 0:
            raise RuntimeError(
                "No Maestro home channel configured for this guild "
                "(discord.homes / thread_home_channel_id)"
            )
        channel = self.get_channel(cid)
        if channel is None:
            try:
                channel = await self.fetch_channel(cid)
            except discord.HTTPException as e:
                raise RuntimeError(
                    f"Cannot fetch thread home channel `{cid}`: {e}"
                ) from e
        if not isinstance(channel, discord.TextChannel):
            raise RuntimeError(
                f"thread home channel `{cid}` is not a text channel "
                f"(got {type(channel).__name__})"
            )
        return channel

    async def _start_persist_session(
        self,
        *,
        user: discord.abc.User,
        text: str,
        notify_message: discord.Message | None,
        source: str,
        source_message: discord.Message | None = None,
        guild_id: int | None = None,
    ) -> discord.Thread:
        async def _notify(content: str) -> None:
            if notify_message is None:
                return
            try:
                await notify_message.edit(content=content)
            except discord.HTTPException as e:
                logger.warning("persist notify edit failed: %s", e)

        if guild_id is None and source_message is not None:
            g = getattr(source_message, "guild", None)
            guild_id = getattr(g, "id", None) if g is not None else None

        try:
            workspace, project_id, project = self._resolve_workspace(text)
        except FileNotFoundError as e:
            await _notify(str(e))
            raise

        try:
            home = await self._get_thread_home_channel(guild_id)
        except RuntimeError as e:
            await _notify(f"**ca_persist failed**\n{e}")
            raise

        chat_id = await create_cursor_chat(bin_path=self.settings.cursor_agent_bin)
        catalog_host = project.host if project is not None else self.settings.local_host
        name = _thread_name(
            project_id, catalog_host, cursor_chat_id=chat_id, text=text
        )

        reuse_notify = (
            notify_message is not None
            and getattr(notify_message.channel, "id", 0) == home.id
            and not isinstance(notify_message.channel, discord.Thread)
        )
        if reuse_notify:
            assert notify_message is not None
            anchor_message = notify_message
        else:
            try:
                anchor_message = await home.send(
                    f"**Maestro /ca_persist** · opening for {user.mention}…"
                )
            except discord.HTTPException as e:
                await _notify(
                    f"**ca_persist failed**\nCannot post in thread home "
                    f"<#{home.id}>: {type(e).__name__}: {e}"
                )
                raise

        try:
            thread = await anchor_message.create_thread(
                name=name,
                auto_archive_duration=1440,
                reason="Maestro ca_persist session",
            )
        except discord.HTTPException as e:
            err = f"**ca_persist failed**\n{type(e).__name__}: {e}"
            try:
                await anchor_message.edit(content=err)
            except discord.HTTPException:
                pass
            if not reuse_notify:
                await _notify(err)
            raise

        try:
            await thread.join()
        except (discord.HTTPException, AttributeError):
            pass

        first_text = text.strip()
        if source_message is not None and list_allowed_attachments(source_message):
            dest = thread_attachments_dir(self.settings.state_dir, thread.id)
            first_text, img_errors, _n = await self._prepare_message_text(
                source_message, first_text, dest=dest
            )
            for err in img_errors:
                try:
                    await thread.send(f"**Attachment** · {err}")
                except discord.HTTPException:
                    pass

        rec = SessionRecord(
            thread_id=thread.id,
            cursor_chat_id=chat_id,
            workspace=str(workspace),
            project_id=project_id,
            host=catalog_host,
            owner_id=user.id,
            parent_channel_id=home.id,
            anchor_message_id=anchor_message.id,
            status="active",
            created_at=datetime.now(timezone.utc).isoformat(),
            thread_name=name,
            mentioned_issue_ids=extract_issue_ids(first_text) or None,
        )
        self.sessions.upsert(rec)

        remote_note = ""
        if project is not None and not project.is_local_to(self.settings.local_host):
            remote_note = f" · remote `ssh {project.ssh_alias}`"

        home_body = (
            f"**Maestro /ca_persist** · `{project_id}` · `{catalog_host}`{remote_note}\n"
            f"Thread: {thread.mention} · session bound (agent on `{self.settings.local_host}`).\n"
            f"Messages in the thread continue Cursor (`--resume`). "
            f"`/stop_ca` stops **this** thread's run. "
            f"Use `/thread_end` **inside** the thread to destroy it."
        )
        try:
            await anchor_message.edit(content=home_body)
        except discord.HTTPException as e:
            logger.warning("persist home anchor edit failed: %s", e)

        if not reuse_notify:
            await _notify(
                f"**Session opened** in {thread.mention} "
                f"(home <#{home.id}>) · `{project_id}` · `{catalog_host}`{remote_note}"
            )

        await thread.send(
            f"Persistent session ready · project `{project_id}` · catalog host `{catalog_host}`.\n"
            f"Send messages here to continue. `/stop_ca` stops the current run · "
            f"`/thread_end` destroys this thread."
        )
        await self._post_original_msg(thread, text.strip())
        chat_log.info(
            "persist started thread=%s project=%s chat=%s source=%s home=%s",
            thread.id,
            project_id,
            chat_id,
            source,
            home.id,
        )
        if not first_text.strip():
            await thread.send("First turn had no text or usable images.")
            return thread
        status, _pos = await self.thread_queues.enqueue(thread.id, first_text)
        if status == "full":
            await thread.send("Could not enqueue first task (queue full).")
        return thread

    async def _handle_queued_thread_turn(self, thread_id: int, text: str) -> None:
        rec = self.sessions.get_active(thread_id)
        if rec is None:
            return
        channel = self.get_channel(thread_id)
        if channel is None:
            try:
                channel = await self.fetch_channel(thread_id)
            except discord.HTTPException:
                self.sessions.close(thread_id)
                return
        if not isinstance(channel, discord.Thread):
            return

        self._last_thread_text[thread_id] = text
        self._track_mentioned_issues(thread_id, text)
        file_count = count_attached_files_in_prompt(text)
        preview = status_preview(text, file_count=file_count)
        stop_view = StopCaView(self, thread_id)
        slot = AgentProcSlot()
        self._thread_slots[thread_id] = slot
        status_msg = await channel.send(
            f"**Busy** · running resume…\n> {preview}",
            view=stop_view,
        )
        keep_stop = True

        async def set_status(content: str) -> None:
            view = (
                stop_view
                if keep_stop and not stop_view.is_finished()
                else None
            )
            try:
                await status_msg.edit(
                    content=content[:_DISCORD_MSG_MAX],
                    view=view,
                )
            except discord.HTTPException:
                try:
                    await channel.send(content[:_DISCORD_MSG_MAX])
                except discord.HTTPException:
                    pass

        async def send_extra(content: str) -> None:
            try:
                await channel.send(content[:_DISCORD_MSG_MAX])
            except discord.HTTPException as e:
                logger.warning("thread extra send failed: %s", e)

        workspace = Path(rec.workspace)
        project = self.catalog.get(rec.project_id)
        user = self.get_user(rec.owner_id) or await self.fetch_user(rec.owner_id)

        if not hasattr(self, "_rich_done"):
            self._rich_done = set()
        inject = thread_id not in self._rich_done

        out_dir = thread_outbound_dir(self.settings.state_dir, thread_id)
        try:
            await self._run_ca_core(
                text=text,
                user=user,
                source="thread-resume",
                set_status=set_status,
                send_extra=send_extra,
                channel=channel,
                resume_chat_id=rec.cursor_chat_id,
                inject_prompt_template=inject,
                persist=True,
                workspace=workspace,
                project=project,
                project_id=rec.project_id,
                proc_slot=slot,
                outbound_dir=out_dir,
            )
            self._rich_done.add(thread_id)
        except AgentCancelled:
            logger.info("persist resume stopped thread=%s", thread_id)
        except Exception as e:
            view = ResumeFailView(self, thread_id)
            view._last_text = text  # type: ignore[attr-defined]
            try:
                await channel.send(
                    f"**Resume failed** · `{type(e).__name__}: {e}`\n"
                    "Choose an option:",
                    view=view,
                )
            except discord.HTTPException:
                logger.warning("could not send resume fail view thread=%s", thread_id)
        finally:
            keep_stop = False
            stop_view.stop()
            try:
                await status_msg.edit(view=None)
            except discord.HTTPException:
                pass
            if self._thread_slots.get(thread_id) is slot:
                self._thread_slots.pop(thread_id, None)

    async def rebind_thread_chat(self, thread_id: int) -> bool:
        rec = self.sessions.get_active(thread_id)
        if rec is None:
            return False
        try:
            chat_id = await create_cursor_chat(bin_path=self.settings.cursor_agent_bin)
        except Exception:
            logger.exception("rebind create-chat failed")
            return False
        self.sessions.update_chat_id(thread_id, chat_id)
        if hasattr(self, "_rich_done"):
            self._rich_done.discard(thread_id)
        # Keep Discord title stamp aligned with the new Cursor chat id.
        old_label = ""
        if rec.thread_name and " · " in rec.thread_name:
            old_label = rec.thread_name.split(" · ", 1)[0].strip()
        name = _thread_name(
            rec.project_id,
            rec.host,
            cursor_chat_id=chat_id,
            label=old_label or None,
        )
        rec2 = self.sessions.get_active(thread_id)
        if rec2 is not None:
            rec2.thread_name = name
            self.sessions.upsert(rec2)
        channel = self.get_channel(thread_id)
        if channel is None:
            try:
                channel = await self.fetch_channel(thread_id)
            except (discord.HTTPException, discord.NotFound):
                channel = None
        if isinstance(channel, discord.Thread):
            try:
                await channel.edit(name=name, reason="Maestro rebind Cursor chat stamp")
            except discord.HTTPException:
                logger.warning("could not rename thread after rebind thread=%s", thread_id)
        return True

    async def _collect_thread_transcript(
        self, thread: discord.Thread, *, limit: int = 50
    ) -> str:
        lines: list[str] = []
        try:
            async for msg in thread.history(limit=limit, oldest_first=True):
                content = (msg.content or "").strip()
                if not content and msg.attachments:
                    names = ", ".join(a.filename or "file" for a in msg.attachments[:5])
                    content = f"[attachment(s): {names}]"
                if not content:
                    continue
                # Skip noisy status heartbeats that are only "Busy · …"
                if content.startswith("**Busy**") and "running" in content.casefold():
                    continue
                who = "Maestro" if msg.author.bot else "Luipy"
                lines.append(f"{who}: {content[:800]}")
        except discord.HTTPException as e:
            logger.warning("thread transcript fetch failed: %s", e)
        return "\n".join(lines[-40:])

    async def _summarize_persist_session(
        self,
        rec: SessionRecord,
        thread: discord.Thread | None,
    ) -> str:
        transcript = ""
        if thread is not None:
            transcript = await self._collect_thread_transcript(thread)
        workspace = Path(rec.workspace)
        if not workspace.is_dir():
            workspace = self.settings.workspace
        prompt_parts = [
            _CLOSE_SUMMARY_PROMPT,
            "",
            f"Thread name: {rec.thread_name or '(none)'}",
            f"Project: {rec.project_id} · host: {rec.host}",
        ]
        if transcript.strip():
            prompt_parts.extend(["", "### Thread transcript", "", transcript.strip()])
        else:
            last = self._last_thread_text.get(rec.thread_id, "")
            if last.strip():
                prompt_parts.extend(["", "### Last operator turn", "", last.strip()[:2000]])
        try:
            result = await call_cursor_agent_session(
                bin_path=self.settings.cursor_agent_bin,
                workspace=workspace,
                prompt_path=None,
                state_dir=self.settings.state_dir,
                user_request="\n".join(prompt_parts),
                timeout_seconds=_CLOSE_SUMMARY_TIMEOUT,
                resume_chat_id=rec.cursor_chat_id,
                inject_prompt_template=False,
            )
            body = result.discord_text(secret_literals=self._secret_literals()).strip()
            if body:
                return body[:1800]
        except Exception:
            logger.exception("close summary cursor-agent failed thread=%s", rec.thread_id)
        # Fallback without LLM
        bits = [
            f"Project `{rec.project_id}` on `{rec.host}`.",
            f"Thread: {rec.thread_name or rec.thread_id}.",
        ]
        if transcript:
            bits.append("Could not LLM-summarize; see thread history before deletion.")
        return "\n".join(f"- {b}" for b in bits)

    async def _post_close_summary(self, rec: SessionRecord, summary: str) -> None:
        parent = self.get_channel(rec.parent_channel_id)
        if parent is None:
            try:
                parent = await self.fetch_channel(rec.parent_channel_id)
            except discord.HTTPException:
                parent = None
        if parent is None:
            logger.warning(
                "close summary: parent channel %s missing", rec.parent_channel_id
            )
            return
        label = rec.thread_name or f"{rec.project_id} · {rec.host}"
        text = sanitize_for_discord(
            f"**Session closed** · `{label}`\n{summary}",
            secret_literals=self._secret_literals(),
        )
        for chunk in chunk_discord(text, limit=_DISCORD_MSG_MAX):
            try:
                await parent.send(chunk)
            except discord.HTTPException as e:
                logger.warning("close summary post failed: %s", e)
                break

    async def _post_redmine_close_notes(
        self,
        rec: SessionRecord,
        *,
        summary: str,
    ) -> str:
        """Post one MaestroBot close note; return a short Discord footnote (or empty)."""
        cfg = self._redmine_config()
        if not cfg.configured:
            return ""
        targets = self._close_note_issue_ids(rec)
        if not targets:
            return ""
        results = await post_session_close_notes(
            cfg=cfg,
            issue_ids=targets,
            project_id=rec.project_id,
            host=rec.host,
            thread_name=rec.thread_name or "",
            cursor_chat_id=rec.cursor_chat_id or "",
            discord_summary=summary,
        )
        if not results:
            return ""
        ok = [iid for iid, err in results if err is None]
        bad = [(iid, err) for iid, err in results if err is not None]
        bits: list[str] = []
        if ok:
            links = ", ".join(f"[#{i}]({cfg.url}/issues/{i})" for i in ok)
            bits.append(f"Redmine close note → {links}")
        if bad:
            bits.append(
                "Redmine note failed for "
                + ", ".join(f"#{i}" for i, _ in bad)
            )
        return " · ".join(bits)

    async def end_persist_thread(
        self,
        thread_id: int,
        *,
        notify_channel: discord.abc.Messageable | None = None,
        summarize: bool = True,
        post_redmine: bool = True,
    ) -> None:
        rec = self.sessions.get_active(thread_id) or self.sessions.get(thread_id)
        channel = self.get_channel(thread_id)
        if channel is None:
            try:
                channel = await self.fetch_channel(thread_id)
            except discord.HTTPException:
                channel = None
        thread = channel if isinstance(channel, discord.Thread) else None

        if summarize and rec is not None and rec.status == "active":
            try:
                summary = await self._summarize_persist_session(rec, thread)
                rm_note = ""
                if post_redmine:
                    try:
                        rm_note = await self._post_redmine_close_notes(
                            rec, summary=summary
                        )
                    except Exception:
                        logger.exception(
                            "redmine close notes failed thread=%s", thread_id
                        )
                if rm_note:
                    summary = f"{summary}\n- {rm_note}"
                await self._post_close_summary(rec, summary)
            except Exception:
                logger.exception("close summary failed thread=%s", thread_id)

        self.thread_queues.clear(thread_id)
        self._thread_slots.pop(thread_id, None)
        self.sessions.close(thread_id)
        purge_thread_attachments(self.settings.state_dir, thread_id)
        purge_thread_outbound(self.settings.state_dir, thread_id)
        if hasattr(self, "_rich_done"):
            self._rich_done.discard(thread_id)
        self._last_thread_text.pop(thread_id, None)

        if thread is not None:
            try:
                await thread.delete(reason="Maestro /thread_end")
                return
            except discord.HTTPException as e:
                logger.warning("thread delete failed: %s", e)
                try:
                    await thread.edit(archived=True, locked=True)
                except discord.HTTPException:
                    pass
        if notify_channel is not None:
            try:
                await notify_channel.send("Session closed (thread already gone).")
            except discord.HTTPException:
                pass

    async def stop_persist_run(self, thread_id: int) -> str:
        """Stop the in-flight resume for one persist thread only.

        Clears that thread's pending queue. Does not touch other threads or
        root-channel one-shot `/ca`. Keeps the Discord thread and Cursor chat.
        """
        rec = self.sessions.get_active(thread_id)
        if rec is None:
            return "No active Maestro persist session for this thread."

        was_busy, dropped = await self.thread_queues.drop_pending(thread_id)
        slot = self._thread_slots.get(thread_id)
        killed = False
        if slot is not None:
            killed = slot.request_cancel()
            if not killed and slot.cancelled:
                # Cancelled before subprocess spawn; handler will raise AgentCancelled.
                killed = was_busy

        if not was_busy and dropped == 0 and not killed:
            return (
                "**Idle** · nothing to stop in this thread "
                "(other threads / root `/ca` are never affected)."
            )

        bits = ["**Stopped** · this thread only"]
        if killed or was_busy:
            bits.append("killed in-flight resume")
        if dropped:
            bits.append(f"dropped queue ×{dropped}")
        bits.append("Cursor chat kept · send a new prompt when ready")
        logger.info(
            "stop_ca thread=%s busy=%s killed=%s dropped=%s",
            thread_id,
            was_busy,
            killed,
            dropped,
        )
        return " · ".join(bits) + "."

    async def _run_stop_ca(self, interaction: discord.Interaction) -> None:
        if not self._is_allowed(interaction.user.id):
            await interaction.response.send_message(_DENY, ephemeral=True)
            return
        ch = interaction.channel
        if not isinstance(ch, discord.Thread):
            await interaction.response.send_message(
                "`/stop_ca` only works **inside** a Maestro persist thread "
                "(does not stop root `/ca` or other threads).",
                ephemeral=True,
            )
            return
        msg = await self.stop_persist_run(ch.id)
        await interaction.response.send_message(msg)

    async def _run_thread_end(
        self,
        interaction: discord.Interaction,
        *,
        clean: bool = False,
    ) -> None:
        if not self._is_allowed(interaction.user.id):
            await interaction.response.send_message(_DENY, ephemeral=True)
            return
        ch = interaction.channel
        if not isinstance(ch, discord.Thread):
            await interaction.response.send_message(
                "`/thread_end` only works **inside** a Maestro persist thread.",
                ephemeral=True,
            )
            return
        rec = self.sessions.get_active(ch.id)
        if rec is None:
            await interaction.response.send_message(
                "No active Maestro session for this thread.",
                ephemeral=True,
            )
            return
        if clean:
            ack = (
                "Ending session · summarizing to parent channel · "
                "no Redmine close note · deleting thread…"
            )
        else:
            ack = (
                "Ending session · summarizing to parent channel · deleting thread…"
            )
        await interaction.response.send_message(ack)
        await self.end_persist_thread(
            ch.id, notify_channel=None, post_redmine=not clean
        )

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if not self._is_allowed(message.author.id):
            return

        # Persist thread follow-ups (no @mention required)
        if isinstance(message.channel, discord.Thread):
            rec = self.sessions.get_active(message.channel.id)
            if rec is not None:
                text = (message.content or "").strip()
                files = list_allowed_attachments(message)
                if not text and not files:
                    return
                if files:
                    dest = thread_attachments_dir(
                        self.settings.state_dir, message.channel.id
                    )
                    text, img_errors, _n = await self._prepare_message_text(
                        message, text, dest=dest
                    )
                    for err in img_errors:
                        try:
                            await message.reply(
                                f"**Attachment** · {err}", mention_author=False
                            )
                        except discord.HTTPException:
                            pass
                if not text.strip():
                    return
                self._track_mentioned_issues(message.channel.id, text)
                status, pos = await self.thread_queues.enqueue(message.channel.id, text)
                if status == "started":
                    return
                if status == "queued":
                    try:
                        await message.reply(
                            f"**Busy** · queued (#{pos}). Will run after the current resume.",
                            mention_author=False,
                        )
                    except discord.HTTPException:
                        pass
                    return
                try:
                    await message.reply(
                        f"**Queue full** (max {_QUEUE_MAX}). Wait, `/stop_ca`, or `/thread_end`.",
                        mention_author=False,
                    )
                except discord.HTTPException:
                    pass
                return

        addressed, via = await _message_addresses_bot(self, message)
        if not addressed:
            return

        if not self.settings.nl_commands:
            return

        guild_id = message.guild.id if message.guild is not None else None
        if not self.settings.is_listen_guild(guild_id):
            return

        await self._handle_nl_message(message, via)

    async def _handle_nl_message(self, message: discord.Message, via: str) -> None:
        me = self.user
        raw = message.content or ""
        user_text = strip_bot_mention(raw, me.id) if me else raw.strip()
        n_files = len(list_allowed_attachments(message))
        if not user_text.strip() and n_files:
            user_text = "Review the attached file(s)."
        chat_log.info(
            "nl input via=%s user=%s text_len=%s files=%s",
            via,
            message.author.id,
            len(user_text),
            n_files,
        )

        status_msg: discord.Message | None = None
        try:
            status_msg = await message.reply(_NL_STATUS_ROUTING, mention_author=False)
        except discord.HTTPException as e:
            logger.warning("nl status reply failed: %s", e)

        async def set_route_status(content: str) -> None:
            await _nl_edit_or_reply(message, status_msg, content)

        route_beat = StatusHeartbeat(
            set_route_status,
            headline="**Maestro** · natural language",
            detail="Routing with cursor-agent",
            interval_seconds=_HEARTBEAT_INTERVAL,
            channel=message.channel,
        )
        await route_beat.start()
        try:
            outcome = await run_nl_router_cursor(
                bin_path=self.settings.cursor_agent_bin,
                workspace=self.settings.repo_root,
                prompts_dir=self.settings.prompts_dir,
                state_dir=self.settings.state_dir,
                user_text=user_text,
                via=via,
                timeout_seconds=self.settings.nl_router_timeout,
            )
        except TimeoutError as e:
            logger.warning("nl router timeout: %s", e)
            outcome = fallback_ca(user_text)
            await route_beat.stop()
            await _nl_edit_or_reply(
                message,
                status_msg,
                "Router timed out · falling back to **`/ca`**…",
            )
        except Exception:
            logger.exception("nl router failed")
            outcome = fallback_ca(user_text)
            await route_beat.stop()
            await _nl_edit_or_reply(
                message,
                status_msg,
                "Router error · falling back to **`/ca`**…",
            )
        else:
            await route_beat.stop()

        if isinstance(outcome, NLParseError):
            chat_log.info("nl parse error detail=%s → fallback ca", outcome.detail)
            inv = fallback_ca(user_text)
            await _nl_edit_or_reply(
                message,
                status_msg,
                "Could not parse router output · falling back to **`/ca`**…",
            )
        else:
            inv = outcome
            if inv.command == "ca":
                await _nl_edit_or_reply(
                    message,
                    status_msg,
                    f"Running **`/ca`** · `{self.settings.local_host}`…",
                )
            elif inv.command == "ca_persist":
                await _nl_edit_or_reply(
                    message,
                    status_msg,
                    f"Running **`/ca_persist`** · `{self.settings.local_host}`…",
                )
            elif inv.command == "ping":
                await _nl_edit_or_reply(message, status_msg, "Running **`/ping`**…")
            elif inv.command == "help":
                await _nl_edit_or_reply(message, status_msg, "Running **`/help`**…")
            elif inv.command == "list_projects":
                await _nl_edit_or_reply(
                    message, status_msg, "Running **`/list_projects`**…"
                )
            elif inv.command == "restart_maestro":
                await _nl_edit_or_reply(
                    message, status_msg, "Running **`/restart_maestro`**…"
                )

        await self._run_nl_invoke(message, inv, status_message=status_msg)

    async def _run_nl_invoke(
        self,
        message: discord.Message,
        inv: NLInvoke,
        *,
        status_message: discord.Message | None,
    ) -> None:
        cmd = inv.command
        args = inv.args
        chat_log.info("nl dispatch command=%s", cmd)

        if cmd == "ping":
            latency_ms = round(self.latency * 1000)
            await _nl_edit_or_reply(
                message, status_message, f"Pong · `{latency_ms} ms`"
            )
            return
        if cmd == "help":
            await _reply_chunked(
                message,
                _HELP + self._restart_pending_note(),
                edit_first=status_message,
            )
            return
        if cmd == "restart_maestro":
            if not self._is_luipy(message.author.id):
                await _nl_edit_or_reply(message, status_message, _DENY_RESTART)
                return
            force = bool(args.get("force"))
            decision = operator_restart(
                state_dir=self.settings.state_dir,
                force=force,
                busy_threads=self.thread_queues.busy_count(),
            )
            logger.info(
                "nl restart_maestro force=%s action=%s",
                force,
                decision.action,
            )
            await _nl_edit_or_reply(message, status_message, decision.detail)
            return
        if cmd == "list_projects":
            host = str(args.get("host") or "all").strip() or "all"
            body = format_list_projects(self.catalog, host_filter=host)
            await _reply_chunked(message, body, edit_first=status_message)
            return
        if cmd == "ca_persist":
            text = str(args.get("text") or "").strip()
            if status_message is None:
                status_message = await message.reply(
                    "Creating persist session…", mention_author=False
                )
            else:
                await _nl_edit_or_reply(
                    message, status_message, "Creating Cursor chat + Discord thread…"
                )
            try:
                await self._start_persist_session(
                    user=message.author,
                    text=text,
                    notify_message=status_message,
                    source="nl-persist",
                    source_message=message,
                    guild_id=getattr(message.guild, "id", None),
                )
            except Exception as e:
                logger.exception("nl ca_persist failed")
                await _nl_edit_or_reply(
                    message,
                    status_message,
                    f"**ca_persist failed**\n{type(e).__name__}: {e}",
                )
            return
        if cmd == "ca":
            text = str(args.get("text") or "").strip()
            if list_allowed_attachments(message):
                dest = oneshot_attachments_dir(self.settings.state_dir, message.id)
                text, img_errors, _n = await self._prepare_message_text(
                    message, text, dest=dest
                )
                for err in img_errors:
                    try:
                        await message.channel.send(f"**Attachment** · {err}")
                    except discord.HTTPException:
                        pass

            async def set_status(content: str) -> None:
                await _nl_edit_or_reply(message, status_message, content)

            async def send_extra(content: str) -> None:
                try:
                    await message.channel.send(content[:_DISCORD_MSG_MAX])
                except discord.HTTPException as e:
                    logger.warning("nl ca extra send failed: %s", e)

            await self._run_ca_core(
                text=text,
                user=message.author,
                source="nl",
                set_status=set_status,
                send_extra=send_extra,
                channel=message.channel,
                outbound_dir=oneshot_outbound_dir(
                    self.settings.state_dir, message.id
                ),
            )
            return

        await _nl_edit_or_reply(
            message, status_message, f"Unknown routed command `{cmd}`."
        )

    async def _attachment_cleanup_loop(self) -> None:
        while True:
            try:
                removed = purge_expired_attachments(self.settings.state_dir)
                if removed:
                    logger.info("attachment TTL cleanup removed %s path(s)", removed)
            except Exception:
                logger.exception("attachment TTL cleanup failed")
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

    async def setup_hook(self) -> None:
        guild_ids = self.settings.guild_ids
        if guild_ids:
            for gid in guild_ids:
                guild = discord.Object(id=gid)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(
                    "Synced %s guild slash command(s) to guild %s",
                    len(synced),
                    gid,
                )
        else:
            synced = await self.tree.sync()
            logger.info("Synced %s global slash command(s)", len(synced))
        if self._attachment_cleanup_task is None or self._attachment_cleanup_task.done():
            self._attachment_cleanup_task = asyncio.create_task(
                self._attachment_cleanup_loop(),
                name="maestro-attachment-ttl",
            )
            # Immediate sweep on boot
            try:
                removed = purge_expired_attachments(self.settings.state_dir)
                if removed:
                    logger.info("attachment TTL boot cleanup removed %s path(s)", removed)
            except Exception:
                logger.exception("attachment TTL boot cleanup failed")

    async def on_ready(self) -> None:
        user = self.user
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"v{__version__}",
        )
        try:
            await self.change_presence(activity=activity)
        except discord.HTTPException as e:
            logger.warning("change_presence(watching v%s) failed: %s", __version__, e)
        homes_fmt = ",".join(
            f"{h.guild_id}:{h.channel_id}" for h in self.settings.homes
        ) or f"{self.settings.guild_id}:{self.settings.channel_id}"
        logger.info(
            "Maestro online as %s (%s) | v%s | homes=%s | thread_home_fallback=%s | host=%s | "
            "nl=%s | message_content=%s | projects=%s",
            user,
            user.id if user else "?",
            __version__,
            homes_fmt,
            self.settings.thread_home_channel_id,
            self.settings.local_host,
            self.settings.nl_commands,
            self.settings.message_content_intent,
            len(self.catalog.all_active()),
        )


def run_bot(settings: Settings) -> None:
    if not settings.guild_ids:
        raise RuntimeError(
            "At least one Discord home is required "
            "(discord.homes or DISCORD_GUILD_ID / discord.guild_id)"
        )
    bot = MaestroBot(settings)
    bot.run(settings.token, log_handler=None)
