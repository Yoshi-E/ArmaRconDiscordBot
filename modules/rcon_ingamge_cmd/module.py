
# Works with Python 3.6
# Discord 1.2.2
import asyncio
from collections import Counter
from collections import deque
import concurrent.futures
import json
import os
import sys
import traceback
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
import prettytable
import geoip2.database
import datetime
import shlex, subprocess
import psutil

import bec_rcon

from modules.rcon import readLog

new_path = os.path.dirname(os.path.realpath(__file__))+'/../core/'
if new_path not in sys.path:
    sys.path.append(new_path)
from utils import CommandChecker, RateBucket, sendLong, CoreConfig, Tools


class CommandRconTaskScheduler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        #self.rcon_adminNotification = CoreConfig.cfg.new(self.path+"/rcon_scheduler.json")
    
        asyncio.ensure_future(self.on_ready())
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.CommandRcon = self.bot.cogs["CommandRcon"]


class RconCommandEngine(object):
    commands = []
    channels = ["Side", "Global", "Vehicle", "Direct", "Group", "Command"]
    command_prefix = "?"
    cogs = None
    
    @staticmethod
    def isChannel(msg):
        for channel in RconCommandEngine.channels:
            if(channel in msg):
                return channel
        return False
    
    @staticmethod
    async def parseCommand(message: str):
        if(": " in message):
            header, body = message.split(": ", 1)
            channel = RconCommandEngine.isChannel(header)
            if(channel): #was written in a channel
                user = header.split(") ")[1]
                msg = body.split(" ")
                com = msg[0]
                if(RconCommandEngine.command_prefix==com[0]):
                    com = com[1:]
                    if(len(msg)>0):
                        args = msg[1:]
                    else:
                        args = None
                    for name, func, parameters in RconCommandEngine.commands:
                        if(name==com):
                            if(len(parameters) > 2):
                                await func(channel, user, *args)
                            else:
                                await func(channel, user)
                                
                            return True
        return False
            
    @staticmethod
    def command(*args, **kwargs):
        def arguments(function):
            if("name" in kwargs):
                name = kwargs["name"]
            else:
                name =  function.__name__

            if(name in Tools.column(RconCommandEngine.commands, 0)):
                raise Exception("Command '{}' already exists".format(name))
            #init
            async def wrapper(*args, **kwargs):
                return await function(RconCommandEngine.cogs, *args, **kwargs)
            t = wrapper
            RconCommandEngine.commands.append([name, t, function.__code__.co_varnames])
            return t
        return arguments


# Registering functions, and interacting with the discord bot.
class CommandRconIngameComs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.playerList = None
        
        asyncio.ensure_future(self.on_ready())
        RconCommandEngine.cogs = self
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.CommandRcon = self.bot.cogs["CommandRcon"]
        self.playerList = await self.CommandRcon.arma_rcon.getPlayersArray()
    
    async def getPlayerBEID(self, player: str):
         #get updated player list, only if player not found
        if(not player in Tools.column(self.playerList,4)):   
            self.playerList = await self.CommandRcon.arma_rcon.getPlayersArray()
        for id, ip, ping, guid, name  in self.playerList:
            if(name.endswith(" (Lobby)")): #Strip lobby from name
                name = name[:-8]
            if(player == name):
                return id
                
    @RconCommandEngine.command(name="ping")  
    async def ping(self, channel, user):
        beid = await self.getPlayerBEID(user)
        await self.CommandRcon.arma_rcon.sayPlayer(beid, "Pong!")

def setup(bot):
    bot.add_cog(CommandRconTaskScheduler(bot))
    bot.add_cog(CommandRconIngameComs(bot))