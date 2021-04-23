
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
from modules.core.Log import log, _stdout_handler, _my_handler
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
        
        self.serverStateInfo = {}
        
        if not os.path.exists(self.path+"/logs/"):
            os.makedirs(self.path+"/logs/")
        self.mission_error_last = 0
        self.mission_error_suppressed = 0
        
        try:
            with open(self.path+"/logs/script_errors.log") as json_file:
                self.script_errors = json.load(json_file)
        except:
            self.script_errors = {}
        
        self.server_pid = None
        asyncio.ensure_future(self.on_ready())
       
        
    def test(self, msg):
        try:
            print(log)
            print(log.info)
            print(_my_handler)
            print(_stdout_handler)
            log.info(msg)
            log.warning(msg)
            log.error(msg)
            return "Sucess"
        except Exception as e:
            print(e)
    
    def testException(self):
        raise Exception("TEST")
    
    async def on_ready(self):
        try:
            await self.bot.wait_until_ready()
            self.CommandRcon = self.bot.cogs["CommandRcon"]
            self.channel = self.bot.get_channel(int(self.cfg["post_channel"]))
            if(self.cfg["report_script_errors"] and self.channel):
                self.readLog.EH.add_Event("Mission script error", self.mission_script_error)
                self.readLog.EH.add_Event("Server sessionID", self.serverRestarted)
                self.readLog.EH.add_Event("Mission world", self.MissionWorld)
                self.readLog.EH.add_Event("Mission started", self.MissionStarted)
                self.readLog.EH.add_Event("Mission finished", self.MissionFinished)
                self.readLog.EH.add_Event("Mission restarted", self.MissionFinished)
            asyncio.ensure_future(self.readLog.watch_log())
            asyncio.ensure_future(self.memory_guard())
            asyncio.ensure_future(self.saveErrors())
            asyncio.ensure_future(self.statusSetter())
        except Exception as e:
            log.print_exc()
            log.error(e)
    
    
###################################################################################################
#####                                    Mission Events                                        ####
###################################################################################################   


    def MissionFinished(self, event, payload):
        self.serverStateInfo["mission state"] = ("finished", time())        
        
    def MissionStarted(self, event, payload):
        self.serverStateInfo["mission state"] = ("started", time())    
        self.serverStateInfo["mission start time"] = datetime.datetime.now()
        
    def MissionWorld(self, event, payload):
        self.serverStateInfo["world"] = (payload["event_match"].group(2), time())    
    
        
    def Players(self, list):
        self.serverStateInfo["players"] = (list, time())
    
    async def serverRestarted(self, event, payload):
        if(self.memoryRestart == True):
            log.info("Server Restarted")
            await self.channel.send(":ballot_box_with_check: Server restarted.")
            self.memoryRestart = False
    
    async def mission_script_error(self, event, payload):
        try:    
            text = payload["msg"]
            line = payload["currentLinePos"]
            stime = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            if text in self.script_errors: 
                self.script_errors[text]["log"] = self.readLog.current_log
                self.script_errors[text]["line"] = line
                self.script_errors[text]["count"] += 1
                self.script_errors[text]["last"] = payload["timestamp"]
                self.script_errors[text]["positions"].append({"log": self.readLog.current_log, "line": line, "time": stime})
            else:
                self.script_errors[text] = {"log": self.readLog.current_log, "line": line, "count": 1, "last": stime, "positions": [{"log": self.readLog.current_log, "line": line, "time": stime}]}
                await self.channel.send(":warning: ``{}`` ``{}`` line ``{}``".format(text, self.readLog.current_log, line))
            

            self.mission_error_last = time()
        except Exception as e:
            log.print_exc()
            log.error(e)

###################################################################################################
#####                                         Other                                            ####
###################################################################################################   
    async def statusSetter(self):
        while True:
            try:
                if(self.cfg["set_custom_status"]):
                    await self.set_status()
            except Exception as e:
                log.print_exc()
                log.error(e)
            await asyncio.sleep(60)  
            
    async def set_status(self):
        players = None
        if("CommandRconDatabase" in self.bot.cogs):
            players = self.bot.cogs["CommandRconDatabase"].players
    
        game_name = ""
        if(players):
            game_name += "{} Players".format(len(players))
        
        if("mission state" in self.serverStateInfo and self.serverStateInfo["mission state"] == "finished"):
            game_name += " Lobby"
            
        if("world" in self.serverStateInfo and self.serverStateInfo["world"]):
            game_name += self.serverStateInfo["world"]
        
        if("mission start time" in self.serverStateInfo 
            and "mission state" in self.serverStateInfo 
            and self.serverStateInfo["mission state"] != "finished"):
            timedelta = datetime.datetime.now()-self.serverStateInfo["mission start time"]
            game_name += " {}min".format(round(timedelta.total_seconds()/60))
        
        if(game_name == ""):
            game_name = "Waiting..."

        status = discord.Status.do_not_disturb #discord.Status.online
        if(self.CommandRcon.arma_rcon.disconnected==False):
            status = discord.Status.online
        
        await self.bot.change_presence(activity=discord.Game(name=game_name), status=status)
    
    
    #triggers server shutdown on high memory usage
    async def saveErrors(self):
        while True:
            try:
                if((self.mission_error_last+60) < time()):
                    with open(self.path+"/logs/script_errors.log", 'w+') as outfile:
                        json.dump(self.script_errors, outfile, indent=4)
            except Exception as e:
                log.print_exc()
                log.error(e)
            await asyncio.sleep(60)    
            
    #triggers server shutdown on high memory usage
    async def memory_guard(self):
        while True:
            try:
                if(self.cfg["server_memory_protection"]):
                    if(psutil.virtual_memory().percent > 70):
                        await self.CommandRcon.arma_rcon.command("#shutdownaftermission")
                        await self.CommandRcon.arma_rcon.sayGlobal("A Server shutdown has been scheduled at the end of this mission.")
                        if(self.memoryRestart == False):
                            await self.channel.send(":warning: Memory usage exceeded! Server shutdown scheduled after mission end")
                            self.memoryRestart = True
                        log.warning(":warning: Memory usage exceeded! Server shutdown scheduled after mission end")
                    elif(psutil.virtual_memory().percent > 95): #might be too aggressive should short memory spikes occur
                        await self.CommandRcon.arma_rcon.shutdown()
                        log.warning(":warning: Memory usage exceeded! Server was forced shutdown")
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
            if linesCounter >= line-1 and len(logAccumulated) < 1000 and rows < rowlimit:
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
  
    @CommandChecker.command(name='viewErrors',
            brief="View recent script errors",
            aliases=['viewerrors'], 
            pass_context=True)
    async def viewErrors(self, ctx):
        msg = ""
        list = reversed(sorted(self.script_errors.items(), key=lambda item: item[1]["last"]))
        for key, item in list:
            msg += "``{}`` ``{}`` ``{}`` ({}) [{}]\n".format(key, item["log"], item["line"], item["count"], item["last"])
            if(len(msg)>1000):
                break
        await ctx.send(msg)     

    @CommandChecker.command(name='resetErrors',
            brief="Reset the error tracker",
            aliases=['reseterrors'], 
            pass_context=True)
    async def resetErrors(self, ctx):
        stime = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        if os.path.exists(self.path+"/logs/script_errors.log"):
            os.rename(self.path+"/logs/script_errors.log", self.path+"/logs/script_errors_{}.log".format(stime))
        self.script_errors = {}
        await ctx.send("Done!")  

def setup(bot):
    bot.add_cog(CommandArma(bot))