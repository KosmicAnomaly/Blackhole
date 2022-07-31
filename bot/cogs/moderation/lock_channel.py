from contextlib import suppress
from discord import ApplicationContext, Embed
from discord.commands import slash_command
from discord.ext.commands import (BucketType, bot_has_permissions, cooldown,
                                  guild_only, has_permissions)
from tools.cog import Cog
from tools.colors import Colors


class ChannelLock(Cog, name="Lock Channel"):
    """Commands to lock and unlock Text Channels"""

    @slash_command(name="shut")
    @cooldown(1, 5, BucketType.member)
    @bot_has_permissions(manage_channels=True, send_messages=True)
    @has_permissions(manage_channels=True)
    @guild_only()
    async def lock(self, ctx: ApplicationContext):
        """Stop messages from being sent in a Text Channel"""

        await ctx.defer()

        perms = ctx.channel.overwrites_for(ctx.guild.default_role)
        perms.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=perms, reason=f"{ctx.author} ({ctx.author.id}) locked the channel")

        embed = Embed(color=Colors.red())

        embed.set_image(
            url="https://cdn.discordapp.com/emojis/939633440926629908.png?quality=lossless")

        embed.set_footer(text=f"Channel locked by {ctx.author}",
                         icon_url="https://images.emojiterra.com/twitter/v13.1/512px/1f512.png")

        await ctx.respond(embed=embed)

    @slash_command(name="unshut")
    @cooldown(1, 5, BucketType.member)
    @bot_has_permissions(manage_channels=True)
    @has_permissions(manage_channels=True)
    @guild_only()
    async def unlock(self, ctx: ApplicationContext):
        """Unlock a Text Channel that has been locked"""

        await ctx.defer()

        perms = ctx.channel.overwrites_for(ctx.guild.default_role)
        perms.send_messages = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=perms, reason=f"{ctx.author} ({ctx.author.id}) unlocked the channel")

        embed = Embed(color=Colors.better_green())

        embed.set_image(
            url="https://cdn.discordapp.com/emojis/939633451051651113.png?quality=lossless")

        embed.set_footer(text=f"Channel unlocked by {ctx.author}",
                         icon_url="https://images.emojiterra.com/twitter/v13.1/512px/1f513.png")

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(ChannelLock(bot))
