
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
from collections import deque
import prettytable
import geoip2.database
import datetime
import shlex, subprocess
import psutil
import re
from time import time


import bec_rcon

from modules.core.utils import CommandChecker, RateBucket, CoreConfig
import modules.core.utils as utils
from modules.arma.readLog import readLog



class CommandArma(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        self.cfg = CoreConfig.modules["modules/arma"]["general"]
        self.channel = None
        
        #read the Log files
        self.readLog = readLog(self.cfg["log_path"], maxMisisons=self.cfg["buffer_maxMisisons"])
        self.readLog.pre_scan()
        
        
        self.mission_error_last = 0
        self.script_errors = deque(maxlen=10000)
        
        self.server_pid = None
        asyncio.ensure_future(self.on_ready())
       
        
        
    async def on_ready(self):
        try:
            await self.bot.wait_until_ready()
            self.CommandRcon = self.bot.cogs["CommandRcon"]
            self.channel = self.bot.get_channel(self.cfg["post_channel"])
            #if(self.channel):
            #    self.readLog.EH.add_Event("Mission script error", self.mission_script_error)
            asyncio.ensure_future(self.readLog.watch_log())
            asyncio.ensure_future(self.memory_guard())
        except Exception as e:
            traceback.print_exc()
            print(e)
    
    async def mission_script_error(self, *args):
        try:
            if(time() - self.mission_error_last < 60*10):
                return
            self.mission_error_last = time()
            regex = "Error in expression <(?P<expression>.*?)>.*?Error position: <(?P<position>.*?)>.*?Error Undefined variable in expression: (?P<err_cause>.*?)File (?P<file>.*?)\.\.\., line (?P<line>[0-9]*)"
            error = "".join(args[3])
            m = re.match(regex, error, flags=re.S)
            if m: 
                await self.channel.send("Error in expression```sqf\n{expression}```Error position:```sqf\n{position}```Error Undefined variable in expression: ``{err_cause}`` ``{file}``... line {line}\nAdditional Errors will be supressed for 10min.".format(**m.groupdict()))
            else:
                await self.channel.send("```sqf\n{}```".format(error))
            
        except Exception as e:
            traceback.print_exc()
            print(e)
    
    #triggers server restarts on high memory usage
    async def memory_guard(self):
        while True:
            if(self.cfg["server_memory_protection"]):
                if(psutil.virtual_memory().percent > 85):
                    await self.CommandRcon.arma_rcon.restartserveraftermission()
                    await self.CommandRcon.arma_rcon.sayGlobal("A Server restart has been scheduled at the end of this mission.")
                    await self.channel.send("Memory usage exceeded! Server restart scheduled after mission end")
                    print(":warning: Memory usage exceeded! Server restart scheduled after mission end")
                #elif(psutil.virtual_memory().percent > 95): #might be too agressive should short memory spikes occour
                #    await self.CommandRcon.arma_rcon.restartServer()
            await asyncio.sleep(10*60)
        
###################################################################################################
#####                              Arma 3 Server start - stop                                  ####
###################################################################################################         
    def start_server(self):
        
        #subprocess.call(shlex.split(self.CommandRcon.rcon_settings["start_server"]))  
        self.server_pid = subprocess.Popen(shlex.split(self.cfg["start_server"]))  
        
    def stop_server(self, pid=-1):
        if(self.server_pid != None):
            self.server_pid.kill()
            self.server_pid = None
        elif(pid>=0):
            try:
                os.kill(pid, 0)
            except SystemError as e:
                pass
            print("Terminated process", pid)
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
    async def stop(self, ctx, pid=-1):
        self.CommandRcon.autoReconnect = False
        if(self.stop_server(pid)==False):
            await ctx.send("Failed to stop server. You might want to try '!stop_all' to stop all arma 3 instances")
        else:
            await ctx.send("Stopped the process.")      

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
                try:
                    mlist.append("{} {} {} ({} entries) {}".format(  mission["dict"]["Mission starting"][0], 
                                                    mission["dict"]["Mission world"][2].group(2), 
                                                    mission["dict"]["Mission file"][2].group(2),
                                                    len(mission["data"]),
                                                    mission["dict"]["Mission id"][2].group(2)))
                except KeyError:
                    if("Mission id" in mission["dict"]):
                        mlist.append("unknown mission {}".format(mission["dict"]["Mission id"][2].group(2)))
                    else:
                        mlist.append("unknown mission")
                    
        msg = "Recently played missions (new to old)\n"
        msg += "\n".join(mlist)
        await utils.sendLong(ctx, msg)  
  

def setup(bot):
    bot.add_cog(CommandArma(bot))