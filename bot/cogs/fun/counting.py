import ast
import logging
import re
from contextlib import suppress

from discord import (ApplicationContext, Embed, HTTPException, Message,
                     RawBulkMessageDeleteEvent, RawMessageDeleteEvent,
                     RawMessageUpdateEvent)
from discord.commands import SlashCommandGroup
from discord.ext.commands import BucketType, cooldown, guild_only
from tools.cog import Cog
from tools.colors import Colors

logger = logging.getLogger("kosmo")

special_numbers = {
    3: "✨",
    7: "🍀",
    13: "🎲",
    21: "🍻",
    42: "💻",
    66: "🔫",
    69: "👌",
    100: "💯",
    101: "🐕",
    404: "⚠️",
    420: "🌿",
    666: "😈",
    1922: "🇷🇺",
    2020: "🔥",
    7573: "🔁",
    9001: "❗"
}


def eval_ast(node):
    match node:
        case ast.Expression(body):
            return eval_ast(body)
        case ast.BinOp(left, ast.Add(), right):
            return eval_ast(left) + eval_ast(right)
        case ast.BinOp(left, ast.Sub(), right):
            return eval_ast(left) - eval_ast(right)
        case ast.BinOp(left, ast.Mult(), right):
            return eval_ast(left) * eval_ast(right)
        case ast.BinOp(left, ast.Div(), right):
            return eval_ast(left) / eval_ast(right)
        case ast.BinOp(left, ast.Pow(), right):
            if eval_ast(right) > 10:
                raise OverflowError
            return eval_ast(left) ** eval_ast(right)
        case ast.Constant(x):
            return x
        case _:
            raise ValueError("Operation Not Supported")


def do_math(input: str):
    # If it's just a number, return it
    if re.fullmatch(r"[0-9]", input):
        return int(input)
    # Otherwise, make sure that it matches our allowed characters
    if not re.fullmatch(r"[0-9()x^\-+./ ]+", input):
        return None

    # Character conversion
    input = input.replace("x", "*").replace("^", "**")

    # Handle parenthesis multiplication
    input = re.sub(r"([0-9]|\))\(", r"\1*(", input)

    # Try to run the equation
    with suppress(OverflowError, ValueError):
        return eval_ast(ast.parse(input, mode="eval"))


class Counting(Cog, name="Counting"):
    """Counting module"""

    RootGroup = SlashCommandGroup(
        "ct", "Commands related to Counting")

    @RootGroup.command(name="stats")
    @cooldown(1, 5, BucketType.channel)
    @cooldown(1, 10, BucketType.member)
    @guild_only()
    async def stats(self, ctx: ApplicationContext):
        """Display the server's Counting stats"""

        statement = """
        SELECT enabled FROM CountingSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (ctx.guild.id,), 1)

        if not settings or not settings[0]:
            await ctx.respond("The Counting module is disabled!", ephemeral=True)
            return

        statement = """
        SELECT next_number, highscore, last_counted_member_id FROM CountingData
        WHERE guild_id = %s;
        """
        data = self.bot.database.execute(
            statement, (ctx.guild.id,), 1)

        if not data:
            await ctx.respond("Nobody has started counting!", ephemeral=True)
            return

        await ctx.defer()

        embed = Embed(title="Counting Stats", color=Colors.deep_blue())

        embed.add_field(name="Next Number",
                        value=data[0], inline=True)

        lastCounted = ctx.guild.get_member(data[2])
        if lastCounted:
            embed.add_field(name="Last Counted",
                            value=lastCounted.mention, inline=True)
        else:
            embed.add_field(name="Last Counted", value=data[2], inline=True)

        embed.add_field(name="Highscore", value=data[1], inline=False)

        await ctx.respond(embed=embed)

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        elif not message.guild:
            return
        elif not message.content:
            return

        guild = message.guild
        channel = message.channel

        statement = """
        SELECT enabled, allow_math FROM CountingSettings
        WHERE (guild_id = %s) AND (channel_id = %s);
        """
        settings = self.bot.database.execute(
            statement, (guild.id, channel.id), 1)

        if not settings or not settings[0]:
            return

        statement = """
        SELECT next_number, highscore, last_counted_member_id FROM CountingData
        WHERE guild_id = %s;
        """
        data = self.bot.database.execute(
            statement, (guild.id,), 1) or (1, 0, None)

        if settings[1]:
            sentNumber = do_math(message.clean_content)

            # Ignore it if it isn't a number
            if sentNumber is None:
                return
            # Ignore it if it isn't greater than or equal to 0
            elif sentNumber < 0:
                return
            # Ignore it if it isn't an integer
            elif isinstance(sentNumber, float):
                if not sentNumber.is_integer():
                    return
                sentNumber = int(sentNumber)
        else:
            sentNumber = message.clean_content
            if not re.fullmatch(r"[0-9]+", sentNumber):
                return
            sentNumber = int(sentNumber)

        description = None
        if sentNumber != data[0]:
            if data[0] == 1 and sentNumber != 1:
                return
            description = f"{message.author.mention} can't count past {data[0]}!"
        if message.author.id == data[2]:
            description = f"{message.author.mention} is trying to count alone!"

        if description:
            embed = Embed(title="Count Reset to 0",
                          description=description, color=Colors.deep_orange())
            highscore = max(data[0]-1, data[1])
            if highscore > data[1]:
                embed.set_footer(text=f"New highscore of {highscore}!")
            else:
                embed.set_footer(text=f"Highscore: {highscore}")

            statement = """
            UPDATE CountingData
                SET next_number = 1,
                highscore = %s,
                last_counted_member_id = NULL,
                last_counted_message_id = NULL
            WHERE guild_id = %s;
            """
            self.bot.database.execute(statement, (highscore, guild.id))

            with suppress(HTTPException):
                await message.add_reaction("❌")
            with suppress(HTTPException):
                await message.channel.send(embed=embed)

        else:
            statement = """
            INSERT INTO CountingData VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT(guild_id) DO UPDATE
                SET next_number = %s,
                last_counted_member_id = %s,
                last_counted_message_id = %s;
            """
            self.bot.database.execute(
                statement, (guild.id, data[0]+1, 0, message.author.id, message.id, data[0]+1, message.author.id, message.id))

            with suppress(HTTPException):
                await message.add_reaction("✅")

            if data[0]+1 in special_numbers.keys():
                with suppress(HTTPException):
                    await message.add_reaction(special_numbers[data[0]+1])

    async def prevent_trolling(self, payload):
        statement = """
        SELECT enabled, allow_math FROM CountingSettings
        WHERE guild_id = %s AND channel_id = %s;
        """

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        settings = self.bot.database.execute(
            statement, (payload.guild_id, channel.id), 1)

        if not settings or not settings[0]:
            return

        statement = """
        SELECT next_number, last_counted_member_id, last_counted_message_id FROM CountingData
        WHERE guild_id = %s;
        """
        data = self.bot.database.execute(
            statement, (payload.guild_id,), 1)

        if not data or data[0] == 1:
            return

        if hasattr(payload, "message_ids") and data[2] not in payload.message_ids:
            return
        elif data[2] != payload.message_id:
            return

        author = await self.bot.get_or_fetch_user(data[1])
        if author:
            author = author.mention
        else:
            author = data[1]

        with suppress(HTTPException):
            msg = None
            msg = await channel.send(f"⚠️ Next Number: **{data[0]}**\nLast Counted: {author}")

        statement = """
        UPDATE CountingData
            SET last_counted_message_id = %s
        WHERE guild_id = %s;
        """
        self.bot.database.execute(
            statement, (msg.id, payload.guild_id))

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        """Handle when members edit their counting messages"""

        await self.prevent_trolling(payload)

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        """Handle when members delete their counting messages"""

        await self.prevent_trolling(payload)

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        """Handle when a counting message is purged"""

        await self.prevent_trolling(payload)


def setup(bot):
    bot.add_cog(Counting(bot))
