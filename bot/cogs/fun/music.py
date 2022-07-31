import json
from contextlib import suppress
from datetime import timedelta
from math import ceil
from random import shuffle
from typing import Type
import lavalink
from discord import (
    ApplicationContext,
    Embed,
    Guild,
    HTTPException,
    Interaction,
    Member,
    SelectOption,
    VoiceChannel,
    VoiceState,
    Bot,
)
from discord.commands import Option, SlashCommandGroup
from discord.ext.commands import BucketType, cooldown, guild_only
from discord.ui import Select, View
from discord.utils import utcnow
from utilities.cog import Cog
from tools.tools import CustomPaginator, make_progress_bar


class SongSelector(Select):
    def __init__(self, songs: list):
        self.songs = songs
        options = []
        index = 0
        for song in self.songs:
            options.append(
                SelectOption(label=song[0], description=song[1], value=index)
            )
            index += 1

        super().__init__(
            placeholder="Which song do you want to queue?",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction):
        self.view.chosenSong = int(self.values[0])
        self.view.stop()


class SongSelectorView(View):
    def __init__(self, songs: list):
        super().__init__()
        self.chosenSong = None
        self.add_item(SongSelector(songs))


class Player(lavalink.DefaultPlayer):
    def __init__(
        self,
        guild_id: int,
        node: lavalink.Node,
        dj_id: int = None,
        text_channel_id: int = None,
    ):
        super().__init__(guild_id, node)
        self.dj_id = dj_id
        self.text_channel_id = text_channel_id
        self.skip_votes = set()
        self.pause_votes = set()
        self.resume_votes = set()
        self.shuffle_votes = set()
        self.restart_votes = set()

    def is_dj(self, member: Member):
        if not self.dj_id:
            self.dj_id = member.id
            return True
        if member.guild.owner.id == member.id:
            return True
        if self.dj_id == member.id:
            return True
        channel = member.guild.get_channel(self.channel_id)
        if channel:
            if channel.permissions_for(member).move_members:
                return True
            if len(channel.members) <= 1:
                return True
        return False

    async def reset(self):
        """Used for cleaning up the player and getting it ready for the next music session"""
        self.channel_id = None
        self.queue.clear()
        await self.clear_filters()
        await self.stop()

    def shuffle_better(self):
        shuffleThese = self.queue[3:]
        shuffle(shuffleThese)
        self.queue = self.queue[:3].extend(shuffleThese)

    def set_votes(self):
        self.skip_votes = set()
        self.pause_votes = set()
        self.resume_votes = set()
        self.shuffle_votes = set()
        self.restart_votes = set()


class Music(Cog, name="Music"):
    """Music module"""

    def __init__(self, bot: Type[Bot]) -> None:
        super().__init__(bot)
        loop = self.bot.loop
        loop.create_task(self.setup_lavalink())

    async def setup_lavalink(self):
        await self.bot.wait_until_ready()

        if not hasattr(self.bot, "lavalink"):
            self.bot.lavalink = lavalink.Client(user_id=self.bot.user.id, player=Player)

            nodes = [
                {"Region": "us", "Name": "US-1"},
                {"Region": "us", "Name": "US-2"},
                {"Region": "hongkong", "Name": "HK-1"},
                {"Region": "japan", "Name": "J-1"},
                {"Region": "eu", "Name": "EU-1"},
                {"Region": "london", "Name": "L-1"},
            ]

            for node in nodes:
                self.bot.lavalink.add_node(
                    host="lavalink",
                    port=2333,
                    password="groovy",
                    region=node["Region"],
                    name=node["Name"],
                )

        self.bot.lavalink.add_event_hooks(self)

    RootGroup = SlashCommandGroup("m", "Commands related to playing music")

    def cog_unload(self):
        """Remove any event hooks that were registered"""
        self.bot.lavalink._event_hooks.clear()

    def create_player(self, guild: Guild):
        return self.bot.lavalink.player_manager.create(
            guild.id, endpoint=str(guild.region)
        )

    def majority_vote(self, channel: VoiceChannel):
        majority = 0.4
        count = len([m for m in channel.members if not m.bot])
        if count == 2:
            return 2
        return ceil(majority * count)

    async def ensure_voice(self, ctx):
        player = self.create_player(ctx.guild)
        if not player.is_connected:
            await player.reset()
            await ctx.guild.change_voice_state(channel=None)
            await ctx.respond(
                f"I am not connected to a Voice Channel!\n...At least...I don't think I am... *has existential crisis*",
                ephemeral=True,
            )
            return
        return player

    @Cog.listener()
    async def on_socket_raw_receive(self, msg):
        data = json.loads(msg)

        if not data or "t" not in data:
            return

        if data["t"] == "VOICE_SERVER_UPDATE":
            guild_id = int(data["d"]["guild_id"])
            player = self.bot.lavalink.player_manager.get(guild_id)

            if player:
                await player._voice_server_update(data["d"])

        elif data["t"] == "VOICE_STATE_UPDATE":
            if int(data["d"]["user_id"]) != int(self.bot.user.id):
                return

            guild_id = int(data["d"]["guild_id"])
            player = self.bot.lavalink.player_manager.get(guild_id)

            if player:
                await player._voice_state_update(data["d"])

    @lavalink.listener(lavalink.events.TrackStuckEvent)
    async def on_track_stuck(self, event: lavalink.events.TrackStuckEvent):
        await event.player.skip()

    @lavalink.listener(lavalink.events.TrackExceptionEvent)
    async def on_track_error(self, event: lavalink.events.TrackExceptionEvent):
        await event.player.skip()

    @lavalink.listener(lavalink.events.TrackStartEvent)
    async def on_track_start(self, event: lavalink.events.TrackStartEvent):
        player = event.player
        track = event.track
        player.set_votes()
        if player.text_channel_id:
            channel = self.bot.get_channel(player.text_channel_id)
            if channel:
                requester = await self.bot.get_or_fetch_user(track.requester)
                if requester:
                    icon = requester.avatar.url
                else:
                    requester = track.requester
                    icon = Embed.Empty

                embed = Embed(
                    title=f"{track.author} - *{track.title}*",
                    url=track.uri,
                    color=0xFF0000,
                )
                formatted = lavalink.format_time(track.duration)
                if formatted.startswith("00:"):
                    formatted = formatted[3:]
                embed.add_field(name="Duration", value=f"`{formatted}`")
                embed.set_author(name="Now Playing")
                embed.set_footer(text=f"Requested by {requester}", icon_url=icon)

                with suppress(HTTPException):
                    await channel.send(embed=embed)

    @Cog.listener()
    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        guild = member.guild
        player = self.create_player(guild)
        # Handle connection changes
        if member.id == guild.me.id:
            if after.channel:
                if after.channel.id != player.channel_id:
                    player.channel_id = after.channel.id
                    await guild.change_voice_state(
                        channel=after.channel, self_deaf=True
                    )

            else:
                await player.reset()
                if guild.voice_client:
                    await guild.change_voice_state(channel=None)
                    return

        if player.is_connected:
            # reassign the dj if they left
            if (
                after.channel
                and after.channel.id == player.channel_id
                and player.dj_id not in after.channel.members
            ):
                for m in after.channel.members:
                    if (not m) or m.bot:
                        continue
                    else:
                        player.dj_id = m.id
                        return

    @RootGroup.command(name="connect")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def connect(self, ctx: ApplicationContext):
        """Invite Kosmo into your Voice Channel to play Music"""

        player = self.create_player(ctx.guild)

        if player.is_connected:
            channel = ctx.guild.get_channel(player.channel_id)
            if channel:
                await ctx.respond(
                    f"I am already connected to a Voice Channel ({channel.mention})",
                    ephemeral=True,
                )
                return

        destination = getattr(ctx.author.voice, "channel", None)
        if not destination:
            await ctx.respond(
                "You need to be in a Voice Channel first!", ephemeral=True
            )
            return

        elif not isinstance(destination, VoiceChannel):
            await ctx.respond(
                f"I am not able to play music in {destination.mention}!", ephemeral=True
            )
            return

        myPerms = destination.permissions_for(ctx.guild.me)
        if not myPerms.connect:
            await ctx.respond(
                f"I am not allowed to connect to {destination.mention}!", ephemeral=True
            )
            return

        elif not myPerms.speak:
            await ctx.respond(
                f"I am not allowed to speak in {destination.mention}!", ephemeral=True
            )
            return

        if (destination.user_limit <= len(destination.members)) and (
            destination.user_limit > 0
        ):
            await ctx.respond(f"{destination.mention} is full!", ephemeral=True)
            return

        await ctx.guild.change_voice_state(channel=destination, self_deaf=True)
        await player.set_volume(50)
        player.dj_id = ctx.author.id
        player.text_channel_id = ctx.channel.id
        player.channel_id = destination.id
        await ctx.respond(f"Connected to {destination.mention}")

    @RootGroup.command(name="disconnect")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def disconnect(self, ctx: ApplicationContext):
        """Disconnect Kosmo from your Voice Channel"""

        player = self.create_player(ctx.guild)
        if player.channel_id:
            if player.is_dj(ctx.author):
                await ctx.guild.change_voice_state(channel=None)
                await player.reset()
                await ctx.respond("See ya")
                return

            else:
                await ctx.respond(
                    f"Only a Music DJ can use `/{ctx.command.qualified_name}`!",
                    ephemeral=True,
                )
                return

        else:
            await self.ensure_voice(ctx)

    @RootGroup.command(name="play")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def play(
        self,
        ctx: ApplicationContext,
        song: Option(str, "Song to play", required=True),
        service: Option(
            str,
            "Service to search from",
            required=False,
            choices=["Soundcloud", "YouTube", "YouTube Music", "Search by URL"],
            default="YouTube Music",
        ),
    ):
        """Searches for and plays a song from a given query"""

        await ctx.defer(ephemeral=True)

        player = await self.ensure_voice(ctx)
        if not player:
            return

        if service == "Soundcloud":
            song = f"scsearch:{song}"
        elif service == "YouTube":
            song = f"ytsearch:{song}"
        elif service == "YouTube Music":
            song = f"ytmsearch:{song}"

        results = await player.node.get_tracks(song)

        if not results or not results.tracks:
            await ctx.respond("No results!", ephemeral=True)
            return

        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL)
        #   PLAYLIST_LOADED - direct URL to playlist)
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.

        if results.load_type == "SEARCH_RESULT":
            titles = []
            songs = []
            for track in results.tracks[:10]:
                thisTitle = (track.title, track.author)
                if not thisTitle in titles:
                    titles.append(thisTitle)
                    songs.append(track)

            if len(songs) == 1:
                track = songs[0]
            else:
                view = SongSelectorView(titles)
                await ctx.respond("Pick a song to queue!", view=view, ephemeral=True)

                await view.wait()

                if view.chosenSong is None:
                    await ctx.edit(content="No response!", view=None)
                    return
                else:
                    track = songs[view.chosenSong]
                    player.add(requester=ctx.author.id, track=track)
                    await ctx.edit(content="Okay!", view=None)

        elif results.load_type == "TRACK_LOADED":
            track = results.tracks[0]

            player.add(requester=ctx.author.id, track=track)
            await ctx.respond("Okay!", ephemeral=True)

        elif results.load_type == "PLAYLIST_LOADED":
            await ctx.respond("You are not allowed to queue playlists!", ephemeral=True)
            return

        else:
            await ctx.respond(
                "I was not able to play that song, sorry!", ephemeral=True
            )
            return

        if player.is_playing:

            embed = Embed(
                title=f"{track.author} - *{track.title}*",
                url=track.uri,
                color=0xFF0000,
            )
            formatted = lavalink.format_time(track.duration)
            if formatted.startswith("00:"):
                formatted = formatted[3:]
            embed.add_field(name="Duration", value=f"`{formatted}`")
            embed.set_author(name="Added to Queue")
            embed.set_footer(
                text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url
            )

            await ctx.channel.send(embed=embed)

        else:
            await player.play()

    @RootGroup.command(name="nowplaying")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def now_playing(self, ctx: ApplicationContext):
        """Display the currently playing song"""

        player = await self.ensure_voice(ctx)
        if not player:
            return

        track = player.current
        if not track:
            await ctx.respond("No music is currently being played!", ephemeral=True)
            return

        requester = await self.bot.get_or_fetch_user(track.requester)
        if requester:
            icon = requester.avatar.url
        else:
            requester = track.requester
            icon = Embed.Empty

        embed = Embed(
            title=f"{track.author} - *{track.title}*",
            url=track.uri,
            color=0xFF0000,
        )

        if not track.stream:
            position = player.position
            duration = track.duration
            start = lavalink.format_time(position)
            if start.startswith("00:"):
                start = start[3:]
            end = lavalink.format_time(duration)
            if end.startswith("00:"):
                end = end[3:]

            embed.description = f"`{start}` {make_progress_bar(percent=position/duration,length=10)} `{end}`"

        embed.set_author(name="Now Playing")
        embed.set_footer(text=f"Requested by {requester}", icon_url=icon)

        await ctx.respond(embed=embed)

    @RootGroup.command(name="skip")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def skip_song(self, ctx: ApplicationContext):
        """Vote to skip the currently playing song"""

        player = await self.ensure_voice(ctx)
        if not player:
            return

        elif not player.current:
            await ctx.respond("No music is currently being played!", ephemeral=True)
            return

        elif player.is_dj(ctx.author):
            await player.skip()
            await ctx.respond("A DJ has skipped this song")
            return

        elif player.current.requester.id == ctx.author.id:
            await player.skip()
            await ctx.respond("The song requester has skipped this song")
            return
        else:
            player.skip_votes.add(ctx.author.id)
            channel = ctx.guild.get_channel(player.channel_id)
            required = self.majority_vote(channel)

            await ctx.respond(
                f"{ctx.author.mention} has voted to skip this song ({len(player.skip_votes)}/{required})"
            )

            if required >= len(player.skip_votes):
                await player.skip()
                await ctx.channel.send("Song vote-skipped")

    @RootGroup.command(name="pause")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def pause_song(self, ctx: ApplicationContext):
        """Vote to pause the currently playing song"""

        player = await self.ensure_voice(ctx)
        if not player:
            return

        elif not player.current:
            await ctx.respond("No music is currently being played!", ephemeral=True)
            return

        elif player.paused:
            await ctx.respond("This song is already paused!", ephemeral=True)
            return

        elif player.is_dj(ctx.author):
            await player.set_pause(True)
            player.pause_votes = set()
            await ctx.respond("A DJ has paused this song")
            return

        else:
            player.pause_votes.add(ctx.author.id)
            channel = ctx.guild.get_channel(player.channel_id)
            required = self.majority_vote(channel)

            await ctx.respond(
                f"{ctx.author.mention} has voted to pause this song ({len(player.pause_votes)}/{required})"
            )

            if required >= len(player.pause_votes):
                await player.set_pause(True)
                player.pause_votes = set()
                await ctx.channel.send("Song vote-paused")

    @RootGroup.command(name="resume")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def resume_song(self, ctx: ApplicationContext):
        """Vote to resume a paused song"""

        player = await self.ensure_voice(ctx)
        if not player:
            return

        elif not player.current:
            await ctx.respond("No music is currently being played!", ephemeral=True)
            return

        elif not player.paused:
            await ctx.respond("This song is not paused!", ephemeral=True)
            return

        elif player.is_dj(ctx.author):
            await player.set_pause(False)
            player.resume_votes = set()
            await ctx.respond("A DJ has resumed this song")
            return

        else:
            player.resume_votes.add(ctx.author.id)
            channel = ctx.guild.get_channel(player.channel_id)
            required = self.majority_vote(channel)

            await ctx.respond(
                f"{ctx.author.mention} has voted to resume this song ({len(player.resume_votes)}/{required})"
            )

            if required >= len(player.resume_votes):
                await player.set_pause(False)
                player.resume_votes = set()
                await ctx.channel.send("Song vote-resumed")

    @RootGroup.command(name="shuffle")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def shuffle_queue(self, ctx: ApplicationContext):
        """Vote to shuffle the queue"""

        player = await self.ensure_voice(ctx)
        if not player:
            return

        elif not player.current:
            await ctx.respond("No music is currently being played!", ephemeral=True)
            return

        elif len(player.queue) < 5:
            await ctx.respond("The queue is too short to be shuffled!", ephemeral=True)
            return

        elif player.is_dj(ctx.author):
            player.shuffle_better()
            player.shuffle_votes = set()
            await ctx.respond("A DJ has shuffled the queue")
            return

        else:
            player.shuffle_votes.add(ctx.author.id)
            channel = ctx.guild.get_channel(player.channel_id)
            required = self.majority_vote(channel)

            await ctx.respond(
                f"{ctx.author.mention} has voted to shuffle the queue ({len(player.shuffle_votes)}/{required})"
            )

            if required >= len(player.shuffle_votes):
                player.shuffle_better()
                player.shuffle_votes = set()
                await ctx.channel.send("Queue vote-shuffled")

    @RootGroup.command(name="queue")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def view_queue(self, ctx: ApplicationContext):
        """View queued songs"""

        player = await self.ensure_voice(ctx)
        if not player:
            return

        if not len(player.queue):
            await ctx.respond("The queue is empty!", ephemeral=True)
            return

        embeds = []
        fieldCounter = 0
        position = 1

        embed = Embed(title=f"Music Queue", color=0x27C093)

        for track in player.queue:
            if fieldCounter == 10:
                fieldCounter = 0
                embeds.append(embed)
                embed = Embed(title=f"Music Queue", color=0x27C093)

            memberObject = ctx.guild.get_member(track.requester)
            if memberObject:
                name = memberObject.mention
            else:
                name = track.requester

            duration = lavalink.format_time(track.duration)
            if duration.startswith("00:"):
                duration = duration[3:]

            if position == 1:
                embed.add_field(
                    name=f"Up Next | {track.author} - *{track.title}*",
                    value=f"`{duration}` | Requested by {name}",
                    inline=False,
                )
            else:
                embed.add_field(
                    name=f"#{position} | {track.author} - *{track.title}*",
                    value=f"`{duration}` | Requested by {name}",
                    inline=False,
                )
            fieldCounter += 1
            position += 1

        if embed not in embeds:
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.respond(embed=embeds[0])
            return

        paginator = CustomPaginator(pages=embeds)

        await paginator.respond(ctx.interaction)

    @RootGroup.command(name="volume")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def change_volume(
        self,
        ctx: ApplicationContext,
        volume: Option(
            int,
            "Set the volume that music will be played at",
            min_value=0,
            max_value=100,
            required=True,
        ),
    ):
        """Change the volume of the music"""

        player = await self.ensure_voice(ctx)
        if not player:
            return

        if not player.is_dj(ctx.author):
            await ctx.respond(
                "You are not allowed to change the volume!", ephemeral=True
            )
            return

        if player.volume == volume:
            await ctx.respond("Volume unchanged.", ephemeral=True)
            return
        else:

            await player.set_volume(volume)

            await ctx.respond(f"Volume set to {volume}%")

    @RootGroup.command(name="effects")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def effects(
        self,
        ctx: ApplicationContext,
        effect: Option(
            str,
            "Effect to apply (Leave this empty to disable effects)",
            choices=[
                "Nightcore",
                "Chipmunks",
                "Deep",
                "Deepfried",
                "Wobble",
                "2x Speed",
                "0.5x Speed",
            ],
            required=False,
        ),
    ):
        """Apply music effects"""

        player = await self.ensure_voice(ctx)
        if not player:
            return

        if not player.is_dj(ctx.author):
            await ctx.respond(
                "You are not allowed to modify Music effects!", ephemeral=True
            )
            return

        await player.clear_filters()

        if not effect:
            await ctx.respond("Music effects disabled")

        elif effect == "Nightcore":
            await player.update_filter(lavalink.Timescale, speed=1.1, pitch=1.3)
            await ctx.respond("**Nightcore** effect enabled")
        elif effect == "Chipmunks":
            await player.update_filter(lavalink.Timescale, speed=1.0, pitch=1.8)
            await ctx.respond("**Chipmunks** effect enabled")
        elif effect == "Deep":
            await player.update_filter(lavalink.Timescale, speed=0.7, pitch=0.5)
            await ctx.respond("**Deep** effect enabled")
        elif effect == "Deepfried":
            await player.update_filter(lavalink.Timescale, speed=0.9, pitch=0.7)
            await player.update_filter(lavalink.Volume, volume=5.0)
            await ctx.respond("**Deepfried** effect enabled")
        elif effect == "Wobble":
            await player.update_filter(lavalink.Vibrato, frequency=5.0, depth=1.0)
            await ctx.respond("**Wobble** effect enabled")
        elif effect == "2x Speed":
            await player.update_filter(lavalink.Timescale, speed=2.0)
            await ctx.respond("Playback speed changed to 200%")
        elif effect == "0.5x Speed":
            await player.update_filter(lavalink.Timescale, speed=2.0)
            await ctx.respond("Playback speed changed to 50%")

    @RootGroup.command(name="emptyqueue")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def empty_queue(self, ctx: ApplicationContext):
        """Empty the Music queue"""

        player = await self.ensure_voice(ctx)
        if not player:
            return

        if not player.is_dj(ctx.author):
            await ctx.respond("You are not allowed to empty the queue!", ephemeral=True)
            return

        player.queue = []
        await ctx.respond("Queue emptied")

    @RootGroup.command(name="stats")
    @cooldown(1, 4, BucketType.user)
    @guild_only()
    async def node_info(self, ctx: ApplicationContext):
        """See stats on the player's Lavalink Node"""

        await ctx.defer(ephemeral=True)

        player = await self.ensure_voice(ctx)
        if not player:
            return

        node = player.node
        stats = node.stats
        embed = Embed(title=f"Connected To Node: {node.name}", color=0x6600FF)
        embed.add_field(
            name="Status", value="Online" if node.available else "Offline", inline=False
        )
        embed.add_field(
            name="Region", value=node.region.replace("_", " ").upper(), inline=False
        )

        nodes = self.bot.lavalink.node_manager.nodes
        embed.add_field(
            name="Node Health",
            value=f"**»** {len([n for n in nodes if n.available])}/{len(nodes)} Nodes Online",
            inline=False,
        )

        if not stats.is_fake:
            startTime = int(
                (utcnow() - timedelta(milliseconds=stats.uptime)).timestamp()
            )
            embed.add_field(
                name="Uptime",
                value=f"**»** Node Booted Up <t:{startTime}:R> (<t:{startTime}:d>)",
                inline=False,
            )
        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot: Type[Bot]) -> None:
    bot.add_cog(Music(bot))
