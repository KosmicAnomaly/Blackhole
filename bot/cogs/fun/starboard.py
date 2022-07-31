import math
from contextlib import suppress

from discord import (ButtonStyle, Embed, HTTPException, Message, PartialEmoji,
                     RawReactionActionEvent, RawReactionClearEmojiEvent,
                     RawReactionClearEvent)
from discord.ui import Button, View
from discord.utils import get
from tools.cog import Cog
from tools.colors import Colors


def min_stars(requirement: int):
    return math.floor(0.75 * requirement)


def build_star_embed(message: Message):
    embed = Embed(color=Colors.gold())

    # If the message was an embed, use that for the starboard embed
    if len(message.embeds):
        firstEmbed = message.embeds[0]
        embed.title = firstEmbed.title
        embed.description = firstEmbed.description
        if firstEmbed.image != Embed.Empty:
            embed.set_image(url=firstEmbed.image.url)

    else:
        embed.description = message.content
        if len(message.attachments):
            embed.set_image(url=message.attachments[0].url)

    embed.set_author(name=message.author,
                     icon_url=message.author.avatar.url)
    embed.timestamp = message.created_at

    return embed


class Starboard(Cog, name="Starboard"):

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if not payload.guild_id:
            return

        if payload.emoji != PartialEmoji.from_str("⭐"):
            return

        statement = """
        SELECT enabled, channel_id, required_stars FROM LevelingSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (payload.guild_id,), 1)

        if not settings or not settings[0] or not settings[1]:
            return

        starboardChannel = self.bot.get_or_fetch_channel(settings[1])
        if not starboardChannel:
            return

        sourceChannel = self.bot.get_or_fetch_channel(payload.channel_id)

        try:
            message = await sourceChannel.fetch_message(payload.message_id)
        except HTTPException:
            return

        reaction = get(message.reactions, emoji=PartialEmoji.from_str("⭐"))

        if reaction:
            count = reaction.count
        else:
            count = 0

        statement = """
        SELECT starboard_message_id FROM StarboardMessages
        WHERE guild_id = %s AND source_message_id = %s;
        """

        starboardMessageID = self.bot.database.execute(
            statement, (payload.guild_id, message.id), 1)

        starboardMessage = None
        if starboardMessageID:
            with suppress(HTTPException):
                starboardMessage = await starboardChannel.fetch_message(starboardMessageID)

        # If the starboard message exists, and the stars has dropped below the required amount, delete the message
        if count < min_stars(settings[2]):

            if starboardMessage:
                with suppress(HTTPException):
                    await starboardMessage.delete()

            statement = """
            DELETE FROM StarboardMessages
            WHERE source_message_id = %s;
            """

            self.bot.database.execute(statement, (starboardMessageID,))
            return

        rebuild = False
        if starboardMessage:
            if starboardMessage.flags.suppress_embeds:
                with suppress(HTTPException):
                    await starboardMessage.delete()
                rebuild = True

            else:
                with suppress(HTTPException):
                    await starboardMessage.edit(content=f"**{count} ⭐**", embed=starboardMessage.embeds[0])
                return

        if rebuild or count >= settings[2]:
            embed = build_star_embed(message)

            starboardMessage = None

            view = View()
            url = message.jump_url.replace("@me", str(payload.guild_id))
            view.add_item(Button(style=ButtonStyle.link,
                                 label="Jump to message", url=url, row=0))

            with suppress(HTTPException):
                starboardMessage = await starboardChannel.send(content=f"⭐ **{count} Stars**", embed=embed, view=view)

            if starboardMessage:
                statement = """
                INSERT INTO StarboardMessages(guild_id, source_message_id, starboard_message_id)
                VALUES (%s, %s, %s)  ON CONFLICT (source_message_id) DO UPDATE
                    SET starboard_message_id = %s;
                """
                self.bot.database.execute(
                    statement, (payload.guild_id, message.id, starboardMessage.id, starboardMessage.id))

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):

        if not payload.guild_id:
            return

        if payload.emoji != PartialEmoji.from_str("⭐"):
            return

        statement = """
        SELECT enabled, channel_id, required_stars FROM LevelingSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (payload.guild_id,), 1)

        if not settings or not settings[0]:
            return

        if not settings[1]:
            return

        starboardChannel = self.bot.get_or_fetch_channel(settings[1])
        if not starboardChannel:
            return

        sourceChannel = self.bot.get_or_fetch_channel(payload.channel_id)

        try:
            message = await sourceChannel.fetch_message(payload.message_id)
        except HTTPException:
            return

        reaction = get(message.reactions, emoji=PartialEmoji.from_str("⭐"))

        if reaction:
            count = reaction.count
        else:
            count = 0

        statement = """
        SELECT starboard_message_id FROM StarboardMessages
        WHERE guild_id = %s AND source_message_id = %s;
        """

        starboardMessageID = self.bot.database.execute(
            statement, (payload.guild_id, message.id), 1)

        starboardMessage = None
        if starboardMessageID:
            with suppress(HTTPException):
                starboardMessage = await starboardChannel.fetch_message(starboardMessageID)

        # If the starboard message exists, and the stars has dropped below the required amount, delete the message
        if count < min_stars(settings[2]):

            if starboardMessage:
                with suppress(HTTPException):
                    await starboardMessage.delete()

            statement = """
            DELETE FROM StarboardMessages
            WHERE source_message_id = %s;
            """

            self.bot.database.execute(statement, (starboardMessageID,))
            return

        rebuild = False
        if starboardMessage:
            if starboardMessage.flags.suppress_embeds:
                with suppress(HTTPException):
                    await starboardMessage.delete()
                rebuild = True

            else:
                with suppress(HTTPException):
                    await starboardMessage.edit(content=f"**{count} ⭐**", embed=starboardMessage.embeds[0])
                return

        if rebuild or count >= settings[2]:
            embed = build_star_embed(message)

            starboardMessage = None

            view = View()
            url = message.jump_url.replace("@me", str(payload.guild_id))
            view.add_item(Button(style=ButtonStyle.link,
                                 label="Jump to message", url=url, row=0))

            with suppress(HTTPException):
                starboardMessage = await starboardChannel.send(content=f"⭐ **{count} Stars**", embed=embed, view=view)

            if starboardMessage:
                statement = """
                INSERT INTO StarboardMessages(guild_id, source_message_id, starboard_message_id)
                VALUES (%s, %s, %s)  ON CONFLICT (source_message_id) DO UPDATE
                    SET starboard_message_id = %s;
                """
                self.bot.database.execute(
                    statement, (payload.guild_id, message.id, starboardMessage.id, starboardMessage.id))

    @Cog.listener()
    async def on_raw_reaction_clear(self, payload: RawReactionClearEvent):

        if not payload.guild_id:
            return

        statement = """
        SELECT enabled, channel_id, required_stars FROM LevelingSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (payload.guild_id,), 1)

        if not settings or not settings[0]:
            return

        if not settings[1]:
            return

        starboardChannel = self.bot.get_or_fetch_channel(settings[1])
        if not starboardChannel:
            return

        sourceChannel = self.bot.get_or_fetch_channel(payload.channel_id)

        try:
            message = await sourceChannel.fetch_message(payload.message_id)
        except HTTPException:
            return

        statement = """
        SELECT starboard_message_id FROM StarboardMessages
        WHERE guild_id = %s AND source_message_id = %s;
        """

        starboardMessageID = self.bot.database.execute(
            statement, (payload.guild_id, message.id), 1)

        starboardMessage = None
        if starboardMessageID:
            with suppress(HTTPException):
                starboardMessage = await starboardChannel.fetch_message(starboardMessageID)

        if starboardMessage:
            with suppress(HTTPException):
                await starboardMessage.delete()

        statement = """
        DELETE FROM StarboardMessages
        WHERE source_message_id = %s;
        """

        self.bot.database.execute(statement, (starboardMessageID,))

    @Cog.listener()
    async def on_reaction_clear_emoji(self, payload: RawReactionClearEmojiEvent):

        if payload.emoji != PartialEmoji.from_str("⭐"):
            return

        if not payload.guild_id:
            return

        statement = """
        SELECT enabled, channel_id, required_stars FROM LevelingSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (payload.guild_id,), 1)

        if not settings or not settings[0]:
            return

        if not settings[1]:
            return

        starboardChannel = self.bot.get_or_fetch_channel(settings[1])
        if not starboardChannel:
            return

        sourceChannel = self.bot.get_or_fetch_channel(payload.channel_id)

        try:
            message = await sourceChannel.fetch_message(payload.message_id)
        except HTTPException:
            return

        statement = """
        SELECT starboard_message_id FROM StarboardMessages
        WHERE guild_id = %s AND source_message_id = %s;
        """

        starboardMessageID = self.bot.database.execute(
            statement, (payload.guild_id, message.id), 1)

        starboardMessage = None
        if starboardMessageID:
            with suppress(HTTPException):
                starboardMessage = await starboardChannel.fetch_message(starboardMessageID)

        if starboardMessage:
            with suppress(HTTPException):
                await starboardMessage.delete()

        statement = """
        DELETE FROM StarboardMessages
        WHERE source_message_id = %s;
        """

        self.bot.database.execute(statement, (starboardMessageID,))


def setup(bot):
    bot.add_cog(Starboard(bot))
