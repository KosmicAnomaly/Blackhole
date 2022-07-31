import re
from contextlib import suppress
from datetime import timedelta

from discord import ApplicationContext, Embed, HTTPException, Member
from discord.commands import Option, slash_command
from discord.ext.commands import (bot_has_guild_permissions, guild_only,
                                  has_guild_permissions)
from discord.utils import utcnow
from tools.cog import Cog
from tools.colors import Colors
from tools.tools import ConfirmationView

class Jschlatt(Cog, name="Jschlatt"):
    """The ultimate mass-action utility"""

    @slash_command(name="jschlatt")
    @bot_has_guild_permissions(ban_members=True, kick_members=True, moderate_members=True)
    @has_guild_permissions(administrator=True)
    @guild_only()
    async def jschlatt(self, ctx: ApplicationContext, action: Option(str, "Action to take on matching members", choices=["Ban Members", "Kick Members", "1 Hour Mute", "1 Day Mute", "1 Week Mute"], required=True), regex: Option(str, "Take action on members who match this regular expression", required=False, default=None), minutes: Option(int, "Take action on members who joined in the last [x] minutes", min_value=0, required=False, default=None), reason: Option(str, "Reason for taking action", required=False, default="No reason provided")):
        """Take action on many server members at once"""

        if regex:
            try:
                pattern = re.compile(regex)

            except re.error:
                await ctx.respond("That is not a valid regex expression!", ephemeral=True)
                return
        else:
            pattern = None

        if minutes:
            threshold = utcnow()-timedelta(minutes=minutes)
        else:
            threshold = None

        if threshold is None and pattern is None:
            await ctx.respond("That would ban everyone O.o", ephemeral=True)
            return

        await ctx.defer()

        def should_yeet(member: Member):
            if member.id == ctx.me.id:
                return False
            if member.id == ctx.author.id:
                return False
            if member.top_role >= ctx.me.top_role:
                return False
            if member.top_role >= ctx.author.top_role:
                if ctx.author.id != ctx.guild.owner.id:
                    return False
            if member.id == ctx.guild.owner.id:
                return False

            if threshold:
                if member.joined_at < threshold:
                    return False
            if pattern:
                if not re.fullmatch(pattern, member.display_name):
                    return False

            return True

        toYeet = list(filter(should_yeet, ctx.guild.members))

        if not len(toYeet):
            await ctx.respond("No matches!")
            return

        embed = Embed(title="*Preparing to launch tactical nuke*",
                      color=Colors.dark_red())

        if action == "Ban Members":
            embed.description = f"**{len(toYeet)} members** will be banned from this server.\nAre you sure you want to continue?"

        elif action == "Kick Members":
            embed.description = f"**{len(toYeet)} members** will be kicked from this server.\nAre you sure you want to continue?"

        elif action == "1 Hour Mute":
            embed.description = f"**{len(toYeet)} members** will be muted until <t:{int((utcnow()+timedelta(hours=1)).timestamp())}:F>\nAre you sure you want to continue?"

        elif action == "1 Day Mute":
            embed.description = f"**{len(toYeet)} members** will be muted until <t:{int((utcnow()+timedelta(days=1)).timestamp())}:F>\nAre you sure you want to continue?"

        elif action == "1 Week Mute":
            embed.description = f"**{len(toYeet)} members** will be muted until <t:{int((utcnow()+timedelta(weeks=1)).timestamp())}:F>\nAre you sure you want to continue?"

        if pattern:
            embed.add_field(
                name="Regex", value=f"```\n{regex}\n```", inline=False)
        if threshold:
            embed.add_field(
                name="Joined after", value=f"<t:{int(threshold.timestamp())}:f>", inline=False)

        view = ConfirmationView()

        await ctx.respond(embed=embed, view=view)

        await view.wait()
        if not view.value:
            await ctx.edit(content="Aborted.", embed=None, view=None)
            return

        embed = Embed(title="*Launching tactical nuke*",
                      color=Colors.dark_red())

        if action == "Ban Members":
            embed.description = f"Banning **{len(toYeet)} members.**"

        elif action == "Kick Members":
            embed.description = f"Kicking **{len(toYeet)} members.**"

        else:
            embed.description = f"Muting **{len(toYeet)} members.**"

        if pattern:
            embed.add_field(
                name="Regex", value=f"```\n{regex}\n```", inline=False)
        if threshold:
            embed.add_field(
                name="Joined after", value=f"<t:{int(threshold.timestamp())}:f>", inline=False)

        await ctx.edit(content=None, embed=embed, view=None)

        counter = 0

        if action == "Ban Members":
            for m in toYeet:
                with suppress(HTTPException):
                    await m.ban(reason=f"{reason}\nBanned by {ctx.author} ({ctx.author.id})")
                    counter += 1

        elif action == "Kick Members":
            for m in toYeet:
                with suppress(HTTPException):
                    await m.kick(reason=f"{reason}\nKicked by {ctx.author} ({ctx.author.id})")
                    counter += 1

        elif action == "1 Hour Mute":
            for m in toYeet:
                timeoutTd = timedelta(hours=1)
                if m.timed_out:
                    timeLeft = m.communication_disabled_until-utcnow()
                    timeoutTd += timeLeft
                    if timeoutTd > timedelta(days=28):
                        timeoutTd = timedelta(days=28)

                with suppress(HTTPException):
                    await m.timeout_for(duration=timeoutTd, reason=f"{reason} - Muted by {ctx.author} ({ctx.author.id})")

                    counter += 1

        elif action == "1 Day Mute":
            for m in toYeet:
                timeoutTd = timedelta(days=1)
                if m.timed_out:
                    timeLeft = m.communication_disabled_until-utcnow()
                    timeoutTd += timeLeft
                    if timeoutTd > timedelta(days=28):
                        timeoutTd = timedelta(days=28)

                with suppress(HTTPException):
                    await m.timeout_for(duration=timeoutTd, reason=f"{reason} - Muted by {ctx.author} ({ctx.author.id})")

                    counter += 1

        elif action == "1 Week Mute":
            for m in toYeet:
                timeoutTd = timedelta(weeks=1)
                if m.timed_out:
                    timeLeft = m.communication_disabled_until-utcnow()
                    timeoutTd += timeLeft
                    if timeoutTd > timedelta(days=28):
                        timeoutTd = timedelta(days=28)

                with suppress(HTTPException):
                    await m.timeout_for(duration=timeoutTd, reason=f"{reason} - Muted by {ctx.author} ({ctx.author.id})")

                    counter += 1

        embed = Embed(title="*Purge Successful*",
                      color=Colors.dark_red())

        if action == "Ban Members":
            embed.description = f"**{counter} members** were banned."

        elif action == "Kick Members":
            embed.description = f"**{counter} members** were kicked."

        elif action == "1 Hour Mute":
            embed.description = f"**{counter} members** were muted until <t:{int((utcnow()+timedelta(hours=1)).timestamp())}:F>."

        elif action == "1 Day Mute":
            embed.description = f"**{counter} members** were muted until <t:{int((utcnow()+timedelta(days=1)).timestamp())}:F>."

        elif action == "1 Week Mute":
            embed.description = f"**{counter} members** were muted until <t:{int((utcnow()+timedelta(weeks=1)).timestamp())}:F>."

        if pattern:
            embed.add_field(
                name="Regex", value=f"```\n{regex}\n```", inline=False)
        if threshold:
            embed.add_field(
                name="Joined after", value=f"<t:{int(threshold.timestamp())}:f>", inline=False)

        await ctx.edit(content=None, embed=embed, view=None)


def setup(bot):
    bot.add_cog(Jschlatt(bot))
