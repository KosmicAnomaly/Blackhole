from datetime import timedelta

from discord import ApplicationContext, Embed, Member
from discord.commands import Option, slash_command
from discord.ext.commands import (bot_has_guild_permissions, guild_only,
                                  has_guild_permissions)
from discord.utils import utcnow
from pytimeparse import parse
from tools.cog import Cog
from tools.colors import Colors

class Timeout(Cog, name="Timeout"):
    """Commands to mute and unmute server members"""

    @slash_command(name="mute")
    @bot_has_guild_permissions(moderate_members=True)
    @has_guild_permissions(moderate_members=True)
    @guild_only()
    async def timeout_command(self, ctx: ApplicationContext, member: Option(Member, "Member to mute", required=True), duration: Option(str, "Duration to mute this member (Default 1hr)", required=False, default="1 hour"), reason: Option(str, "Reason for the mute", required=False, default="No reason provided")):
        """Mute a member"""

        await ctx.defer(ephemeral=True)

        if member.id == ctx.me.id:
            await ctx.respond("🤨", ephemeral=True)
            return

        if member.id == ctx.author.id:
            await ctx.respond("...you know `/sleep` exists for that, right?", ephemeral=True)
            return

        if member.id == ctx.guild.owner.id:
            await ctx.respond("...you know that's the owner, right?", ephemeral=True)
            return

        if ctx.me.top_role <= member.top_role:
            await ctx.respond(f"I am not able to mute {member.mention}!", ephemeral=True)
            return

        if ctx.author.top_role <= member.top_role:
            await ctx.respond(f"You are not able to mute {member.mention}!", ephemeral=True)
            return

        seconds = parse(duration)
        if seconds is None:
            await ctx.respond("I don't understand that duration format!", ephemeral=True)
            return

        timeoutTd = timedelta(seconds=seconds)

        if timeoutTd < timedelta(minutes=1):
            await ctx.respond("The minimum mute duration is 1 minute!", ephemeral=True)
            return
        elif timeoutTd > timedelta(days=28):
            await ctx.respond("The maximum mute duration is 28 days!", ephemeral=True)
            return

        if member.timed_out:
            alreadyTimedOut = True
            timeLeft = member.communication_disabled_until-utcnow()
            timeoutTd += timeLeft
            if timeoutTd > timedelta(days=28):
                timeoutTd = timedelta(days=28)
        else:
            alreadyTimedOut = False

        try:
            await member.timeout_for(duration=timeoutTd, reason=f"{reason} - Muted by {ctx.author} ({ctx.author.id})")

        except:
            await ctx.respond(f"I was not able to mute {member.mention}!", ephemeral=True)
        else:
            unmuteDT = utcnow()+timeoutTd
            timeFormat = f"<t:{int(unmuteDT.timestamp())}:F>"
            if alreadyTimedOut:
                embed = Embed(title=f"{member}'s timeout has been extended",
                              description=f"{member.mention} will be muted until {timeFormat}", color=Colors.red())
            else:
                embed = Embed(title=f"{member} has been muted",
                              description=f"{member.mention} will be muted until {timeFormat}", color=Colors.red())

            await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(name="unmute")
    @bot_has_guild_permissions(moderate_members=True)
    @has_guild_permissions(moderate_members=True)
    @guild_only()
    async def remove_timeout(self, ctx: ApplicationContext, member: Option(Member, "Member to unmute", required=True), reason: Option(str, "Reason for the unmute", required=False, default="No reason provided")):
        """Unmute a member"""

        await ctx.defer(ephemeral=True)

        if member.id == ctx.me.id:
            await ctx.respond("🤨", ephemeral=True)
            return

        if member.id == ctx.guild.owner.id:
            await ctx.respond("...you know that's the owner, right?", ephemeral=True)
            return

        if member.id == ctx.author.id:
            await ctx.respond("hmm", ephemeral=True)
            return

        if ctx.me.top_role <= member.top_role:
            await ctx.respond(f"I am not able to unmute {member.mention}!", ephemeral=True)
            return

        if ctx.author.top_role <= member.top_role:
            await ctx.respond(f"You are not able to unmute {member.mention}!", ephemeral=True)
            return

        if member.timed_out is False:
            await ctx.respond(f"{member.mention} is not muted!", ephemeral=True)
            return

        try:
            await member.remove_timeout(reason=f"{reason} - Unmuted by {ctx.author} ({ctx.author.id})")
            await ctx.respond("Done!", ephemeral=True)
        except:
            await ctx.respond(f"I was not able to unmute {member.mention}!", ephemeral=True)


def setup(bot):
    bot.add_cog(Timeout(bot))
