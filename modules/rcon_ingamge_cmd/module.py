
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
import inspect
import time

from modules.core.utils import CommandChecker, sendLong, CoreConfig, Tools
from .cmdengine import RconCommandEngine

class CommandRconTaskScheduler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        #self.rcon_adminNotification = CoreConfig.cfg.new(self.path+"/rcon_scheduler.json")
    
        asyncio.ensure_future(self.on_ready())
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.CommandRcon = self.bot.cogs["CommandRcon"]


# Registering functions, and interacting with the discord bot.
class CommandRconIngameComs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        self.afkLock = False
        self.afkTime = -1
        asyncio.ensure_future(self.on_ready())
        
        self.RconCommandEngine = RconCommandEngine
        RconCommandEngine.cogs = self
        RconCommandEngine.rate_limit_commands.append("afk")
        #RconCommandEngine.admins.append("Yoshi_E") this simply bypasses cooldowns for cmds
        #RconCommandEngine.admins.append("[H] Tom")
        #RconCommandEngine.admins.append("zerty")
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.CommandRcon = self.bot.cogs["CommandRcon"]
    
        
    @RconCommandEngine.command(name="ping")  
    async def ping(self, rctx):
        await rctx.say("Pong!")    

    @RconCommandEngine.command(name="help")  
    async def ping(self, rctx):
        for func_name, func, parameters in RconCommandEngine.commands:
            if(len(parameters) > 2):
                await rctx.say("{} {}".format(func_name, parameters[2:]))   
            else:
                await rctx.say("{}".format(func_name))    
        
    @RconCommandEngine.command(name="players")  
    async def players(self, rctx):
        playerList = await self.CommandRcon.arma_rcon.getPlayersArray()
        msg = ""
        for id, ip, ping, guid, name in playerList:
            msg += "\n{} | {}".format(id, name[:22]) #.ljust(20, " ") #.rjust(3, " ")
            if(len(msg)>200):
                await rctx.say(msg)
                msg = "\n"
        if(msg != ""):
            await rctx.say(msg)    
            
    @RconCommandEngine.command(name="afk")  
    async def check_afk(self, rctx, beid):
        time_to_respond = 300 #checks for 5min (10*30s), gives a warning every 30s
        channel = rctx.channel
        user = rctx.user
        ctx_beid = rctx.user_beid
        
        
        if(self.afkLock == True):
            await rctx.say("An AFK check is already in progess, please wait {}s.".format(self.afkTime))
            return False
        self.afkLock = True
        
        players = await self.CommandRcon.arma_rcon.getPlayersArray()
        player_name = None
        for player in players:
            if(int(player[0]) == int(beid)):
                player_name = player[4]
        if(player_name!=None and player_name.endswith(" (Lobby)")): #Strip lobby from name
            player_name = player_name[:-8]
        
        if(player_name==None):
            await rctx.say("Failed to find player with that ID")
            self.afkLock = False
            return False
        msg= "Starting AFK check for: {} - {}".format(player_name, beid)
        await rctx.say(msg)
        
        already_active = False
        for i in range(0, time_to_respond): 
            self.afkTime = time_to_respond-i
            if(self.CommandRcon.playerTypesMessage(player_name)):
                if(i==0):
                    already_active = True
                    await rctx.say("Player was recently active. Canceling AFK check.")  
                else:
                    await rctx.say("Player responded in chat. Canceling AFK check.")  
                if(already_active == False):
                    await self.CommandRcon.arma_rcon.sayPlayer(beid,  "Thank you for responding in chat.")
                self.afkLock = False
                return True
            if((i % 30) == 0):
                try:
                    for k in range(0, 3):
                        await self.CommandRcon.arma_rcon.sayPlayer(beid, "Type something in chat or you will be kicked for being AFK. ("+str(round(i/30)+1)+"/10)")
                except: 
                    print("Failed to send command sayPlayer (checkAFK)")
            await asyncio.sleep(1)
        if(self.CommandRcon.playerTypesMessage(player_name)):
            if(i==0):
                already_active = True
            await rctx.say("Player responded in chat. Canceling AFK check.")  
            if(already_active == False):
                try:
                    await self.CommandRcon.arma_rcon.sayPlayer(beid, "Thank you for responding in chat.")
                except:
                    print("Failed to send command sayPlayer")
            self.afkLock = False        
            return False
        else:
            await self.CommandRcon.arma_rcon.kickPlayer(beid, "AFK too long (user_check by {})".format(user))
            await rctx.say("``{}`` did not respond and was kicked for being AFK".format(player_name))
        self.afkLock = False

def setup(bot):
    #bot.add_cog(CommandRconTaskScheduler(bot))
    bot.add_cog(CommandRconIngameComs(bot))