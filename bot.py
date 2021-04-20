#!/usr/bin/python3
import sys
import os
import time

if(sys.version_info[0] != 3 or (sys.version_info[1] > 6 or sys.version_info[1] < 5)):
    print("This bot requires Python >= 3.5 and <= 3.6. You are currently running version {}.{}".format(*sys.version_info[:2]))
    time.sleep(5)
    sys.exit("Terminated")

import discord
from discord.ext import commands
from modules.core import utils
from modules.core.Log import log

import subprocess
import asyncio

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
    log.info('Logged in as {} [{}]'.format(bot.user.name, bot.user.id))
    log.info(bot.guilds)
    log.info('------------')
    roles = []
    for guild in list(bot.guilds):
        roles += await guild.fetch_roles()
    bot.CoreConfig.load_role_permissions(roles)

async def main():
    
    utils.Modules.loadCogs(bot)
    
    try:
        await bot.login(cfg["TOKEN"])
        await bot.connect()
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys.exit("Bot Terminated (KeyboardInterrupt)")
    except (KeyError, discord.errors.LoginFailure):
        log.info("PROMPT: Please configure the bot")
        input("\nPlease configure the bot on the settings page. [ENTER to terminte the bot]\n")


if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("[DiscordBot] Interrupted")
        
    if(hasattr(bot, "restarting") and bot.restarting == True):
        log.info("Restarting")
        
        time.sleep(1)
        subprocess.Popen("python" + " bot.py", shell=True) #TODO: Will not work on all system
