import re
from contextlib import suppress

import cmudict
import syllables
from discord import ButtonStyle, Embed, HTTPException, Message, TextChannel
from discord.ui import Button, View
from discord.utils import escape_markdown
from num2words import num2words
from tools.cog import Cog
from tools.colors import Colors

# Haiku detection adapted from https://www.kaggle.com/lazovich/headline-haiku-detection

syllableDictionary = cmudict.dict()


def delete_markdown(text: str):
    underlined = r"(__){1}([\s\S]+)(__){1}"
    italics1 = r"(_){1}([\s\S]+)(_){1}"
    italics2 = r"(\*){1}([\s\S]+)(\*){1}"
    bold = r"(\*\*){1}([\s\S]+)(\*\*){1}"
    strikethrough = r"(~~){1}([\s\S]+)(~~){1}"
    spoiler = r"(\|\|){1}([\s\S]+)(\|\|){1}"
    codeBlock = r"(```){1}([\s\S]+)(```){1}"
    code = r"(`){1}([\s\S]+)(`){1}"
    markdownRegex = [underlined, italics1, bold,
                     italics2, strikethrough, spoiler, codeBlock, code]

    for type in markdownRegex:
        while re.findall(type, text):
            text = re.sub(type, r"\2", text)
    return text


def count_syllables(word: str):

    # Convert the number into its word-form if possible
    if word.isnumeric():
        try:
            words = num2words(word).replace("-", " ").split(" ")
        except:
            return None
    else:
        words = word.replace("-", " ").split(" ")

    totalSyllables = 0

    for thisWord in words:
        # Check if word is in the dictionary
        syls = syllableDictionary[thisWord]

        if not len(syls):
            totalSyllables = syllables.estimate(thisWord)
        else:
            for sound in syls[0]:
                if sound[-1].isdigit():
                    totalSyllables += 1

    return totalSyllables


def is_haiku(text: str):
    words = text.split(" ")

    totalSyllables = 0
    hit_5 = False
    hit_7 = False

    thisGroup = []

    haikuParts = [None, None, None]

    # Loop through all the words and check for the
    # intermediate milestones of a haiku structure
    i = 0
    for word in words:

        thisGroup.append(i)

        wordSyllables = count_syllables(word)

        if not wordSyllables:
            return False

        totalSyllables += wordSyllables

        # We hit the first five syllables - reset the counter
        if totalSyllables == 5 and not hit_5:
            totalSyllables = 0
            hit_5 = True
            haikuParts[0] = thisGroup
            thisGroup = []

        # If we hit five and then found 7 syllables,
        # we have our second haiku line
        if totalSyllables == 7 and hit_5 and not hit_7:
            totalSyllables = 0
            hit_7 = True
            haikuParts[1] = thisGroup
            thisGroup = []

        i += 1

    # If we hit 5 and 7 and there are only 5
    # syllables left, we have a haiku-able text
    if (totalSyllables == 5) and hit_5 and hit_7:
        haikuParts[2] = thisGroup

        return haikuParts
    return False


class Haiku(Cog, name="Haiku"):
    """Haiku module"""

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        elif not message.guild:
            return
        elif not message.content:
            return

        guild = message.guild

        statement = """
        SELECT enabled, channel_id, announce, react FROM HaikuSettings
        WHERE guild_id = %s;
        """
        settings = self.bot.database.execute(
            statement, (guild.id,), 1)

        if not settings or not settings[0]:
            return

        # remove markdown
        content = delete_markdown(message.clean_content.replace("\n", " "))

        # remove double spaces
        content = re.sub(r" +", " ", content)

        # check if all characters are stuff that we want
        if not re.fullmatch(r"[a-zA-Z0-9 (){}[\]\"\*'+\-$%#@!\^&,;:?!\.]+", content):
            return

        # change stuff like "5.0" to "5 point 0"
        haikuReady = re.sub(r"([0-9]){1}\.([0-9]){1}", r"\1 point \2", content)

        # Remove punctuation and other bad characters
        haikuReady = re.sub(r"[^\s\w-]", "", haikuReady)
        haikuReady = re.sub(r" +", " ", haikuReady).strip()

        if not len(haikuReady):
            return

        parts = is_haiku(haikuReady)
        if parts is False:
            return

        words = content.split(" ")

        firstLine = escape_markdown(" ".join([words[i] for i in parts[0]]))
        secondLine = escape_markdown(" ".join([words[i] for i in parts[1]]))
        thirdLine = escape_markdown(" ".join([words[i] for i in parts[2]]))

        haiku = f"*{firstLine}*\n*{secondLine}*\n*{thirdLine}*"

        embed = Embed(description=haiku, color=Colors.parchment())
        embed.set_footer(text=f"- {message.author.name}",
                         icon_url=message.author.avatar.url)

        if settings[1]:
            haikuChannel = self.bot.get_partial_messageable(
                settings[1], type=TextChannel)

            view = View()
            url = message.jump_url.replace("@me", str(guild.id))
            view.add_item(Button(style=ButtonStyle.link,
                          label="Jump to message", url=url, row=0))

            with suppress(HTTPException):
                await haikuChannel.send(embed=embed, view=view)

        if settings[2]:
            with suppress(HTTPException):
                await message.reply(embed=embed, mention_author=False)

        if settings[3]:
            with suppress(HTTPException):
                await message.add_reaction("📜")


def setup(bot):
    bot.add_cog(Haiku(bot))
