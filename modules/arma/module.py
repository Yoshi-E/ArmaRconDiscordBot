
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
from modules.core.Log import log
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
        self.memoryRestart = False
        
        self.mission_error_last = 0
        self.mission_error_suppressed = 0
        self.script_errors = deque(maxlen=10000)
        
        self.server_pid = None
        asyncio.ensure_future(self.on_ready())
       
        
        
    async def on_ready(self):
        try:
            await self.bot.wait_until_ready()
            self.CommandRcon = self.bot.cogs["CommandRcon"]
            self.channel = self.bot.get_channel(int(self.cfg["post_channel"]))
            if(self.cfg["report_script_errors"] and self.channel):
                self.readLog.EH.add_Event("Mission script error", self.mission_script_error)
                self.readLog.EH.add_Event("Server sessionID", self.serverRestarted)
            asyncio.ensure_future(self.readLog.watch_log())
            asyncio.ensure_future(self.memory_guard())
        except Exception as e:
            log.print_exc()
            log.error(e)
    
    async def serverRestarted(self, oldLog, newLog):
        if(self.memoryRestart == True):
            await self.channel.send("Server restarted.")
            self.memoryRestart = False
    
    async def mission_script_error(self, event, stime, text, regxm, line):
        try:
            if(time() - self.mission_error_last < 60*10):
                self.mission_error_suppressed += 1
                return
            self.mission_error_last = time()
            if(self.mission_error_suppressed > 0):
                await self.channel.send(":warning: {} Errors were suppressed\n``{}`` ``{}`` line ``{}``\nAdditional Errors will be suppressed for 10min.".format(self.mission_error_suppressed, text, self.readLog.current_log, line))
            else:    
                await self.channel.send(":warning: ``{}`` ``{}`` line ``{}``\nAdditional Errors will be suppressed for 10min.".format(text, self.readLog.current_log, line))
            self.mission_error_suppressed = 0
            
            
            #regex = "Error in expression <(?P<expression>.*?)>.*?Error position: <(?P<position>.*?)>.*?Error Undefined variable in expression: (?P<err_cause>.*?)File (?P<file>.*?)\.\.\., line (?P<line>[0-9]*)"
            #m = re.match(regex, error, flags=re.S)
            # if m: 
                # await self.channel.send("{}... line {}\nAdditional Errors will be suppressed for 10min.".format(text, line)
            # else:
                # await self.channel.send("```sqf\n{}```".format(error))
            
        except Exception as e:
            log.print_exc()
            log.error(e)
    
    #triggers server restarts on high memory usage
    async def memory_guard(self):
        while True:
            try:
                if(self.cfg["server_memory_protection"]):
                    if(psutil.virtual_memory().percent > 85):
                        await self.CommandRcon.arma_rcon.restartserveraftermission()
                        await self.CommandRcon.arma_rcon.sayGlobal("A Server restart has been scheduled at the end of this mission.")
                        if(self.memoryRestart == False):
                            await self.channel.send("Memory usage exceeded! Server restart scheduled after mission end")
                            self.memoryRestart = True
                        log.warning("Memory usage exceeded! Server restart scheduled after mission end")
                    #elif(psutil.virtual_memory().percent > 95): #might be too agressive should short memory spikes occour
                    #    await self.CommandRcon.arma_rcon.restartServer()
            except Exception as e:
                log.print_exc()
                log.error(e)
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
            log.info("Terminated process '{}'".format(pid))
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
        
    @CommandChecker.command(name='view',
            brief="View a snipped of a server log",
            pass_context=True)
    async def viewLog(self, ctx, logfile, line=0):
        #remove .. and / \
        logfile = logfile.replace("/", "")
        logfile = logfile.replace("\\", "")
        logfile = logfile.replace("..", "")
        if not(logfile.endswith(".log") or logfile.endswith(".rpt")):
            raise Exception("File must be a .log or .rpt file")
        path = self.readLog.log_path+logfile
        logAccumulated = ""
        sfile = open(path, "r")
        rowlimit = 30
        rows = 0
        linesCounter = 1
         
        for row in sfile:
            #discord limit = 2000
            if linesCounter >= line and len(logAccumulated) < 1000 and rows < rowlimit:
                logAccumulated += row
                rows += 1
            linesCounter += 1
        logAccumulated = logAccumulated[:1000]
        logAccumulated = logAccumulated[:logAccumulated.rfind("\n")]
        await ctx.send("```{}```".format(logAccumulated))      
        sfile.close()
        
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