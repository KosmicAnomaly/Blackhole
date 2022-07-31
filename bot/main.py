import logging
import os
from logging.handlers import TimedRotatingFileHandler

from discord.utils import utcnow

from tools.bot import Anomaly

startTime = utcnow()

# Set up logging
logger = logging.getLogger("kosmo")
logger.setLevel(logging.INFO)

fileHandler = TimedRotatingFileHandler(
    filename=f"./logs/bot.log", when="midnight", interval=1, backupCount=7)
format = logging.Formatter(
    "%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
fileHandler.setFormatter(format)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(format)
logger.addHandler(consoleHandler)


bot = Anomaly()

for root, dirs, files in os.walk("./cogs"):
    for file in files:
        if file.endswith(".py"):
            name = os.path.join(root, file).replace("/", ".")[2:-3]
            try:
                bot.load_extension(name)
            except:
                logger.error(f"Failed to load Cog '{name}'", exc_info=True)
            else:
                logger.info(f"Cog '{name}' loaded")


if __name__ == "__main__":
    discordToken = os.getenv("DISCORD_TOKEN")
    try:
        logger.info("Logging into Discord")
        bot.run(discordToken)
    except:
        logger.critical("Failed to login to Discord")
    else:
        logger.warning("Kosmo has shut down")
