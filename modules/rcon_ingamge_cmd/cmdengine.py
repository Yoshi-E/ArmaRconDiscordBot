
# Works with Python 3.6
import asyncio
from collections import Counter
from collections import deque
import os
import sys
import traceback
import datetime
import inspect
import time

import logging
from logging.handlers import RotatingFileHandler

#Limits commands to X per second
class RateBucketLimit():
    def __init__(self, per_function = False, limit = 30):
        self.limit = limit
        self.last = 0 #time.time()-(limit+1)
        self.per_function = per_function
        self.functions = {}
        
    def check(self, func_name):
        if(self.per_function == True):
            if(func_name not in self.functions):
                self.functions[func_name] = RateBucketLimit(False, self.limit)
            return self.functions[func_name].check(func_name)
        else:    
            if((time.time()-self.last) < self.limit):
                return "You have to wait {} seconds before you can use this command again.".format(round(abs(time.time()-self.last-self.limit)))
        return True
        
    def update(self):
        if((time.time()-self.last) >= self.limit):
            self.last = time.time()

class RconCommandEngine(object):

    #context object for players
    class context(object):
        def __init__(self):
            RconCommandEngine.logging = True
        
            self.base_msg = None
            self.func_name = None
            self.parameters = None
            self.args = None
            self.error = False
            self.executed = False
            self.user = None
            self.command = None
            self.channel = None
            self.user_beid = -1
            self.user_guid = -1
        
        async def say(self, msg):
            if(int(self.user_beid) >= 0):
                if(RconCommandEngine.logging==True):
                    RconCommandEngine.log.info(msg)
                await RconCommandEngine.cogs["CommandRcon"].arma_rcon.sayPlayer(self.user_beid, msg)
            else:
                self.error = "Invalid BEID"
                raise Exception(self.error)
    
        def __repr__(self):
            return "RconContext<[{}], {}>".format(self.user_beid, self.base_msg)
            
        def __str__(self):
            return "{} [beid: {}, executed: {}, error: {}]".format(self.base_msg, self.user_beid, self.executed, self.error)
    
    console_logging = True
    commands = []
    channels = ["Side", "Global", "Vehicle", "Direct", "Group", "Command"]
    command_prefix = "?"
    cogs = None #acess to discord bots cogs
    users = {}
    rate_limit_commands = []
    rate_limit = 900 #15min
    admins = []
    
    #Create Log handler:
    _log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
    _logFile = os.path.dirname(os.path.realpath(__file__))+"/commands.log"
    _stdout_handler = logging.StreamHandler(sys.stdout)
    _my_handler = RotatingFileHandler(_logFile, mode='a', maxBytes=10*1000000, backupCount=10, encoding=None, delay=0)
    _my_handler.setFormatter(_log_formatter)
    _my_handler.setLevel(logging.INFO)

    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)
    log.addHandler(_my_handler)
    log.addHandler(_stdout_handler)

    @staticmethod
    async def getPlayerBEID(player: str):
        #get updated player list, only if player not found
        #if(not player in Tools.column(self.playerList,4)):   
        playerList = await RconCommandEngine.cogs["CommandRcon"].arma_rcon.getPlayersArray()
        for id, ip, ping, guid, name  in playerList:
            if(name.endswith(" (Lobby)")): #Strip lobby from name
                name = name[:-8]
            if(player == name):
                return (id, guid)
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
                    if(len(ctx.command) > len(RconCommandEngine.command_prefix) and RconCommandEngine.command_prefix==ctx.command[:len(RconCommandEngine.command_prefix)]):
                        ctx.command = ctx.command[len(RconCommandEngine.command_prefix):]
                        return await RconCommandEngine.processCommand(ctx)
        except Exception as e:
            RconCommandEngine.log.error(traceback.format_exc())
            RconCommandEngine.log.error(e)
    
    @staticmethod
    async def checkPermission(ctx, func_name):
        return True

    @staticmethod     
    async def processCommand(ctx):
        self = RconCommandEngine.cogs["CommandRconIngameComs"]
        ctx.user_beid, ctx.user_guid = await RconCommandEngine.getPlayerBEID(ctx.user)
        for Command in RconCommandEngine.commands:
            ctx.func_name = Command["cmd"] 
            ctx.parameters = Command["kwargs"] 
            func = Command["func"]
            try:
                if(Command["cmd"] ==ctx.command):
                    for cog in Command["cogs"]:
                        if cog not in RconCommandEngine.cogs:
                            ctx.executed = False
                            ctx.error = "Cog '{}' not loaded".format(cog)
                            return ctx
                
                    if( ctx.user  not in RconCommandEngine.admins):
                        #Create Rate limit
                        if( ctx.user  not in RconCommandEngine.users):
                            RconCommandEngine.users[ctx.user] = RateBucketLimit(True, RconCommandEngine.rate_limit)
                        if(Command["cmd"]  in RconCommandEngine.rate_limit_commands):
                            check_data = RconCommandEngine.users[ctx.user].check(Command["cmd"] )
                            if(check_data != True):
                                ctx.executed = False
                                await ctx.say("Error: '{}'".format(check_data))
                                return ctx
                                
                    permisison = await RconCommandEngine.checkPermission(ctx, Command["cmd"])
                    if(not permisison):
                        ctx.executed = False
                        return ctx

                    if(len(Command["kwargs"] ) > 0):
                        result = await func(self, ctx, *ctx.args)
                    else:
                        result = await func(self, ctx)
                    
                    if result: #only update if the command was executed correctly (returned True)
                         RconCommandEngine.users[ctx.user].update()
                         
                    ctx.executed = True
                    RconCommandEngine.log.info(ctx)
                    return ctx
            except TypeError as e:
                ctx.error = "Invalid arguments: Given {}, expected {}".format(len(ctx.args), len(Command["kwargs"])-2)
                ctx.executed = False
                await ctx.say(ctx.error)
                RconCommandEngine.log.error(traceback.format_exc())
                RconCommandEngine.log.error("Error in: {}".format(ctx))
                return ctx
            except Exception as e:
                if(ctx.command == "afk"):
                    RconCommandEngine.cogs["CommandRconIngameComs"].afkLock = False #set Rconcommand engine 
                RconCommandEngine.log.error(traceback.format_exc())
                ctx.error = "Error: '{}'".format(e)
                ctx.executed = False
                await ctx.say("Error '{}'".format(ctx.error))
                RconCommandEngine.log.error("Error in: {}".format(ctx))
                return ctx
        #Command not found
        if(len(ctx.command) > len(RconCommandEngine.command_prefix) and ctx.command[:len(RconCommandEngine.command_prefix)] != RconCommandEngine.command_prefix and ctx.command != "" and ctx.command != None):
            ctx.error = "Command '{}' not found".format(ctx.command)
            ctx.executed = False
            RconCommandEngine.log.warning(ctx)
            return ctx
        return None
        
    @staticmethod
    def command(*args, **kwargs):
        def arguments(function):
            if("name" in kwargs):
                name = kwargs["name"]
            else:
                name =  function.__name__           
            
            if("cogs" in kwargs):
                cogs = kwargs["cogs"]
            else:
                cogs = []
                        
            for Command in RconCommandEngine.commands:       
                if(name == Command["cmd"]):
                    raise Exception("Command '{}' already exists".format(name))
            
            #init
            async def wrapper(*t_args, **t_kwargs):
                # t_args[0] --> self
                return await function(*t_args, **t_kwargs)
            t = wrapper
            RconCommandEngine.commands.append({"cmd": name, "func": t, "kwargs": inspect.getfullargspec(function)[0], "cogs": cogs})
            return t
        return arguments
