
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
from discord.utils import escape_markdown
import prettytable
import geoip2.database
import datetime
import shlex, subprocess
import psutil

import bec_rcon

from modules.core.utils import CommandChecker, RateBucket, CoreConfig
import modules.core.utils as utils
from modules.core.Log import log

class CommandRconSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.rcon_adminNotification = CoreConfig.cfg.new(self.path+"/rcon_notifications.json")
        self.server_pid = None
        asyncio.ensure_future(self.on_ready())
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.CommandRcon = self.bot.cogs["CommandRcon"]
        
###################################################################################################
#####                                   General functions                                      ####
###################################################################################################         
        
    async def sendPMNotification(self, id, keyword, msg):
        ctx = self.bot.get_user(int(id))
        
        userEle = self.getAdminSettings(id)
        if(userEle["muted"] == True):
            return
        #online idle dnd offline
        if(userEle["sendAlways"] == True or str(ctx.message.author.status) in ["online", "idle"]):
            #msg = "\n".join(message_list)
            msg = self.CommandRcon.generateChat(10)
            if(len(msg)>0 and len(msg.strip())>0):
                await utils.sendLong(ctx, "The Keyword '{}' was triggered: \n {}".format(keyword, msg))

    async def checkKeyWords(self, message):
        for id, value in self.rcon_adminNotification.items():
            if(value["muted"] == False):
                for keyword in value["keywords"]:
                    if(keyword.lower() in message.lower()):
                        await self.sendPMNotification(id, keyword, message)
                        break
                        
    def getAdminSettings(self, id): 
        if(str(id) not in  self.rcon_adminNotification):
             self.rcon_adminNotification[str(id)] = {}
        userEle = self.rcon_adminNotification[str(id)]

        if(not "keywords" in userEle):
            userEle["keywords"] = []
            userEle["muted"] = False
            userEle["sendAlways"] = True
        return userEle
 
###################################################################################################
#####                              Admin notification commands                                 ####
###################################################################################################  

    @CommandChecker.command(name='addKeyWord',
        brief="Add Keyword to Admin notifications (use '\_' as a space)",
        aliases=['addkeyword'],
        pass_context=True)
    async def addKeyWord(self, ctx, *keyword):
        keyword = " ".join(keyword)
        keyword = keyword.replace("\_", " ")
        userEle = self.getAdminSettings(ctx.message.author.id)
        userEle["keywords"].append(keyword)  
        self.rcon_adminNotification.json_save()
        await ctx.send("Added Keyword.")
    
    @CommandChecker.command(name='removeKeyWord',
        brief="Remove Keyword to Admin notifications  (use '\_' as a space)",
        aliases=['removekeyword'],
        pass_context=True)
    async def removeKeyWord(self, ctx, *keyword):
        keyword = " ".join(keyword)
        keyword = keyword.replace("\_", " ")
        id = ctx.message.author.id
        if(str(id) in  self.rcon_adminNotification and keyword in self.rcon_adminNotification[str(id)]["keywords"] ):
            self.rcon_adminNotification[str(id)]["keywords"].remove(keyword)
            await ctx.send("Removed Keyword.")
        else:
            await ctx.send("Keyword not found.")
        self.rcon_adminNotification.json_save()   

    @CommandChecker.command(name='listKeyWords',
        brief="Lists all your Keywords for Admin notifications",
        aliases=['listkeywords'],
        pass_context=True)
    async def listKeyWords(self, ctx):
        id = ctx.message.author.id
        if(str(id) in  self.rcon_adminNotification and len(self.rcon_adminNotification[str(id)]["keywords"])>0 ):
            keywords = "\n".join(self.rcon_adminNotification[str(id)]["keywords"])
            await utils.sendLong(ctx, "```{}```".format(keywords))
        else:
            await ctx.send("You dont have any keywords.")
        self.rcon_adminNotification.json_save()  

    @CommandChecker.command(name='setNotification',
        brief="Args = [mute, unmute, online, always]",
        aliases=['setnotification'],
        pass_context=True)
    async def setNotification(self, ctx, status):
        args = ["mute", "unmute", "online", "always"]
        await ctx.send("mute = Will never send you a message. \n unmute = allows me to send you a message. \n online = Sending a message only when you are online or AFK. \n always = Will always send you a message.")
        if(status in args):
            userEle = self.getAdminSettings(ctx.message.author.id)
            if(status == "mute"):
                userEle["muted"] == True
            else:
                userEle["muted"] == False
            if(status == "online"):
                userEle["sendAlways"] = False
            else:
                userEle["sendAlways"] = True
            await ctx.send("Your current settings are: muted: {}, sendAlways: {}".format(userEle["muted"] , userEle["sendAlways"]))
        else:
            await ctx.send("Invalid argument. Valid arguments are: [{}]".format(", ".join(args)))

        self.rcon_adminNotification.json_save() 
        
        
###################################################################################################
#####                                    Other commands                                        ####
###################################################################################################  

    @CommandChecker.command(name='debug',
        brief="Toggles RCon debug mode",
        pass_context=True)
    async def cmd_debug(self, ctx, value): 
        self.CommandRcon.arma_rcon.setlogging(value)
        msg= "Set debug mode to:"+str(value)
        await ctx.send(msg)     


class CommandRcon(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))

        self.arma_chat_channels = ["Side", "Global", "Vehicle", "Direct", "Group", "Command"]
        
        
        #Load cfg:
        self.rcon_settings = CoreConfig.cfg.new(  self.path+"/"+
                                        utils.Modules.settings_dir+"rcon.json", 
                                        self.path+"/"+
                                        utils.Modules.settings_dir+"rcon.default_json")
        CoreConfig.modules["modules/rcon"]["rcon"] = self.rcon_settings
        CoreConfig.registered.append(self.rcon_settings)
        
        self.lastReconnect = deque()
        self.ipReader = geoip2.database.Reader(self.path+"/GeoLite2-Country.mmdb")
        self.arma_rcon  = None
        
        asyncio.ensure_future(self.on_ready())
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.CommandRconSettings = self.bot.cogs["CommandRconSettings"]        
        self.RateBucket = RateBucket(self.streamMsg)
        
        try:
            self.CommandArma = self.bot.cogs["CommandArma"]
            self.readLog = self.CommandArma.readLog
        except KeyError:
            self.readLog = None
            self.CommandArma = None
            
        if("streamChat" in self.rcon_settings and self.rcon_settings["streamChat"] != None):
            self.streamChat = self.bot.get_channel(self.rcon_settings["streamChat"])
            #self.streamChat.send("TEST")
        else:
            self.streamChat = None
        
        self.setupRcon()
            
    def setupRcon(self, serverMessage=None):
        try:
            Events = None
            if self.arma_rcon:
                Events = self.arma_rcon.Events.copy()
            del self.arma_rcon 
            self.arma_rcon = bec_rcon.ARC(self.rcon_settings["ip"], 
                                     self.rcon_settings["password"], 
                                     self.rcon_settings["port"], 
                                     {'timeoutSec' : self.rcon_settings["timeoutSec"]}
                                    )
            if Events:
                #restore Event Handlers
                self.arma_rcon.Events = Events
            else:
                #Add Event Handlers
                self.arma_rcon.add_Event("received_ServerMessage", self.rcon_on_msg_received)
                self.arma_rcon.add_Event("on_disconnect", self.rcon_on_disconnect)
                
            if(serverMessage):
                self.arma_rcon.serverMessage = serverMessage
            else:   
                #Extend the chat storage
                data = self.arma_rcon.serverMessage.copy()
                self.arma_rcon.serverMessage = deque(maxlen=500) #Default: 100
                data.reverse()
                for d in data:
                    self.arma_rcon.serverMessage.append(d)
        except Exception as e:
            log.print_exc()
            log.error(e)
        
                
        
###################################################################################################
#####                                  common functions                                        ####
###################################################################################################
    
    #converts unicode to ascii, until utf-8 is supported by rcon
    def setEncoding(self, msg):
        return bytes(msg.encode()).decode("utf-8","replace") 
    
    def getPlayerFromMessage(self, message: str):
        if(":" in message):
            header, body = message.split(":", 1)
            if(self.isChannel(header)): #was written in a channel
                player_name = header.split(") ")[1]
                return player_name
        return False
        
    def isChannel(self, msg):
        for channel in self.arma_chat_channels:
            if(channel in msg):
                return True
        return False
    
    #check if there was chat activity by the player in the last [min] minutes
    def playerTypesMessage(self, player_name, min=25):
        data = self.arma_rcon.serverMessage.copy()
        data.reverse()
        for pair in data: #checks all recent chat messages
            msg = pair[1]
            diff = datetime.datetime.now() - pair[0]
            #cancel search if chat is older than 25min
            if(diff.total_seconds() > 0 and diff.total_seconds()/60 >= min): 
                break
            msg_player = self.getPlayerFromMessage(msg)
            if(msg_player != False and player_name == msg_player or 
               (" "+player_name+" disconnected") in msg or
               (player_name in msg and " has been kicked by BattlEye" in msg)): #if player wrote something return True
                return True
        return False
    
    async def streamMsg(self, message_list):
        msg = "\n".join(message_list)
        if(len(msg.strip())>0):
            await self.streamChat.send(msg)    
        
                    
###################################################################################################
#####                                BEC Rcon Event handler                                    ####
###################################################################################################  
    #function called when a new message is received by rcon
    def rcon_on_msg_received(self, args):
        message = discord.utils.escape_markdown(args[0], as_needed=True)

        if("CommandRconIngameComs" in self.bot.cogs):
            asyncio.ensure_future(self.bot.cogs["CommandRconIngameComs"].RconCommandEngine.parseCommand(args[0]))
        #example: getting player name
        if(":" in message):
            header, body = message.split(":", 1)
            if(self.isChannel(header)): #was written in a channel
                #check for admin notification keywords
                asyncio.ensure_future(self.CommandRconSettings.checkKeyWords(body))
                player_name = header.split(") ")[1]
                #log.info(player_name)
                #log.info(body)
            #else: is join or disconnect, or similar
            
                #check if the chat is streamed or not
                if(self.streamChat != None):
                    self.RateBucket.add(message)
    
        
    
    #event supports async functions
    #function is called when rcon disconnects
    async def rcon_on_disconnect(self):
        await asyncio.sleep(10)

        # cleanup old records
        try:
            while self.lastReconnect[0] < datetime.datetime.now() - datetime.timedelta(seconds=60):
                self.lastReconnect.popleft()
        except IndexError:
            pass # there are no records in the queue.
        if len(self.lastReconnect) > self.rcon_settings["max_reconnects_per_minute"]:
            log.warning("Stopped Reconnecting - Too many reconnects!")
            if(self.streamChat):
                await self.streamChat.send(":warning: Stopped Reconnecting - Too many reconnects!\n Reconnect with '!reconnect'")
        else:
            self.lastReconnect.append(datetime.datetime.now())
            log.info("Reconnecting to BEC Rcon")
            self.setupRcon(self.arma_rcon.serverMessage) #restarts form scratch (due to weird behaviour on reconnect)


    def generateChat(self, limit):
        msg = ""
        data = self.arma_rcon.serverMessage.copy()
        start = len(data)-1
        if(start > limit):
            end = start-limit
        else:
            end = 0
        i = end
        while(i<=start):
            pair = data[i]
            time = pair[0]
            msg += time.strftime("%H:%M:%S")+" | "+ pair[1]+"\n"
            i+=1
        return discord.utils.escape_markdown(msg, as_needed=True)

###################################################################################################
#####                                BEC Rcon custom commands                                  ####
###################################################################################################  
    @CommandChecker.command(name='reconnect',
        brief="Reconnects to the Rcon Server",
        aliases=['reconnectrcon'],
        pass_context=True)
    async def reconnectrcon(self, ctx): 
        if(self.arma_rcon.disconnected==True):
            self.setupRcon(self.arma_rcon.serverMessage)
            await ctx.send("Reconnected Rcon")   
        else:
            await ctx.send("Disconnecting and waiting for 45s before reconnecting...")
            await asyncio.sleep(46)
            self.setupRcon(self.arma_rcon.serverMessage)
            await ctx.send("Reconnected.")    
            
    @CommandChecker.command(name='disconnect',
        brief="Terminates the connection to Rcon",
        aliases=['disconnectrcon'],
        pass_context=True)
    async def disconnectrcon(self, ctx): 
        self.lastReconnect.append(datetime.datetime.now())
        self.arma_rcon.disconnect()
        await ctx.send("Disconnect Rcon")   
       
     
    @CommandChecker.command(name='streamChat',
        brief="Streams the arma 3 chat live into the current channel",
        aliases=['streamchat'],
        pass_context=True)
    async def stream(self, ctx): 
        self.streamChat = ctx
        self.rcon_settings["streamChat"] = ctx.message.channel.id
        
        await ctx.send("Streaming chat...")
    
    @CommandChecker.command(name='stopStream',
        brief="Stops the stream",
        aliases=['stopstream'],
        pass_context=True)
    async def streamStop(self, ctx): 
        self.streamChat = None
        self.rcon_settings["streamChat"] = None
        await ctx.send("Stream stopped")
            
    @CommandChecker.command(name='checkAFK',
        brief="Checks if a player is AFK (5min)",
        aliases=['checkafk'],
        pass_context=True)
    async def checkAFK(self, ctx, player_id: int): 
        players = await self.arma_rcon.getPlayersArray()
        player_name = None
        for player in players:
            if(int(player[0]) == player_id):
                player_name = player[4]
        if(player_name == None):
            await ctx.send("Player not found")
            return
        if(player_name.endswith(" (Lobby)")): #Strip lobby from name
            player_name = player_name[:-8]
        msg= "Starting AFK check for: ``"+str(player_name)+"``"
        await ctx.send(msg)  
        already_active = False
        for i in range(0, 300): #checks for 5min (10*30s)
            if(self.playerTypesMessage(player_name)):
                if(i==0):
                    already_active = True
                    await ctx.send("Player was recently active. Canceling AFK check.")  
                else:
                    await ctx.send("Player responded in chat. Canceling AFK check.")  
                if(already_active == False):
                    await self.arma_rcon.sayPlayer(player_id,  "Thank you for responding in chat.")
                return
            if((i % 30) == 0):
                try:
                    for k in range(0, 3):
                        await self.arma_rcon.sayPlayer(player_id, "Type something in chat or you will be kicked for being AFK. ("+str(round(i/30)+1)+"/10)")
                except: 
                    log.error("Failed to send command sayPlayer (checkAFK)")
            await asyncio.sleep(1)
        if(self.playerTypesMessage(player_name)):
            if(i==0):
                already_active = True
            await ctx.send("Player responded in chat. Canceling AFK check.")  
            if(already_active == False):
                try:
                    await self.arma_rcon.sayPlayer(player_id, "Thank you for responding in chat.")
                except:
                    log.error("Failed to send command sayPlayer")
            return
        else:
            await self.arma_rcon.kickPlayer(player_id, "AFK too long")
            await ctx.send("``"+str(player_name)+"`` did not respond and was kicked for being AFK") 

    @CommandChecker.command(name='status',
        brief="Current connection status",
        pass_context=True)
    async def status(self, ctx, limit=20): 
        msg = ""
        if(self.arma_rcon.disconnected==False):
           msg+= "Connected to: "+ self.arma_rcon.serverIP+"\n"
        else:
            msg+= "Currently not connected: "+ self.arma_rcon.serverIP+"\n"
        msg+= str(len(self.arma_rcon.serverMessage))+ " Messages collected"
        await ctx.send(msg) 
            
    @CommandChecker.command(name='getChat',
        brief="Get the last ingame chat messages",
        aliases=['getchat'],
        pass_context=True)
    async def getChat(self, ctx, limit=20): 
        msg = self.generateChat(limit)
        await utils.sendLong(ctx, msg)

    @CommandChecker.command(name='players+',
        brief="Lists current players on the server",
        pass_context=True)
    async def playersPlus(self, ctx):
        players = await self.arma_rcon.getPlayersArray()

        limit = 100
        i = 1
        new = False
        msg  = "Players: \n"
        for player in players:
            if(i <= limit):
                id,ip,ping,guid,name = player
                
                if(self.playerTypesMessage(name)):
                    active = ":green_circle:"
                else:
                    active = ":white_circle:"
                #fetch country
                try:
                    response = self.ipReader.country(ip.split(":")[0])
                    region = str(response.country.iso_code).lower()
                except:
                    region = ":question:"
                    
                if(region == "none"):
                    flag = ":question:" #symbol if no country was found
                else:
                    flag = ":flag_{}:".format(region)
                msg+= "{}#{} | {} {}".format(active, id, flag, discord.utils.escape_markdown(name, as_needed=True))+"\n"

        await utils.sendLong(ctx, msg)
        
###################################################################################################
#####                                   BEC Rcon commands                                      ####
###################################################################################################    

    @CommandChecker.command(name='command',
        brief="Sends a custom command to the server",
        help="Executes any command by directly sending the input to the server. Will return if the command was executed. For example '!command say -1 hello' will send a global message", 
        pass_context=True)
    async def command(self, ctx, *message): 
        message = " ".join(message)
        message = self.setEncoding(message)
        data = await self.arma_rcon.command(message)
        if(len(data) == 0):
            msg = "Executed command: ``"+str(message)+"`` and returned nothing (confirmed its execution)"
        else:
            msg = "Executed command: ``"+str(message)+"`` wich returned: "+str(data)
        await utils.sendLong(ctx,msg)

    @CommandChecker.command(name='kickPlayer',
        brief="Kicks a player who is currently on the server",
        aliases=['kickplayer'],
        pass_context=True)
    async def kickPlayer(self, ctx, player_id: int, *message): 
        message = " ".join(message)
        message = self.setEncoding(message)
        await self.arma_rcon.kickPlayer(player_id, message)
            
        msg = "kicked player: "+str(player_id)
        await ctx.send(msg)

    @CommandChecker.command(name='say',
        brief="Sends a global message",
        pass_context=True)
    async def sayGlobal(self, ctx, *message): 
        name = ctx.message.author.name
        message = " ".join(message)
        message = self.setEncoding(message)
        await self.arma_rcon.sayGlobal(name+": "+message)
        msg = "Send: ``"+message+"``"
        await ctx.send(msg)    

    @CommandChecker.command(name='sayPlayer',
        brief="Sends a message to a specific player",
        aliases=['sayplayer', 'sayp'],
        pass_context=True)
    async def sayPlayer(self, ctx, player_id: int, *message): 
        message = " ".join(message)
        message = self.setEncoding(message)
        name = ctx.message.author.name
        if(len(message)<2):
            message = "Ping"
        await self.arma_rcon.sayPlayer(player_id, name+": "+message)
        msg = "Send msg: ``"+str(player_id)+"``"+message
        await ctx.send(msg)

    @CommandChecker.command(name='loadScripts',
        brief="Loads the 'scripts.txt' file without the need to restart the server",
        aliases=['loadscripts'],
        pass_context=True)
    async def loadScripts(self, ctx): 
        await self.arma_rcon.loadScripts()
        msg = "Loaded Scripts!"
        await ctx.send(msg)        

    @CommandChecker.command(name='loadEvents',
        aliases=['loadevents'],
        brief="Loads Events",
        pass_context=True)
    async def loadEvents(self, ctx): 
        await self.arma_rcon.loadEvents()
        msg = "Loaded Events!"
        await ctx.send(msg)    

    @CommandChecker.command(name='maxPing',
        brief="Changes the MaxPing value. If a player has a higher ping, he will be kicked from the server",
        aliases=['maxping'],
        pass_context=True)
    async def maxPing(self, ctx, ping: int): 
        await self.arma_rcon.maxPing(ping)
        msg = "Set maxPing to: "+ping
        await ctx.send(msg)       

    @CommandChecker.command(name='changePassword',
        brief="Changes the RCon password",
        aliases=['changepassword'],
        pass_context=True)
    async def changePassword(self, ctx, *password): 
        password = " ".join(password)
        await self.arma_rcon.changePassword(password)
        msg = "Set Password to: ``"+password+"``"
        await ctx.send(msg)        

    @CommandChecker.command(name='loadBans',
        brief="(Re)load the BE ban list from bans.txt",
        aliases=['loadbans'],
        pass_context=True)
    async def loadBans(self, ctx): 
        await self.arma_rcon.loadBans()
        msg = "Loaded Bans!"
        await ctx.send(msg)    


    @CommandChecker.command(name='players',
        brief="Lists current players on the server",
        pass_context=True)
    async def players(self, ctx):
        players = await self.arma_rcon.getPlayersArray()
        msgtable = prettytable.PrettyTable()
        msgtable.field_names = ["ID", "Name", "IP", "GUID"]
        msgtable.align["ID"] = "r"
        msgtable.align["Name"] = "l"
        msgtable.align["IP"] = "l"
        msgtable.align["GUID"] = "l"

        limit = 100
        i = 1
        new = False
        msg  = ""
        for player in players:
            if(i <= limit):
                msgtable.add_row([player[0], discord.utils.escape_markdown(player[4], as_needed=True), player[1],player[3]])
                if(len(str(msgtable)) < 1800):
                    i += 1
                    new = False
                else:
                    msg += "```"
                    msg += str(msgtable)
                    msg += "```"
                    await ctx.send(msg)
                    msgtable.clear_rows()
                    msg = ""
                    new = True
        if(new==False):
            msg += "```"
            msg += str(msgtable)
            msg += "```"
            await ctx.send(msg)    

    @CommandChecker.command(name='admins',
        brief="Lists current admins on the server",
        pass_context=True)
    async def admins(self, ctx):
        admins = await self.arma_rcon.getAdminsArray()
        msgtable = prettytable.PrettyTable()
        msgtable.field_names = ["ID", "IP"]
        msgtable.align["ID"] = "r"
        msgtable.align["IP"] = "l"

        limit = 100
        i = 1
        new = False
        msg  = ""
        for admin in admins:
            if(i <= limit):
                msgtable.add_row([admin[0], admin[1]])
                if(len(str(msgtable)) < 1800):
                    i += 1
                    new = False
                else:
                    msg += "```"
                    msg += str(msgtable)
                    msg += "```"
                    await ctx.send(msg)
                    msgtable.clear_rows()
                    msg = ""
                    new = True
        if(new==False):
            msg += "```"
            msg += str(msgtable)
            msg += "```"
            await ctx.send(msg)  
            
    @CommandChecker.command(name='getMissions',
        brief="Gets a list of all Missions",
        aliases=['getmissions'],
        pass_context=True)
    async def getMissions(self, ctx):
        missions = await self.arma_rcon.getMissions()
        await utils.sendLong(ctx, missions)
        
    @CommandChecker.command(name='loadMission',
        brief="Loads a mission",
        aliases=['loadmission'],
        pass_context=True)
    async def loadMission(self, ctx, mission: str):
        if(mission.endswith(".pbo",-4)): #Strips PBO
            mission = mission[:-4]
        await self.arma_rcon.loadMission(mission)
        msg = "Loaded mission: ``"+str(missions)+"``"
        await ctx.send(msg)  
    
    @CommandChecker.command(name='banPlayer',
        brief="Ban a player with his player id from the server.",
        help="Kicks and Bans a player with the specifed BE player id (usually 0-100)",
        aliases=['banplayer'],
        pass_context=True)
    async def banPlayer(self, ctx, player_id, time=0, *message): 
        message = " ".join(message)
        message = self.setEncoding(message)
        if(len(message)<2):
            await self.arma_rcon.banPlayer(player=player, time=time)
        else:
            await self.arma_rcon.banPlayer(player, message, time)
            
        msg = "Banned player: ``"+str(player)+" - "+matches[0]+"`` with reason: "+message
        await ctx.send(msg)    
        
    @CommandChecker.command(name='addBan',
        brief="Ban a player with GUID (even if they are offline)",
        aliases=['addban'],
        help="Adds a ban to the ban (GUID) list",
        pass_context=True)
    async def addBan(self, ctx, GUID: str, time=0, *message): 
        message = " ".join(message)
        message = self.setEncoding(message)
        matches = ["?"]
        if(len(GUID) != 32):
            raise Exception("Invalid GUID")
        if(len(message)<2):
            await self.arma_rcon.addBan(guid=GUID, time=time)
        else:
            await self.arma_rcon.addBan(GUID, message, time)
            
        msg = "Banned player: ``"+str(GUID)+" - "+matches[0]+"`` with reason: "+message

    @CommandChecker.command(name='removeBan',
        brief="Removes a ban",
        aliases=['removeban'],
        pass_context=True)
    async def removeBan(self, ctx, banID: int): 
        await self.arma_rcon.removeBan(banID)
            
        msg = "Removed ban: ``"+str(banID)+"``"
        await ctx.send(msg)    
        
    @CommandChecker.command(name='getBans',
        brief="Lists the most recent bans",
        aliases=['getbans'],
        pass_context=True)
    async def getBans(self, ctx): 
        bans = await self.arma_rcon.getBansArray()
        bans.reverse() #news bans first
        msgtable = prettytable.PrettyTable()
        msgtable.field_names = ["ID", "GUID", "Time", "Reason"]
        msgtable.align["ID"] = "r"
        msgtable.align["IP"] = "l"
        msgtable.align["GUID"] = "l"

        limit = 20
        i = 1
        new = False
        msg  = ""
        for ban in bans:
            if(i <= limit):
                if(len(str(msgtable)) < 1700):
                    msgtable.add_row([ban[0], ban[1], ban[2],ban[3]])
                    i += 1
                    new = False
                else:
                    msg += "```"
                    msg += str(msgtable)
                    msg += "```"
                    await ctx.send(msg)
                    msgtable.clear_rows()
                    msg = ""
                    new = True
        if(new==False):
            msg += "```"
            msg += str(msgtable)
            msg += "```"
            await ctx.send(msg)   
        if(i>=limit):
            msg = "Limit of "+str(limit)+" reached. There are still "+str(len(bans)-i)+" more bans"
            await ctx.send(msg)   
            
    @CommandChecker.command(name='getBEServerVersion',
        brief="Gets the current version of the BE server",
        aliases=['beversion', 'BEversion', 'BEVersion'],
        pass_context=True)
    async def getBEServerVersion(self, ctx): 
        version = await self.arma_rcon.getBEServerVersion()
        msg = "BE version: ``"+str(version)+"``"
        await ctx.send(msg)         
        
    @CommandChecker.command(name='lock',
        brief="Locks the server. No one will be able to join",
        pass_context=True)
    async def lock(self, ctx): 
        data = await self.arma_rcon.lock()
        msg = "Locked the Server"
        await ctx.send(msg)    

    @CommandChecker.command(name='unlock',
        brief="Unlocks the Server",
        pass_context=True)
    async def unlock(self, ctx): 
        data = await self.arma_rcon.unlock()
        msg = "Unlocked the Server"
        await ctx.send(msg)       

    @CommandChecker.command(name='shutdown',
        brief="Shutdowns the Server",
        pass_context=True)
    async def shutdown(self, ctx): 
        data = await self.arma_rcon.shutdown()
        msg = "Shutdown the Server"
        await ctx.send(msg)           

    @CommandChecker.command(name='restart',
        brief="Restart mission with current player slot selection",
        pass_context=True)
    async def restart(self, ctx): 
        data = await self.arma_rcon.restart()
        msg = "Restarting the Mission"
        await ctx.send(msg)          

    @CommandChecker.command(name='restartServer',
        brief="Shuts down and restarts the server immediately",
        pass_context=True)
    async def restartServer(self, ctx): 
        data = await self.arma_rcon.restartServer()
        msg = "Restarting the Server"
        await ctx.send(msg)           

    @CommandChecker.command(name='restartM',
        brief="Shuts down and restarts the server after mission ends",
        pass_context=True)
    async def restartserveraftermission(self, ctx): 
        data = await self.arma_rcon.restartserveraftermission()
        msg = "Restarting the Server after mission ends"
        await ctx.send(msg)       

    @CommandChecker.command(name='shutdownM',
        brief="Shuts down the server after mission ends",
        pass_context=True)
    async def shutdownserveraftermission(self, ctx): 
        data = await self.arma_rcon.shutdownserveraftermission()
        msg = "Shuting down the Server after mission ends"
        await ctx.send(msg)       

    @CommandChecker.command(name='reassign',
        brief="Sends all players back to the lobby and unslots them",
        pass_context=True)
    async def reassign(self, ctx): 
        data = await self.arma_rcon.reassign()
        msg = "All users are send back to the lobby"
        await ctx.send(msg)          

    @CommandChecker.command(name='monitords',
        brief="Shows performance information in the dedicated server console. Tracks the performance for 10s",
        pass_context=True)
    async def monitords(self, ctx,): 
        if(not self.readLog):
            raise Exception("Arma module required, but not loaded!")
    
        async def sendLoad(event, timestamp, msg, event_match):
            await ctx.send(msg)
 
        self.readLog.EH.add_Event("Server load", sendLoad)
        await self.arma_rcon.monitords(1)
        await asyncio.sleep(5)
        await self.arma_rcon.monitords(0)
        self.readLog.EH.remove_Event("Server load", sendLoad)
        
    @CommandChecker.command(name='goVote',
        brief="Users can vote for the mission selection.",
        aliases=['govote'],
        pass_context=True)
    async def goVote(self, ctx): 
        data = await self.arma_rcon.goVote()
        msg = "Sending users to vote for next mission"
        await ctx.send(msg)          



def setup(bot):
    bot.add_cog(CommandRcon(bot))
    bot.add_cog(CommandRconSettings(bot))