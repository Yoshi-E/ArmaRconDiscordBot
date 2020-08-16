
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

from modules.core.utils import CommandChecker, RateBucket, CoreConfig
import modules.core.utils as utils
from modules.arma.readLog import readLog

class CommandArma(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        self.cfg = CoreConfig.modules["modules/arma"]["general"]
        
        #read the Log files
        self.readLog = readLog(self.cfg["log_path"], maxMisisons=self.cfg["buffer_maxMisisons"])
        self.readLog.define_line_types()
        self.readLog.pre_scan()
        
        
        self.server_pid = None
        asyncio.ensure_future(self.on_ready())
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.CommandRcon = self.bot.cogs["CommandRcon"]
        asyncio.ensure_future(self.readLog.watch_log())
        
        
###################################################################################################
#####                              Arma 3 Server start - stop                                  ####
###################################################################################################         
    def start_server(self):
        
        #subprocess.call(shlex.split(self.CommandRcon.rcon_settings["start_server"]))  
        self.server_pid = subprocess.Popen(shlex.split(self.cfg["start_server"]))  
        
    def stop_server(self):
        if(self.server_pid != None):
            self.server_pid.kill()
            self.server_pid = None
        else:
            return False
            
    def stop_all_server(self):
        for proc in psutil.process_iter():
            if(proc.name()==self.cfg["stop_server"]):
                proc.kill()
        #os.system('taskkill /f /im {}'.format(self.CommandRcon.rcon_settings["stop_server"])) 
        
    @CommandChecker.command(name='start',
            brief="Starts the arma server",
            pass_context=True)
    async def start(self, ctx):
        await ctx.send("Starting Server...")  
        self.start_server()
        self.CommandRcon.autoReconnect = True
   
    @CommandChecker.command(name='stop',
            brief="Stops the arma server (If server was started with !start)",
            pass_context=True)
    async def stop(self, ctx):
        self.CommandRcon.autoReconnect = False
        if(self.stop_server()==False):
            await ctx.send("Failed to stop server. You might want to try '!stop_all' to stop all arma 3 instances")
        else:
            await ctx.send("Stopped the Server.")      

    @CommandChecker.command(name='stopall',
            brief="Stop all configured arma servers",
            pass_context=True)
    async def stop_all(self, ctx):
        self.CommandRcon.autoReconnect = False
        self.stop_all_server()
        await ctx.send("Stop all Servers.")      
        
    @CommandChecker.command(name='history',
            brief="Returns recently played missions",
            pass_context=True)
    async def history(self, ctx):
        mlist = []
        for mission in reversed(self.readLog.Missions):
            if "Mission starting" in mission["dict"]:
                mlist.append("{} {} {} ({} entries)".format(  mission["dict"]["Mission starting"][0], 
                                                mission["dict"]["Mission world"][2].group(2), 
                                                mission["dict"]["Mission file"][2].group(2),
                                                len(mission["data"])))
        msg = "Recently played missions (new to old)\n"
        msg += "\n".join(mlist)
        await ctx.send(msg)  
  

def setup(bot):
    bot.add_cog(CommandArma(bot))