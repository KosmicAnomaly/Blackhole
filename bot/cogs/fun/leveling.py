import math
from contextlib import suppress
from datetime import datetime
from math import ceil as round_up
from random import randint

from discord import (ApplicationContext, Embed, Guild, HTTPException, Member,
                     Message)
from discord.commands import Option, SlashCommandGroup, user_command
from discord.ext.commands import (BucketType, cooldown, guild_only,
                                  has_guild_permissions)
from tools.bot import Anomaly
from tools.cog import Cog
from tools.colors import Colors
from tools.tools import CustomPaginator, make_progress_bar


def get_xp(level: int):
    return math.floor(2*(level**3)+200*level)


def get_level(xp: int):
    level = 0
    while get_xp(level) <= xp:
        level += 1
    return level - 1


def level_embed(member: Member, level: int, xp: int):
    xpStart = get_xp(level)
    xpEnd = get_xp(level+1)

    embed = Embed(
        title=f"Level {level}", description=member.mention, color=Colors.better_neon_green())
    embed.set_thumbnail(url=member.display_avatar.url)

    # make a cool progress bar
    progressBar = make_progress_bar(
        percent=(xp - xpStart) / (xpEnd - xpStart), length=15)

    embed.add_field(name=f"{xp} Experience"[:256],
                    value=f"{progressBar}\n{xpEnd-xp} Experience remaining to level up"[:1024], inline=True)

    return embed


class Leveling(Cog, name="Leveling"):
    """Leveling module"""

    def __init__(self, bot: Anomaly):
        super().__init__(bot)
        self.leveling_cooldowns = {}

    def handle_cooldown(self, guild: Guild, member: Member, dt: datetime):
        """Handles the 1-minute leveling cooldown"""
        guildCooldowns = self.leveling_cooldowns.get(guild.id)
        if not guildCooldowns:
            self.leveling_cooldowns[guild.id] = {member.id: dt}
            return True
        oldDT = guildCooldowns.get(member.id)
        if not oldDT:
            self.leveling_cooldowns[guild.id][member.id] = dt
            return True
        if (dt-oldDT).total_seconds() < 60:
            return False
        self.leveling_cooldowns[guild.id][member.id] = dt
        return True

    RootGroup = SlashCommandGroup(
        "lvl", "Commands related to the Leveling module")

    MemberGroup = RootGroup.create_subgroup(
        "member", "Manage the levels of other server members")

    @MemberGroup.command(name="reset")
    @cooldown(1, 2, BucketType.member)
    @has_guild_permissions(administrator=True)
    @guild_only()
    async def reset_member_level(self, ctx: ApplicationContext, member: Option(Member, "Member to reset", required=True)):
        """Reset a member's level"""

        await ctx.defer(ephemeral=True)

        statement = """
        SELECT enabled FROM LevelingSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (ctx.guild.id,), 1)

        if not settings or not settings[0]:
            await ctx.respond("The Leveling module is disabled!", ephemeral=True)
            return

        statement = """
        DELETE FROM MemberExperience
        WHERE guild_id = %s AND member_id = %s;
        """

        self.bot.database.execute(statement, (ctx.guild.id, member.id))

        await ctx.edit(content=f"{member.mention}'s level has been reset!", view=None)

    @MemberGroup.command(name="set")
    @cooldown(1, 2, BucketType.member)
    @has_guild_permissions(administrator=True)
    @guild_only()
    async def set_member_level(self, ctx: ApplicationContext, member: Option(Member, "Member to edit", required=True), level: Option(int, "New level", min_value=0, max_value=200, required=True)):
        """Change a member's level"""

        await ctx.defer(ephemeral=True)

        statement = """
        SELECT enabled FROM LevelingSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (ctx.guild.id,), 1)

        if not settings or not settings[0]:
            await ctx.respond("The Leveling module is disabled!", ephemeral=True)
            return

        xp = get_xp(level)

        statement = """
        INSERT INTO MemberExperience(guild_id, member_id, experience, level)
        VALUES (%s, %s, %s, %s)  ON CONFLICT (guild_id, member_id) DO UPDATE
            SET experience = %s,
            level = %s;
        """
        self.bot.database.execute(
            statement, (ctx.guild.id, member.id, xp, level, xp, level))

        await ctx.edit(content=f"{member.mention}'s level has been updated to **Level {level}!**", view=None)

    @RootGroup.command(name="check")
    @cooldown(3, 15, BucketType.member)
    @guild_only()
    async def check_level(self, ctx: ApplicationContext, member: Option(Member, "Server member", required=False, default=None)):
        """Check the level of a member"""

        await ctx.defer(ephemeral=True)

        member = member or ctx.author

        if member.bot:
            await ctx.respond("It's over 9000!", ephemeral=True)

        statement = """
        SELECT enabled FROM LevelingSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (ctx.guild.id,), 1)

        if not settings or not settings[0]:
            await ctx.respond("The Leveling module is disabled!", ephemeral=True)
            return

        statement = """
        SELECT FROM MemberExperience VALUES (experience, level)
        WHERE guild_id = %s AND member_id = %s;
        """
        data = self.bot.database.execute(
            statement, (ctx.guild.id, member.id), 1) or (0, 0)

        embed = level_embed(member, data[1], data[0])

        await ctx.respond(embed=embed, ephemeral=True)

    @user_command(name="View Level")
    @cooldown(3, 15, BucketType.member)
    @guild_only()
    async def view_level_menu(self, ctx: ApplicationContext, user: Member):
        """Check the level of a member"""

        await ctx.defer(ephemeral=True)

        if user.bot:
            await ctx.respond("It's over 9000!", ephemeral=True)

        statement = """
        SELECT enabled FROM LevelingSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (ctx.guild.id,), 1)

        if not settings or not settings[0]:
            await ctx.respond("The Leveling module is disabled!", ephemeral=True)
            return

        statement = """
        SELECT FROM MemberExperience VALUES (experience, level)
        WHERE guild_id = %s AND member_id = %s;
        """
        data = self.bot.database.execute(
            statement, (ctx.guild.id, user.id), 1) or (0, 0)

        embed = level_embed(user, data[1], data[0])

        await ctx.respond(embed=embed, ephemeral=True)

    @RootGroup.command(name="leaderboard")
    @cooldown(1, 30, BucketType.member)
    @guild_only()
    async def leaderboard(self, ctx: ApplicationContext):
        """View the server's leveling leaderboard"""

        await ctx.defer(ephemeral=True)

        statement = """
        SELECT enabled FROM LevelingSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (ctx.guild.id,), 1)

        if not settings or not settings[0]:
            await ctx.respond("The Leveling module is disabled!", ephemeral=True)
            return

        statement = """
        SELECT member_id, experience, level FROM MemberExperience
        WHERE guild_id = %s
        ORDER BY level DESC, experience DESC, member_id ASC
        LIMIT 120; 
        """

        memberLevels = self.bot.database.execute(
            statement, (ctx.guild.id,), count=-1)

        embeds = []
        fieldCounter = 0
        position = 1
        baseEmbed = Embed(title="Leveling Leaderboard",
                          color=Colors.better_neon_green())

        embed = baseEmbed.copy()
        for thisMember in memberLevels:
            memberObject = ctx.guild.get_member(thisMember[0])
            if memberObject:
                name = memberObject.mention

                embed.add_field(name=f"Position #{position}",
                                value=f"{name}\n```Level {thisMember[2]}\n{thisMember[1]} Experience```", inline=True)
                fieldCounter += 1
                position += 1

            if fieldCounter == 12:
                fieldCounter = 0
                embeds.append(embed)
                embed = baseEmbed.copy()

        if embed not in embeds:
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.respond(embed=embeds[0], ephemeral=True)
            return

        paginator = CustomPaginator(pages=embeds)

        await paginator.respond(ctx.interaction, ephemeral=True)

    @Cog.listener()
    async def on_message(self, message: Message):

        if message.author.bot:
            return
        elif not message.guild:
            return
        elif not message.content:
            return
        elif len(message.content) < 2:
            return

        guild = message.guild
        channel = message.channel

        if not self.handle_cooldown(message.guild, message.author, message.created_at):
            return

        statement = """
        SELECT enabled, multiplier, stack_roles, blacklisted_role_id, announce FROM LevelingSettings
        WHERE guild_id = %s;
        """

        settings = self.bot.database.execute(statement, (guild.id,), 1)

        if not settings or not settings[0]:
            return

        if settings[3] in [r.id for r in message.author.roles]:
            return

        statement = """
        SELECT FROM MemberExperience VALUES (experience, level)
        WHERE guild_id = %s AND member_id = %s;
        """
        data = self.bot.database.execute(
            statement, (guild.id, message.author.id), 1) or (0, 0)

        # random xp gain
        gain = randint(15, 25) * settings[1]
        newXP = round_up(gain + data[0])

        # calculate what level the member needs to be at
        newLevel = get_level(newXP)

        # level up if the new level is different from the old level
        if newLevel > data[1]:
            data[1] = newLevel
            if settings[4]:
                with suppress(HTTPException):
                    await message.channel.send(f"{message.author.mention} has leveled up to level **{newLevel}**!")

        # add leveling reward roles
        if message.guild.me.guild_permissions.manage_roles:

            statement = """
            SELECT role_id, required_level FROM LevelingRoles
            WHERE guild_id = %s
            ORDER BY required_level ASC;
            """

            levelingRoles = self.bot.database.execute(
                statement, (guild.id,), count=-1)

            useableRoles = []
            for thisRole in levelingRoles:
                roleObj = message.guild.get_role(thisRole[0])
                if roleObj and roleObj.is_assignable():
                    useableRoles.append((roleObj, thisRole[1]))

            earnedRoles = [i[0] for i in useableRoles if i[1] <= data[1]]
            if settings[2] and len(earnedRoles):
                with suppress(HTTPException):
                    await message.author.add_roles(*earnedRoles, reason="Adding Leveling Reward Roles")

            else:
                await message.author.remove_roles(*[i[0] for i in useableRoles], reason="Removing old Leveling Reward Roles")
                if len(earnedRoles):
                    with suppress(HTTPException):
                        await message.author.add_roles(earnedRoles[-1], reason=f"Adding Leveling Reward Role")

        statement = """
        INSERT INTO MemberExperience(guild_id, member_id, experience, level)
        VALUES (%s, %s, %s, %s) ON CONFLICT (guild_id, member_id) 
            DO UPDATE
                SET experience = %s,
                level = %s;
        """
        self.bot.database.execute(
            statement, (guild.id, message.author.id, newXP, newLevel, newXP, newLevel))


def setup(bot):
    bot.add_cog(Leveling(bot))
