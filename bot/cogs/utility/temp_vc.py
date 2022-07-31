from discord import HTTPException, Member, VoiceState
from discord.ext.tasks import loop
from tools.bot import Anomaly
from tools.cog import Cog
from datetime import time,timezone

class TempVC(Cog, name="Temp VC"):
    """TempVC module"""

    def __init__(self, bot: Anomaly):
        super().__init__(bot)
        self.manual_remove.start()

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        """Create or delete Voice Channels as needed"""

        guild = member.guild

        if not guild:
            return
        if member.bot:
            return

        statement = """
        SELECT enabled, channel_id FROM TempVCSettings WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (guild.id,), 1)

        if not settings or not settings[0]:
            return

        # if the user is joining the temp vc channel
        after = after.channel
        if after and after.id == settings[1]:
            # make sure we can move them
            afterCategory = after.category
            perms = afterCategory.permissions_for(guild.me)
            if (perms.move_members) and (perms.manage_channels) and (member.top_role < guild.me.top_role):

                newVC = await guild.create_voice_channel(name=f"{member.name[:20]}'s VC", category=afterCategory, reason="Member joined the TempVC channel")
                await member.move_to(newVC, reason="Member joined the TempVC channel")

                statement = """
                    INSERT INTO TempVCChannels(guild_id, channel_id)
                    VALUES (%s, %s);
                    """

                self.bot.database.execute(statement, (guild.id, newVC.id))

        # if the user is leaving the temp vc channel, and the channel is now empty
        before = before.channel
        if before and not len([m for m in before.members if not m.bot]):
            if before.permissions_for(guild.me).manage_channels:

                # check if it is a temp vc channel
                statement = """
                SELECT channel_id FROM TempVCChannels
                WHERE guild_id = %s AND channel_id = %s;
                """

                maybeExists = self.bot.database.execute(
                    statement, (guild.id, before.id), 1)

                if maybeExists:
                    try:
                        await before.delete(reason="This channel was created by the TempVC module and is now empty")
                    except HTTPException:
                        pass
                    else:
                        statement = """
                        DELETE FROM TempVCChannels
                        WHERE channel_id = %s;
                        """
                        self.bot.database.execute(statement, (before.id,))

    def cog_unload(self):
        self.manual_remove.cancel()

    # Manually delete empty TempVC channels every 24 hours in case one was missed
    @loop(
        time=time(12, 0, tzinfo=timezone.utc)
    )
    async def manual_remove(self):

        statement = """
        SELECT channel_id FROM TempVCChannels
        """
        channels = self.bot.database.execute(statement, count=-1) or []

        for channel in channels:
            c = await self.bot.get_or_fetch_channel(channel[0])
            if not c:
                statement = """
                DELETE FROM TempVCChannels
                WHERE channel_id = %s;
                """
                self.bot.database.execute(statement)

            elif not len([m for m in c.members if not m.bot]):
                try:
                    await c.delete(reason="This channel was created as a Temporary Voice Channel and is now empty")
                except HTTPException:
                    pass
                else:
                    statement = """
                        DELETE FROM TempVCChannels
                        WHERE channel_id = %s;
                        """
                    self.bot.database.execute(statement, (c.id,))

    @manual_remove.before_loop
    async def before_manual_remove(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(TempVC(bot))
