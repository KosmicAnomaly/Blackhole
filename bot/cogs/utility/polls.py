import uuid

from discord import ApplicationContext, Embed, Interaction
from discord.commands import Option, slash_command
from discord.ext.commands import (BucketType, bot_has_permissions, cooldown,
                                  guild_only, has_permissions)
from discord.ui import Select, View
from tools.bot import Anomaly
from tools.cog import Cog
from tools.colors import Colors


class PollDropdown(Select):
    def __init__(self, uuid: uuid.uuid1, options: list, max_choices: int):
        self.id = uuid
        self.options = options
        self.max_choices = max_choices

        counter = 1
        for option in options:
            self.add_option(label=option, value=counter, default=False)
            counter += 1

        super().__init__(
            placeholder="Vote!",
            min_values=0,
            max_values=max_choices
        )


class PollView(View):
    def __init__(self, uuid: uuid.uuid1, options: list, max_choices: int):
        self.id = uuid
        self.options = options
        self.max_choices = max_choices

        super().__init__()
        self.add_item(PollDropdown(options, max_choices))
        self.stop()


class Polls(Cog, name="Polls"):
    """Command to create polls for members to vote on"""

    def __init__(self, bot: Anomaly):
        super().__init__(bot)
        self.views_added = False

    @Cog.listener()
    async def on_ready(self):
        if not self.views_added:

            statement = """
            SELECT view_custom_id, guild_id, channel_id, message_id, topic, max_choices, option_1, option_2, option_3, option_4, option_5
            FROM Polls;
            """
            polls = self.bot.database.execute(statement, count=-1) or []

            for poll in polls:
                guild = self.bot.get_guild(poll[1])
                if not guild:
                    continue

                options = [i[:30] for i in polls[6:]]

                providedOptions = [i for i in options if len(i)]
                view = PollView(
                    uuid=poll[0], options=providedOptions, max_choices=poll[5])
                self.bot.add_view(view, message_id=poll[3])

            self.views_added = True

    @slash_command(name="poll")
    @cooldown(3, 60, BucketType.member)
    @bot_has_permissions(send_messages=True, view_channel=True)
    @has_permissions(manage_messages=True)
    @guild_only()
    async def poll(
        self,
        ctx: ApplicationContext,
        topic: Option(str, "Topic of the poll (up to 100 characters)", required=True),
        max_choices: Option(int, "How many choices members can vote for at once", choices=[1, 2, 3, 4], required=True),
        option_1: Option(str, "Option 1 (up to 50 characters)", required=True),
        option_2: Option(str, "Option 2 (up to 50 characters)", required=True),
        option_3: Option(str, "Option 3 (up to 50 characters)", required=False, default=""),
        option_4: Option(str, "Option 4 (up to 50 characters)", required=False, default=""),
        option_5: Option(str, "Option 5 (up to 50 characters)",
                         required=False, default="")
    ):
        """Create a poll for members to vote on"""

        await ctx.defer(ephemeral=True)

        topic = topic[:100]

        options = [i[:30]
                   for i in [option_1, option_2, option_3, option_4, option_5]]

        providedOptions = [i for i in options if len(i)]

        max_choices = max(
            1, min(len(providedOptions), max_choices))

        embed = Embed(title=topic, color=Colors.lavender())
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url)

        id = uuid.uuid1()
        view = PollView(uuid=id, options=providedOptions,
                        max_choices=max_choices)

        msg = await ctx.channel.send(embed=embed, view=view)
        await ctx.respond("Poll created!", ephemeral=True)

        statement = """
        INSERT INTO Polls
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        self.bot.database.execute(
            statement, (id, ctx.guild.id, ctx.channel.id, msg.id, max_choices, topic, *options))

    @ Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if not interaction.is_component():
            return
        if not interaction.guild:
            return

        message = interaction.message
        if message.author != interaction.guild.me:
            return

        statement = """
        SELECT * FROM Polls
        WHERE message_id = %s;
        """
        data = self.bot.database.execute(statement, (message.id,), 1)

        if not data:
            return

        if message.flags.suppress_embeds:
            statement = """
            DELETE FROM Polls
            WHERE message_id = %s;
            """
            self.bot.database.execute(statement, (message.id,))

            await message.delete()
            return

        options = [i for i in data[4:8] if i]

        chosenOptions = interaction.data["values"]
        response = interaction.response
        member = interaction.user

        # update votes
        statement = """
        DELETE FROM PollVotes
        WHERE message_id = %s AND member_id = %s;
        """
        self.bot.database.execute(statement, (message.id, member.id))

        statement = """
        INSERT INTO PollVotes
        VALUES (%s, %s, %s);
        """

        for i in chosenOptions:
            self.bot.database.execute(
                statement, (message.id, member.id, int(i)))

        statement = """
        SELECT option, COUNT(*) FROM PollVotes
        WHERE message_id = %s
        GROUP BY option
        ORDER BY option ASC;
        """

        voteCounts = self.bot.database.execute(
            statement, (message.id,), count=-1)

        statement = """
        SELECT COUNT(*) FROM PollVotes
        WHERE message_id = %s;
        """

        totalVotes = self.bot.database.execute(
            statement, (message.id,), 1) or 0

        embed = Embed(title=data[3], color=Colors.lavender())

        for i in voteCounts:
            if not totalVotes:
                percentage = 0
            else:
                percentage = round(100 * i[1] / totalVotes, 1)
            embed.add_field(
                name=options[i[0]], value=f"{i[1]} Votes ({percentage}%)", inline=False)

        embed.set_footer(text=f"{totalVotes} Total Votes")
        await message.edit(embed=embed)

        await response.send_message("Your vote has been counted!", ephemeral=True)


def setup(bot):
    bot.add_cog(Polls(bot))
