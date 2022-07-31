from discord import ApplicationContext, Embed, Member
from discord.commands import Option, slash_command
from discord.ext.commands import (bot_has_guild_permissions, guild_only,
                                  has_guild_permissions)
from tools.cog import Cog
from tools.colors import Colors


class PermaYeet(Cog, name="Permayeet"):
    """Commands to kick and ban members"""

    @slash_command(name="yeet")
    @bot_has_guild_permissions(kick_members=True)
    @has_guild_permissions(kick_members=True)
    @guild_only()
    async def kick_member(self, ctx: ApplicationContext, member: Option(Member, "Member to kick", required=True), reason: Option(str, "Reason for the kick", required=False, default="No reason provided")):
        """Kick a member from the server"""

        await ctx.defer()

        if member.id == ctx.me.id:
            await ctx.respond("🤨", ephemeral=True)
            return

        if member.id == ctx.author.id:
            await ctx.respond("hmm", ephemeral=True)
            return

        if member.id == ctx.guild.owner.id:
            await ctx.respond("...you know that's the owner, right?", ephemeral=True)
            return

        if ctx.me.top_role <= member.top_role:
            await ctx.respond(f"I am not able to kick {member.mention}!", ephemeral=True)
            return

        if ctx.author.top_role <= member.top_role:
            await ctx.respond(f"You are not able to kick {member.mention}!", ephemeral=True)
            return

        try:
            await member.kick(reason=f"{reason} - Kicked by {ctx.author} ({ctx.author.id})")

        except:
            await ctx.respond(f"I was not able to kick {member.mention}!", ephemeral=True)
        else:
            embed = Embed(title=f"{member} has been kicked",
                          color=Colors.red())
            embed.add_field(name="Reason", value=f"```\n{reason}\n```")
            embed.set_footer(text=f"Kicked by {ctx.author}")
            await ctx.respond(embed=embed)

    @slash_command(name="permayeet")
    @bot_has_guild_permissions(ban_members=True)
    @has_guild_permissions(ban_members=True)
    @guild_only()
    async def ban_member(self, ctx: ApplicationContext, member: Option(Member, "Member to ban", required=True), reason: Option(str, "Reason for the ban", required=False, default="No reason provided")):
        """Ban a member from the server"""

        await ctx.defer()

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
            await ctx.respond(f"I am not able to ban {member.mention}!", ephemeral=True)
            return

        if ctx.author.top_role <= member.top_role:
            await ctx.respond(f"You are not able to ban {member.mention}!", ephemeral=True)
            return

        try:
            await member.ban(reason=f"{reason} - Banned by {ctx.author} ({ctx.author.id})")

        except:
            await ctx.respond(f"I was not able to ban {member.mention}!", ephemeral=True)
        else:
            embed = Embed(title=f"{member} has been banned",
                          color=Colors.dark_red())
            embed.add_field(name="Reason", value=f"```\n{reason}\n```")
            embed.set_footer(text=f"Banned by {ctx.author}")

            embed.set_author(name="The Ban Hammer has fallen",
                             icon_url="https://cdn.discordapp.com/emojis/930976896995459123.png?quality=lossless")

            embed.set_image(
                url="https://c.tenor.com/heCqAK_FUpYAAAAC/cosmic-ban.gif")

            await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(PermaYeet(bot))
