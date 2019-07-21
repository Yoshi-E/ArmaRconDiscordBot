import traceback
import sys
import os
import discord
from packaging import version
import time
import inspect
import asyncio

assert version.parse(discord.__version__) >= version.parse("1.2.2"), "Module 'Discord' required to be >= 1.2.5"

new_path = os.path.dirname(os.path.realpath(__file__))
if new_path not in sys.path:
    sys.path.append(new_path)
from config import Config

#combines items of the last X seconds into a list
class RateBucket():
    def __init__(self, function, limit = 5):
        self.limit = limit
        self.last = time.time()
        self.list = []
        self.function = function
    
    # ensures the msg is send
    async def _add_check(self):
        asyncio.sleep(self.limit+0.1)
        self._add()
    
    def _add(self):
        if((time.time()-self.last) > self.limit):
            if(inspect.iscoroutinefunction(self.function)): #is async
                asyncio.ensure_future(self.function(self.list))
            else:
                self.function(self.list) 
            self.list = []
            self.last = time.time()
        else:
            asyncio.ensure_future(self._add_check())
                
    def add(self, value):
        self.list.append(value)
        self._add()


class CoreConfig():
    path = os.path.dirname(os.path.realpath(__file__))
    cfg = Config(path+"/config.json", path+"/config.default_json")
    
    @staticmethod
    def update():
        GlobalConfig.cfg.load() #reload cfg from file 

class CommandChecker():
    
    @staticmethod
    def check(func):
        async def commandDenied(ctx):
            await ctx.send("You cant use this command here.")
        
        async def wrapped(*args, **kwargs):
            if(len(args)>1):
                super_self = args[0]
                ctx = args[1]
                if(type(ctx) == discord.ext.commands.context.Context):
                    if(len(CoreConfig.cfg["listChannels"])>0 and not ctx.message.channel.id in CoreConfig.cfg["listChannels"]):
                        return await commandDenied(ctx)
                    
            return await func(*args, **kwargs)
        return wrapped


