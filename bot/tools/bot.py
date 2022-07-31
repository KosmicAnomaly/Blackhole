import logging
import re
from contextlib import suppress

from discord import (AllowedMentions, Bot, Guild, HTTPException, Intents,
                     PartialEmoji)
from discord.utils import utcnow
from emoji import UNICODE_EMOJI

from tools.database import Database

logger = logging.getLogger("kosmo")


class Anomaly(Bot):
    def __init__(self):

        allowed_mentions = AllowedMentions(
            everyone=False,
            roles=True,
            users=True,
            replied_user=True
        )
        intents = Intents(
            emojis_and_stickers=True,
            guild_messages=True,
            guild_reactions=True,
            guilds=True,
            members=True,
            message_content=True,
            presences=True,
            voice_states=True
        )

        super().__init__(
            chunk_guilds_at_startup=True,
            help_command=None,
            heartbeat_timeout=120.0,
            allowed_mentions=allowed_mentions,
            intents=intents,
            enable_debug_events=True,
            debug_guilds=[821043163716124713]
        )

        self.database = Database()

        self.connected = False

    def process_reconnect(self):
        self.connected = True
        if self.last_disconnect:
            seconds = (utcnow() - self.last_disconnect).total_seconds()
            if seconds >= 60:
                logger.warning(
                    f"Reconnected to Discord after {seconds} seconds of downtime")

    async def on_ready(self):
        if not hasattr(self, "start_time"):
            self.start_time = utcnow()
            logger.info(
                f"{self.user} has logged into Discord (Running on {len(self.guilds)} servers)")

        if not self.connected:
            self.process_reconnect()

    async def on_connect(self):
        if not self.connected:
            self.process_reconnect()

        await self.sync_commands()

    async def on_resumed(self):
        if not self.connected:
            self.process_reconnect()

    async def on_disconnect(self):
        if self.connected:
            self.connected = False
            self.last_disconnect = utcnow()

    async def on_guild_join(self, guild: Guild):
        """Logs when Kosmo joins a server"""
        logger.info(
            f"{self.user} joined a server (Name: {guild.name}, ID: {guild.id}, Member Count: {guild.member_count})")

    async def on_guild_remove(self, guild: Guild):
        """Logs when Kosmo leaves a server"""
        logger.info(
            f"{self.user} was removed from a server (Name: {guild.name}, ID: {guild.id})")

    async def get_or_fetch_channel(self, id: int):
        channel = self.get_channel(id)
        if not channel:
            with suppress(HTTPException):
                channel = await self.fetch_channel(id)
        return channel

    def get_emoji_object(self, emoji: str):
        if re.fullmatch(r"<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18}>", emoji):
            partial = PartialEmoji.from_str(emoji)
            emoji = self.get_emoji(partial.id)
            return emoji

        if emoji in UNICODE_EMOJI["en"].keys():
            return PartialEmoji.from_str(emoji)
        else:
            return None
