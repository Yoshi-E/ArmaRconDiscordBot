
# Work with Python 3.6
import asyncio
from collections import Counter
import json
import os
from .playerMapGenerator import playerMapGenerator
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
import ast
import sys
import traceback
import urllib.parse
import threading
import datetime

from modules.core.utils import CommandChecker, sendLong, CoreConfig
from modules.rcon_jmw.process_log import ProcessLog
from modules.core.Log import log

class CommandJMW(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        self.cfg = CoreConfig.modules["modules/rcon_jmw"]["general"]
        
        self.user_data = {}
        if(os.path.isfile(self.path+"/userdata.json")):
            self.user_data = json.load(open(self.path+"/userdata.json","r"))
        
        asyncio.ensure_future(self.on_ready())
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        try:
            self.CommandRcon = self.bot.cogs["CommandRcon"]
            self.CommandArma = self.bot.cogs["CommandArma"]
            
            self.processLog = ProcessLog(self.CommandArma.readLog, self.cfg)
            self.processLog.readLog.EH.add_Event("Mission readname", self.gameStart)
            self.processLog.readLog.EH.add_Event("Mission finished", self.gameEnd)
            #self.processLog.EH.add_Event("on_missionHeader", self.gameStart)
            #self.processLog.EH.add_Event("on_missionGameOver", self.gameEnd)
           
            #self.processLog.readLog.pre_scan()
            # log.info(len(self.processLog.readLog.Missions))
            # for m in self.processLog.readLog.Missions:
                # if("Mission id" in m["dict"]):
                    # log.info(len(m["data"]), len(self.processLog.processGameBlock(m)), m["dict"]["Mission id"])
            
            #--> working correctly
            # log.info("#"*20)
            # for e in list(self.processLog.readLog.dataRows)[-100:]:
                # log.info(e[1])
                
                
            # game = self.processLog.readLog.Missions_current
            # game = self.processLog.processGameBlock(game)
            # log.info(len(game))  
            # for i in range(8):
                # try:
                    # game = self.processLog.buildGameBlock(i)
                    # game = self.processLog.processGameBlock(game)
                    # log.info(len(game))      
                # except IndexError:
                    # log.info("Game '{}' not found".format(i))
            #log.info(self.processLog.readData(False, 0))
            
            self.playerMapGenerator = playerMapGenerator(self.cfg["data_path"])
        except Exception as e:
            log.print_exc()
            log.error(e)
        
        
###################################################################################################
#####                                  common functions                                        ####
###################################################################################################
    async def task_setStatus(self):
        #while True:
            try:
                await asyncio.sleep(60)
                await self.setStatus()
            except (KeyboardInterrupt, asyncio.CancelledError):
                log.info("[asyncio] exiting", task_setStatus)
            except Exception as e:
                log.error("setting status failed", e)
                log.print_exc()

                
    async def setStatus(self):
        game = ""
        status = discord.Status.do_not_disturb #discord.Status.online
        
        if(not self.processLog):
            return
        #get current Game data
        try:
            meta, game, dict = self.processLog.generateGame()
        except EOFError:
            return #No valid logs found, just return

        last_packet = None
        for packet in reversed(game):
            if(packet["CTI_DataPacket"]=="Data"):
                last_packet = packet
                break
        
        #fetch data
        time_running = 0
        if(last_packet != None and "time" in last_packet and packet["time"] > 0):
            time_running = round(packet["time"]/60)  
            if "mission start time" not in self.CommandArma.serverStateInfo:
                self.CommandArma.serverStateInfo["mission start time"] = datetime.datetime.now() - datetime.timedelta(minutes=time_running)            
                self.CommandArma.serverStateInfo["mission state"] = "playing"    
        winner = "currentGame"
        if("winner" in meta):
            winner = meta["winner"]   
        
        #Get players
        players = 0
        if(last_packet != None and "players" in last_packet):
            players = len(packet["players"])
        
        #Get Map
        map = "unknown"
        starting_time = None
        if("map" in meta):
            map = meta["map"]

        elif("Mission world" in dict):
            map = dict["Mission world"][2].group(2)
            #Get Starting time
            starting_time = dict["Mission world"][0]
            
            
        if( map!="unknown" 
            and ("world" in self.CommandArma.serverStateInfo
            and self.CommandArma.serverStateInfo["world"][1] == 0) 
            or "world" not in self.CommandArma.serverStateInfo):
            self.CommandArma.serverStateInfo["world"] = (map, 0)
        
        
        
        #set checkRcon status
        game_name = "..."
        if("CommandRcon" in self.bot.cogs):
            if(self.CommandRcon.arma_rcon.disconnected==False):
                status = discord.Status.online
                
                if(winner!="currentGame" or last_packet == None or game[-1]["CTI_DataPacket"]=="GameOver" or "Mission starting" not in self.processLog.readLog.Missions[-1]["dict"]):
                    game_name = "Lobby"
                else:
                    game_name = "{} {}min {}".format(map, time_running, players)
                    if(players!=1):
                        game_name+="players"
                    else:
                        game_name+="player"
            else:
                status = discord.Status.do_not_disturb
        else:
            status = discord.Status.online
            game_name = "Online"
 
        if(self.cfg["set_custom_status"]==False):
            return
        if(self.bot.is_closed()):
            return False
        await self.bot.change_presence(activity=discord.Game(name=game_name), status=status)
        
    
    async def set_user_data(self, user_id=0, field="", data=[]):
        if(user_id != 0):
            self.user_data[user_id] = {field: data}
        #save data
        with open(self.path+"/userdata.json", 'w') as outfile:
            json.dump(self.user_data, outfile, sort_keys=True, indent=4, separators=(',', ': '))
    
    async def dm_users_new_game(self):
        if(self.bot.is_closed()):
            return False
        msg = "A game just ended, now is the best time to join for a new game!"
        for user in self.user_data:
            if "nextgame" in self.user_data[user] and self.user_data[user]["nextgame"] == True:
                log.info("sending DM to: "+str(user))
                puser = self.bot.get_user(int(user))
                await puser.send(msg)  
                self.user_data[user]["nextgame"] = False
        await self.set_user_data() #save changes
    
    async def processGame(self, channel, admin=False, gameindex=0, sendraw=False):
        if(self.bot.is_closed()):
            return False
        try:
            game = self.processLog.readData(admin, gameindex)   
            timestamp = game["date"]+" "+game["time"]
            msg="Sorry, I could not find any games"
            if(admin == True): #post additional info
                if(game["gameduration"] < 2):
                    gameindex+=1
                    await channel.send("Selected game is too short, displaying lastgame="+str(gameindex)+" instead")
                    game = self.processLog.readData(admin, gameindex)  
                filename = game["picname"]
                if(sendraw == True):
                    filename = game["dataname"]
                log_graph = filename
                msg="["+timestamp+"] "+str(game["gameduration"])+"min game. Winner:"+game["lastwinner"]
                msg += "\n<http://www.jammywarfare.eu/replays/?file={}>".format(urllib.parse.quote(game["picname"].split("/")[-1].replace(".png", ".json")))
                await channel.send(file=discord.File(log_graph), content=msg)
                com_east = "EAST_com:"+str(Counter(self.processLog.featchValues(game["data"], "commander_east")))
                com_west = "WEST_com:"+str(Counter(self.processLog.featchValues(game["data"], "commander_west")))
                await channel.send(com_east)
                await channel.send(com_west)
            else: #normal dislay
                if(game["gameduration"]<30):
                    if(game["gameduration"]<10):
                        game["gameduration"] = 10
                    if(game["lastwinner"] == "WEST"):
                        loser = "EAST"
                    else:
                        loser = "WEST"
                    msg="["+timestamp+"] "+"A "+str(game["gameduration"])+"min game was just finished because "+loser+" lost their HQ."
                    await channel.send(msg)
                else:
                    msg="["+timestamp+"] Congratulation, "+game["lastwinner"]+"! You beat the other team after "+str(game["gameduration"])+"min of intense fighting. A new game is about to start, time to join!"
                    filename = game["picname"]
                    log_graph = filename
                    msg += "\n<http://www.jammywarfare.eu/replays/?file={}>".format(urllib.parse.quote(game["picname"].split("/")[-1].replace("-CUR", "").replace("-ADV", "").replace(".png", ".json")))
                    #http://www.jammywarfare.eu/replays/?file=2020-06-17%2310-53-00%23195%23EAST%23Altis%23.json
                    #http://www.jammywarfare.eu/replays/?file=/home/arma/scripts/jmwBOT/modules/jmw/images/2020-06-18%2317-06-40%23285%23currentGame%23Altis%23-CUR-ADV.png
                    await channel.send(file=discord.File(log_graph), content=msg)

        except Exception as e:
            log.print_exc()
            await channel.send("Unable to find game: "+str(e))   

    async def processOldGame(self, channel, admin=False, gameindex=0, sendraw=False):
        if(self.bot.is_closed()):
            return False
        if(gameindex<=0):
            return await self.processGame(channel, admin, 0, sendraw)
        try:
            #get list of old game files
            path = self.cfg['image_path']
            ignore = ["-CUR", "currentGame"] #log files that will be ignored
            if(os.path.exists(path)):
                files = []
                for file in os.listdir(path):
                    if ((file.endswith(".png") and "-ADV" in file) and not any(x in file for x in ignore)):
                        files.append(file)
                files = sorted(files, reverse=True)
            else:
                files = []
            
            if(gameindex > len(files)):
                msg="Sorry, I could not find any games"
                await channel.send(com_west)
                return
                
           
            picname = files[gameindex-1]
            print(picname)
            gamefile = picname.replace(".png", ".json")
            timestamp = " ".join(picname.split("#")[:2])
            gameduration = picname.split("#")[2]
            lastwinner = picname.split("#")[3]
            
            if(sendraw == True):
                filename = self.cfg['data_path']+gamefile
            else:
                filename = self.cfg['image_path']+picname
            msg="["+timestamp+"] "+str(gameduration)+"min game. Winner:"+lastwinner
            msg += "\n<http://www.jammywarfare.eu/replays/?file={}>".format(urllib.parse.quote(gamefile))
            await channel.send(file=discord.File(filename), content=msg)

        except Exception as e:
            log.print_exc()
            await channel.send("An error occurred: "+str(e))

    


    async def gameEnd(self, *args):
        #log.info("GAMESTART")
        if(self.bot.is_closed()):
            return False
        channel = self.bot.get_channel(int(self.cfg["post_channel"]))
        await self.dm_users_new_game()
        await self.processGame(channel)
        self.processLog.readData(True, 0) #Generate advaced data as well, for later use.  
        
    async def gameStart(self, *args):
        if(self.bot.is_closed()):
            return False
        channel = self.bot.get_channel(int(self.cfg["post_channel"]))
        msg="Let the game go on! The Server is now continuing the mission."
        await channel.send(msg)
        
    ###################################################################################################
    #####                                   Bot commands                                           ####
    ###################################################################################################

    @CommandChecker.command(  name='ping',
                        pass_context=True)
    async def command_ping(self, ctx, *args):
        msg = 'Pong!'
        await ctx.send(msg)
    

    ####################################
    #Game tools                        #
    ####################################
    @CommandChecker.command(  name='nextgame',
                        brief="You'll receive a DM when a game has ended",
                        description="Send 'nextgame stop' to stop the notification",
                        pass_context=True)
    async def command_nextgame(self, ctx):
        message = ctx.message
         #get user ID
        if hasattr(message, 'author'):
            tauthor = message.author.id
        else:
            tauthor = message.channel.user.id
        if(" " in message.content):
            val = message.content.split(" ")[1]
            if(val=="stop"):
                await self.set_user_data(str(tauthor), "nextgame" , False)
                msg = ':x: Ok, I will send no message'
            else:
                msg = ':question: Sorry, I did not understand'
        else:
            #store data, to remind user later on
            await self.set_user_data(str(tauthor), "nextgame" , True)
            msg = ':white_check_mark: Ok, I will send you a message when you can join for a new round.'
        puser = self.bot.get_user(tauthor)
        await puser.send(msg)  

        
    @CommandChecker.command(  name='lastgame',
                        brief="Posts a summary of select game",
                        description="Takes up to 2 arguments, 1st: index of the game, 2nd: sending 'normal'",
                        pass_context=True)
    async def command_lastgame(self, ctx, index=0, admin = "yes"):
        message = ctx.message
        if(admin=="yes"):
            admin = True
        else: 
            admin = False
        await self.processOldGame(message.channel, admin, index)

    # @CommandChecker.command(  name='lastdata',
                        # brief="sends the slected game as raw .json",
                        # description="Takes up to 2 arguments, 1st: index of the game, 2nd: sending 'normal'",
                        # pass_context=True)
    # async def command_lastdata(self, ctx, index=0):
        # message = ctx.message
        # admin = True
        # await self.processGame(message.channel, admin, index, True)
        
    @CommandChecker.command(name='dump',
        brief="dumps array data into a dump.json file",
        pass_context=True)
    async def dump(self, ctx):
        await ctx.send("Dumping {} packets to file".format(len(self.processLog.dataRows)))
        with open(self.path+"/dump.json", 'w') as outfile:
            json.dump(list(self.processLog.dataRows), outfile)      
    
    @CommandChecker.command(name='getData',
        brief="gets recent log entry (0 = first, -1 = last)",
        aliases=['getdata'],
        pass_context=True)
    async def getData(self, ctx, index=0):
        msg = "There are {} packets: ```{}```".format(len(self.processLog.dataRows), self.processLog.dataRows[index])
        await sendLong(ctx,msg)    
        
    @CommandChecker.command(name='heatmap',
        brief="generates a heatmap of a select player",
        aliases=['heatMap'],
        pass_context=True)
    async def heatmap(self, ctx, map, *player_name):
        await sendLong(ctx,"Generating data...")
        
        player_name = " ".join(player_name)
        if(len(player_name)==0):
            player_name = "all"
        
        t = threading.Thread(target=self.heatmap_helper, args=[ctx, player_name, map, 16])
        t.start()
        
    def heatmap_helper(self, ctx, player_name, map="Altis", sigma=16):
        virtualFile = self.playerMapGenerator.generateMap(player_name, map=map, sigma=16)
        if(virtualFile == False):
            asyncio.run_coroutine_threadsafe(sendLong(ctx,"No data found"), self.bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(ctx.send(content="Map for {}".format(player_name), file=discord.File(virtualFile, 'heatmap{}'.format(".jpg"))), self.bot.loop)
        
    @CommandChecker.command(name='heatmapA',
        brief="generates a heatmap of a select player",
        aliases=['heatmapa'],
        pass_context=True)
    async def heatmapA(self, ctx, map, *player_name):
        await sendLong(ctx,"Generating data...")
        
        player_name = " ".join(player_name)
        if(len(player_name)==0):
            player_name = "all"
        
        t = threading.Thread(target=self.heatmap_helper, args=[ctx, player_name, map, 8])
        t.start()
            
    @CommandChecker.command(name='r',
        brief="terminates the bot",
        pass_context=True)
    async def setRestart(self, ctx):
        await ctx.send("Restarting...")
        sys.exit()     
                  
                
    @CommandChecker.command(name='eval',
        brief="Evluate a py expression",
        pass_context=True)
    async def evaluate(self, ctx, *expression):
        inp = " ".join(expression)
        log.info("exec '{}'".format(inp))
        data = str(exec(inp, {'bot': self.bot, 'logp': self.processLog}))
        #await ctx.send("```py\n{}```".format(data)) 
    
    @CommandChecker.command(name='dumpres',
        brief="Dumps the recent system performance into a json file",
        pass_context=True)
    async def dumpsysres(self, ctx):
        filename = "sys_performance.json"
        with open(filename, 'w') as outfile:
            json.dump(list(self.processLog.system_res), outfile)
        
        await ctx.send("Saved System data to '{}' ({} entries)".format(filename, len(self.processLog.system_res))) 
                  
    
def setup(bot):
    module = CommandJMW(bot)
    bot.loop.create_task(module.task_setStatus())
    bot.add_cog(module)
    