import pytest
import discord
from discord.ext import commands
from modules.core import utils
from modules.core.Log import log
import asyncio
import func_timeout

cfg = utils.CoreConfig.cfgDiscord

intents = discord.Intents.default()
intents.members = True  # Subscribe to the privileged members 

bot = commands.Bot(command_prefix=cfg["BOT_PREFIX"], pm_help=True, intents=intents)
bot.CoreConfig = utils.CoreConfig(bot)  

@bot.event
async def on_ready():
    utils.Modules.loadCogs(bot)
    log.info('Logged in as {} [{}]'.format(bot.user.name, bot.user.id))
    log.info(bot.guilds)
    log.info('------------')
    roles = []
    for guild in list(bot.guilds):
        roles += await guild.fetch_roles()
    bot.CoreConfig.load_role_permissions(roles)
    bot.close()


@pytest.mark.timeout(30)
def test_Optimizer():
    # Load the bot to test it working, then force it to close
    try:
        func_timeout.func_timeout(10, bot.run, args=(cfg["TOKEN"],))
    except func_timeout.FunctionTimedOut:
        pass
    assert True

