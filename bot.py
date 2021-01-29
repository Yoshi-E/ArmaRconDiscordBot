import sys
import os

if(sys.version_info[0] != 3 or (sys.version_info[1] > 6 or sys.version_info[1] < 4)):
    sys.exit("This bot requires Python3 >= 3.4 and <= 3.6. You are currently running version {}.{}".format(*sys.version_info[:2]))
import discord
from discord.ext import commands
from modules.core import utils
import time
import subprocess
import asyncio


import logging
from logging.handlers import RotatingFileHandler

#Create Log handler:
log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
logFile = os.path.dirname(os.path.realpath(__file__))+"/discord.log"
my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=1*1000000, backupCount=10, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)
log = logging.getLogger("discord")
log.setLevel(logging.INFO)
log.addHandler(my_handler)


# Make bot join server:
# https://discordapp.com/oauth2/authorize?client_id=xxxxxx&scope=bot
# API Reference
#https://discordpy.readthedocs.io/en/rewrite/ext/commands/api.html#event-reference

#cfg = utils.CoreConfig.modules["modules/core"]["discord"]
cfg = utils.CoreConfig.cfgDiscord

intents = discord.Intents.default()
intents.members = True  # Subscribe to the privileged members 

bot = commands.Bot(command_prefix=cfg["BOT_PREFIX"], pm_help=True, intents=intents)
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
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("[DiscordBot] Interrupted")
        
    if(hasattr(bot, "restarting") and bot.restarting == True):
        print("Restarting")
        
        time.sleep(1)
        subprocess.Popen("python" + " bot.py", shell=True) #TODO: Will not work on all system
