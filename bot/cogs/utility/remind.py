import asyncio
from contextlib import suppress
from datetime import datetime, timedelta

from discord import ApplicationContext, Embed, HTTPException
from discord.commands import Option, SlashCommandGroup
from discord.ext.commands import BucketType, cooldown
from discord.utils import utcnow
from pytimeparse import parse
from tools.bot import Anomaly
from tools.cog import Cog
from tools.colors import Colors


class Remind(Cog, name="Remind"):
    """Remind module"""

    def __init__(self, bot: Anomaly):
        super().__init__(bot)
        loop = self.bot.loop

        statement = """
        SELECT reminder_id, user_id, reminder, expires
        FROM Reminders;
        """
        reminders = self.bot.database.execute(statement, count=-1) or []

        for r in reminders:
            if r[3] > utcnow():
                timeLater = loop.time()+(r[3]-utcnow()).total_seconds()
            else:
                timeLater = loop.time()
            loop.call_soon(self.remind, timeLater, r[0], r[1], r[2])

    async def remind(self, reminder_id: int, user_id: int, message: str):
        await self.bot.wait_until_ready()

        user = await self.bot.get_or_fetch_user(user_id)
        if not user:
            return

        embed = Embed(title="I'm reminding you about something!",
                      description=message, color=Colors.hot_pink())
        embed.set_footer(text=f"ID: {reminder_id}")

        with suppress(HTTPException):
            await user.send(embed=embed)

        statement = """
        DELETE FROM Reminders
        WHERE reminder_id = %s;
        """
        self.bot.database.execute(statement, (reminder_id,))

    RootGroup = SlashCommandGroup(
        "remind", "Commands related to the Remind module")

    @RootGroup.command(name="add")
    @cooldown(1, 5, BucketType.member)
    async def add_reminder(self, ctx: ApplicationContext, message: Option(str, "What should I remind you about?", required=True), when: Option(str, "When should I remind you?", required=True)):
        """Add a reminder"""

        await ctx.defer(ephemeral=True)

        seconds = parse(when)
        if seconds is None:
            await ctx.respond("I don't understand that duration format!", ephemeral=True)
            return

        remindAt = utcnow()+timedelta(seconds=seconds)

        statement = """
        INSERT INTO Reminders(user_id, reminder, expires)
        VALUES (%s, %s, %s)
        RETURNING reminder_id;
        """

        reminder_id = self.bot.database.execute(
            statement, (ctx.author.id, message, remindAt), 1)

        embed = Embed(title="Reminder Created!", color=Colors.hot_pink())
        embed.description = message
        timeFormat = f"<t:{int(remindAt.timestamp())}:R> (<t:{int(remindAt.timestamp())}:F>)"
        embed.add_field(name="You will be reminded",
                        value=timeFormat, inline=False)
        embed.set_footer(text=f"ID: {reminder_id}")

        await ctx.respond(embed=embed, ephemeral=True)

        await self.remind(reminder_id=reminder_id, message=message, user=ctx.author, when=remindAt)


def setup(bot):
    bot.add_cog(Remind(bot))
