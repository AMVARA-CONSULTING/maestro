"""Discord UI for persisted session resume failures and stop controls."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from maestro.bot import MaestroBot

logger = logging.getLogger(__name__)


class StopCaView(discord.ui.View):
    """Stop button on the busy status message (this thread only)."""

    def __init__(self, bot: MaestroBot, thread_id: int) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.thread_id = thread_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.bot._is_allowed(interaction.user.id):
            await interaction.response.send_message(
                "Maestro only responds to **allowlisted** operators.",
                ephemeral=True,
            )
            return False
        if interaction.channel_id != self.thread_id:
            await interaction.response.send_message(
                "`/stop_ca` / Stop only apply to **this** persist thread.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_ca(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        msg = await self.bot.stop_persist_run(self.thread_id)
        try:
            await interaction.followup.send(msg)
        except discord.HTTPException as e:
            logger.warning("stop_ca button followup failed: %s", e)
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        try:
            if interaction.message is not None:
                await interaction.message.edit(view=self)
        except discord.HTTPException:
            pass
        self.stop()


class ResumeFailView(discord.ui.View):
    def __init__(self, bot: MaestroBot, thread_id: int) -> None:
        super().__init__(timeout=600)
        self.bot = bot
        self.thread_id = thread_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.bot._is_allowed(interaction.user.id):
            await interaction.response.send_message(
                "Maestro only responds to **allowlisted** operators.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Retry", style=discord.ButtonStyle.primary)
    async def retry(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        text = getattr(self, "_last_text", None) or "Retry previous request"
        await interaction.followup.send("Retrying…", ephemeral=True)
        status, pos = await self.bot.thread_queues.enqueue(self.thread_id, text)
        if status == "full":
            await interaction.followup.send("Queue full.", ephemeral=True)
        elif status == "queued":
            await interaction.followup.send(f"Queued (#{pos}).", ephemeral=True)
        self.stop()

    @discord.ui.button(label="New Cursor session", style=discord.ButtonStyle.secondary)
    async def new_session(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        ok = await self.bot.rebind_thread_chat(self.thread_id)
        if not ok:
            await interaction.followup.send(
                "Could not create a new Cursor chat. Try `/thread_end`.",
                ephemeral=True,
            )
            return
        text = getattr(self, "_last_text", None) or "Continue previous task in a new Cursor chat"
        await self.bot.thread_queues.enqueue(self.thread_id, text)
        await interaction.followup.send("New Cursor chat bound · running…", ephemeral=True)
        self.stop()

    @discord.ui.button(label="End thread", style=discord.ButtonStyle.danger)
    async def end_thread(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        await self.bot.end_persist_thread(self.thread_id, notify_channel=interaction.channel)
        self.stop()
