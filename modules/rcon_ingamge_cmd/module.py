
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

import bec_rcon

from modules.rcon import readLog
from modules.core.utils import CommandChecker, RateBucket, sendLong, CoreConfig, Tools

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

    #context object for players
    class context(object):
        def __init__(self):
            RconCommandEngine.logging = True
        
            self.base_msg = None
            self.func_name = None
            self.parameters = None
            self.args = None
            self.rctx = None
            self.error = False
            self.executed = False
            self.user = None
            self.command = None
            self.channel = None
            self.base_msg = None
            self.user_beid = -1
        
        async def say(self, msg):
            if(int(self.user_beid) >= 0):
                if(RconCommandEngine.logging==True):
                    RconCommandEngine.log_s(msg)
                await RconCommandEngine.cogs.CommandRcon.arma_rcon.sayPlayer(self.user_beid, msg)
            else:
                self.error = "Invalid BEID"
                raise Exception(self.error)
    
        def __repr__(self):
            return "RconContext<[{}], {}>".format(self.user_beid, self.base_msg)
            
        def __str__(self):
            return "{} [beid: {}, executed: {}, error: {}]".format(self.base_msg, self.user_beid, self.executed, self.error)
    
    logging = True
    commands = []
    channels = ["Side", "Global", "Vehicle", "Direct", "Group", "Command"]
    command_prefix = "?"
    cogs = None
    users = {}
    rate_limit_commands = []
    rate_limit = 900 #15min
    admins = []
    
    
    @staticmethod
    def log_s(msg):
        if(RconCommandEngine.logging==True):
            now = datetime.datetime.now()
            print(now.strftime("%m/%d/%Y, %H:%M:%S"), msg)  
            
    def log(self, msg):
        if(RconCommandEngine.logging==True):
            now = datetime.datetime.now()
            print(now.strftime("%m/%d/%Y, %H:%M:%S"), msg)    
            
    @staticmethod
    async def getPlayerBEID(player: str):
        #get updated player list, only if player not found
        #if(not player in Tools.column(self.playerList,4)):   
        playerList = await RconCommandEngine.cogs.CommandRcon.arma_rcon.getPlayersArray()
        for id, ip, ping, guid, name  in playerList:
            if(name.endswith(" (Lobby)")): #Strip lobby from name
                name = name[:-8]
            if(player == name):
                return id
        raise LookupError("Player '{}' not found".format(player))
        
    @staticmethod
    def isChannel(msg):
        for channel in RconCommandEngine.channels:
            if(channel in msg):
                return channel
        return False
    
    @staticmethod
    async def parseCommand(message: str):
        try:
            if(": " in message):
                header, body = message.split(": ", 1)
                channel = RconCommandEngine.isChannel(header)
                if(channel): #was written in a channel
                    ctx = RconCommandEngine.context()
                    ctx.base_msg = message
                    ctx.user = header.split(") ")[1]
                    
                    ctx.args = body.split(" ")
                    ctx.command = ctx.args[0]
                    ctx.args = ctx.args[1:]
                    
                    ctx.channel = channel
                    if(len(ctx.command) > 0 and RconCommandEngine.command_prefix==ctx.command[0]):
                        ctx.command = ctx.command[1:]
                        return await RconCommandEngine.processCommand(ctx)
        except Exception as e:
            RconCommandEngine.log_s(traceback.format_exc())
            RconCommandEngine.log_s(e)
                        
    async def processCommand(ctx):
        ctx.user_beid = await RconCommandEngine.getPlayerBEID(ctx.user)
        for func_name, func, parameters in RconCommandEngine.commands:
            ctx.func_name = func_name 
            ctx.parameters = parameters 
            try:
                if(func_name==ctx.command):
                    if( ctx.user  not in RconCommandEngine.admins):
                        #Create Rate limit
                        if( ctx.user  not in RconCommandEngine.users):
                            RconCommandEngine.users[ctx.user] = RateBucketLimit(True, RconCommandEngine.rate_limit)
                        if(func_name in RconCommandEngine.rate_limit_commands):
                            check_data = RconCommandEngine.users[ctx.user].check(func_name)
                            if(check_data != True):
                                ctx.executed = False
                                await ctx.say("Error: '{}'".format(check_data))
                                return ctx
                    
                    if(len(parameters) > 0):
                        await func(ctx, *ctx.args)
                    else:
                        await func(ctx)
                    ctx.executed = True
                    RconCommandEngine.log_s(ctx)
                    return ctx
            except TypeError as e:
                ctx.error = "Invalid arguments: Given {}, expected {}".format(len(ctx.args), len(parameters)-2)
                ctx.executed = False
                RconCommandEngine.log_s(traceback.format_exc())
                RconCommandEngine.log_s("Error in: {}".format(ctx))
                return ctx
            except Exception as e:
                if(ctx.command == "afk"):
                    RconCommandEngine.cogs.afkLock = False #set Rconcommand engine 
                RconCommandEngine.log_s(traceback.format_exc())
                ctx.error = "Error: '{}'".format(e)
                ctx.executed = False
                RconCommandEngine.log_s("Error in: {}".format(ctx))
                return ctx
        #Command not found
        if(len(ctx.command) > 0 and ctx.command[0] != "?" and ctx.command != "" and ctx.command != None):
            ctx.error = "Command '{}' not found".format(ctx.command)
            ctx.executed = False
            RconCommandEngine.log_s(ctx)
            return ctx
        return None
            
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
            RconCommandEngine.commands.append([name, t, inspect.getfullargspec(function)[0]])
            return t
        return arguments


# Registering functions, and interacting with the discord bot.
class CommandRconIngameComs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        self.afkLock = False
        self.afkTime = -1
        asyncio.ensure_future(self.on_ready())
        RconCommandEngine.cogs = self
        RconCommandEngine.rate_limit_commands.append("afk")
        #RconCommandEngine.admins.append("Yoshi_E")
        RconCommandEngine.admins.append("[H] Tom")
        RconCommandEngine.admins.append("zerty")
        
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
    bot.add_cog(CommandRconTaskScheduler(bot))
    bot.add_cog(CommandRconIngameComs(bot))