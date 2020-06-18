import discord
from discord.ext import commands
from modules.core import utils
import time
import subprocess
import asyncio
import sys
# Make bot join server:
# https://discordapp.com/oauth2/authorize?client_id=xxxxxx&scope=bot
# API Reference
#https://discordpy.readthedocs.io/en/rewrite/ext/commands/api.html#event-reference

#cfg = utils.CoreConfig.modules["modules/core"]["discord"]
cfg = utils.CoreConfig.cfgDiscord

bot = commands.Bot(command_prefix=cfg["BOT_PREFIX"], pm_help=True)
bot.CoreConfig = utils.CoreConfig(bot)
 
###################################################################################################
#####                                  Initialization                                          ####
###################################################################################################     

@bot.event
async def on_ready():
    print('Logged in as {} [{}]'.format(bot.user.name, bot.user.id))
    print(bot.guilds)
    print('------------')
    bot.CoreConfig.load_role_permissions()

async def main():
    
    utils.Modules.loadCogs(bot)
    
    try:
        await bot.login(cfg["TOKEN"])
        await bot.connect()
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys.exit("Bot Terminated (KeyboardInterrupt)")
    except (KeyError, discord.errors.LoginFailure):
        print("")
        input("Please configure the bot on the settings page. [ENTER to terminte the bot]\n")


if __name__ == '__main__':

    #while True:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    #asyncio.ensure_future()
    if(hasattr(bot, "restarting") and bot.restarting == True):
        print("Restarting")
        
        time.sleep(1)
        subprocess.Popen("python" + " bot.py", shell=True)
