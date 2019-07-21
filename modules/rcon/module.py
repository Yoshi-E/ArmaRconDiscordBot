
# Works with Python 3.6
# Discord 1.2.2
import asyncio
from collections import Counter
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
from collections import deque
import time


import bec_rcon

new_path = os.path.dirname(os.path.realpath(__file__))+'/../core/'
if new_path not in sys.path:
    sys.path.append(new_path)
from utils import CommandChecker, RateBucket, CoreConfig

 
class CommandRcon(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.check_dependencies()

        self.arma_chat_channels = ["Side", "Global", "Vehicle", "Direct", "Group", "Command"]
        
        self.rcon_settings = self.gobal_cfg.new(self.path+"/rcon_cfg.json", self.path+"/rcon_cfg.default_json")
        
        self.ipReader = geoip2.database.Reader(self.path+"/GeoLite2-Country.mmdb")
        
        asyncio.ensure_future(self.on_ready())
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        self.RateBucket = RateBucket(self.streamMsg)
        if("streamChat" in self.rcon_settings and self.rcon_settings["streamChat"] > 0):
            self.streamChat = self.bot.get_channel(self.rcon_settings["streamChat"])
            #self.streamChat.send("TEST")
        else:
            self.streamChat = None
        
        self.setupRcon()
            
    def setupRcon(self, serverMessage=None):
        self.arma_rcon = bec_rcon.ARC(self.rcon_settings["ip"], 
                                 self.rcon_settings["password"], 
                                 self.rcon_settings["port"], 
                                 {'timeoutSec' : self.rcon_settings["timeoutSec"]}
                                )
        
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
###################################################################################################
#####                                  common functions                                        ####
###################################################################################################

    def check_dependencies(self):
                 #checking depencies 
        if("Commandconfig" in self.bot.cogs.keys()):
            self.gobal_cfg = self.bot.cogs["Commandconfig"].cfg
        else: 
            sys.exit("Module 'Commandconfig' not loaded, but required")
    
    #converts unicode to ascii, until utf-8 is supported by rcon
    def setEncoding(self, msg):
        return bytes(msg.encode()).decode("ascii","ignore") 
    
    #sends a message thats longer than what discord can handel
    async def sendLong(self, ctx, msg: str):
        discord_limit = 1900 #discord limit is 2000
        while(len(msg)>0): 
            if(len(msg)>discord_limit): 
                await ctx.send(msg[:discord_limit])
                msg = msg[discord_limit:]
            else:
                await ctx.send(msg)
                msg = ""
                
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
        
    def playerTypesMessage(self, player_name):
        data = self.arma_rcon.serverMessage.copy()
        data.reverse()
        for pair in data: #checks all recent chat messages
            msg = pair[1]
            diff = datetime.datetime.now() - pair[0]
            #cancel search if chat is older than 25min
            if(diff.total_seconds() > 0 and diff.total_seconds()/60 >= 25): 
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
        
    def escapeMarkdown(self, msg):
        #Markdown: *_`~#
        msg = msg.replace("*", "\*")
        msg = msg.replace("_", "\_")
        msg = msg.replace("`", "\`")
        msg = msg.replace("~", "\~")
        msg = msg.replace("#", "\#")
        return msg
###################################################################################################
#####                                   Bot commands                                           ####
###################################################################################################   
    def canUseCmds(ctx):
        roles = ["Admin", "Developer"] #Does not work in PMs for now
        admin_ids = [165810842972061697,  #can be used in PMS
                     218606481094737920, 
                     105981087590649856]
        print(ctx.message.author.name+"#"+str(ctx.message.author.id)+": "+ctx.message.content)
        if(ctx.author.id in admin_ids):
            return True
        if(hasattr(ctx.author, 'roles')):
            for role in ctx.author.roles:
                if(role in roles):
                    return True        
        return False
###################################################################################################
#####                                BEC Rcon Event handler                                    ####
###################################################################################################  
    #function called when a new message is received by rcon
    def rcon_on_msg_received(self, args):
        message=self.escapeMarkdown(args[0])
        #print(message) or post them into a discord channel
        if(":" in message):
            header, body = message.split(":", 1)
            if(self.isChannel(header)): #was written in a channel
                player_name = header.split(") ")[1]
                #print(player_name)
                #print(body)
            #else: is join or disconnect, or similaar
        if(self.streamChat != None):
            self.RateBucket.add(message)
    
        
    
    #event supports async functions
    #function is called when rcon disconnects
    async def rcon_on_disconnect(self):
        await asyncio.sleep(10)
        print("Reconnecting to BEC Rcon")
        self.setupRcon(self.arma_rcon.serverMessage) #restarts form scratch
        #self.arma_rcon.reconnect()
        
###################################################################################################
#####                                BEC Rcon custom commands                                  ####
###################################################################################################  
    @commands.check(canUseCmds)    
    @commands.command(name='streamChat',
        brief="Streams the arma 3 chat live into the current channel",
        pass_context=True)
    @CommandChecker.check
    async def stream(self, ctx): 
        self.streamChat = ctx
        self.rcon_settings["streamChat"] = ctx.message.channel.id
        
        await ctx.send("Streaming chat...")
    
    @commands.check(canUseCmds)   
    @commands.command(name='stopStream',
        brief="Stops the stream",
        pass_context=True)
    @CommandChecker.check
    async def streamStop(self, ctx): 
        self.streamChat = None
        self.rcon_settings["streamChat"] = None
        await ctx.send("Stream stopped")
            

    @commands.check(canUseCmds)   
    @commands.command(name='checkAFK',
        brief="Checks if a player is AFK (5min)",
        pass_context=True)
    @CommandChecker.check
    async def checkAFK(self, ctx, player_id: int): 
        players = await self.arma_rcon.getPlayersArray()
        player_name = None
        for player in players:
            if(int(player[0]) == player_id):
                player_name = player[4]
        if(player_name.endswith(" (Lobby)")): #Strip lobby from name
            player_name = player_name[:-8]
        if(player_name == None):
            await ctx.send("Player not found")
            return
        msg= "Starting AFK check for: ``"+str(player_name)+"``"
        await ctx.send(msg)  
        already_active = False
        for i in range(0, 300): #checks for 5min (10*30s)
            if(self.playerTypesMessage(player_name)):
                if(i==0):
                    already_active = True
                await ctx.send("Player responded in chat. Canceling AFK check.")  
                if(already_active == False):
                    await self.arma_rcon.sayPlayer(player_id,  "Thank you for responding in chat.")
                return
            if((i % 30) == 0):
                for k in range(0, 3):
                    await self.arma_rcon.sayPlayer(player_id, "Type something in chat or you will be kicked for being AFK. ("+str(round(i/30)+1)+"/10)")
            await asyncio.sleep(1)
        if(self.playerTypesMessage(player_name)):
            if(i==0):
                already_active = True
            await ctx.send("Player responded in chat. Canceling AFK check.")  
            if(already_active == False):
                await self.arma_rcon.sayPlayer(player_id, "Thank you for responding in chat.")
            return
        else:
            await self.arma_rcon.kickPlayer(player_id, "AFK too long")
            await ctx.send("``"+str(player_name)+"`` did not respond and was kicked for being AFK") 
            
    # @commands.check(canUseCmds)   
    # @commands.command(name='steamChat',
        # brief="Toggles RCon debug mode",
        # pass_context=True)
    # async def cmd_debug(self, ctx, time_min=1): 
        # if(self.arma_rcon.options['debug']==True):
            # self.arma_rcon.options['debug'] = False
        # else:
            # self.arma_rcon.options['debug'] = True
       
        # msg= "Set debug mode to:"+str(self.arma_rcon.options['debug'])
        # await ctx.send(msg)     
    
    @commands.check(canUseCmds)   
    @commands.command(name='debug',
        brief="Toggles RCon debug mode",
        pass_context=True)
    @CommandChecker.check
    async def cmd_debug(self, ctx, limit=20): 
        if(self.arma_rcon.options['debug']==True):
            self.arma_rcon.options['debug'] = False
        else:
            self.arma_rcon.options['debug'] = True
       
        msg= "Set debug mode to:"+str(self.arma_rcon.options['debug'])
        await ctx.send(msg)     
    
    @commands.check(canUseCmds)   
    @commands.command(name='status',
        brief="Current connection status",
        pass_context=True)
    @CommandChecker.check
    async def status(self, ctx, limit=20): 
        msg = ""
        if(self.arma_rcon.disconnected==False):
           msg+= "Connected to: "+ self.arma_rcon.serverIP+"\n"
        else:
            msg+= "Currently not connected: "+ self.arma_rcon.serverIP+"\n"
        msg+= str(len(self.arma_rcon.serverMessage))+ " Messages collected"
        await ctx.send(msg) 
        
    @commands.check(canUseCmds)   
    @commands.command(name='getChat',
        brief="Get the last ingame chat messages",
        pass_context=True)
    @CommandChecker.check
    async def getChat(self, ctx, limit=20): 
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
        await self.sendLong(ctx, msg)
        
    @commands.check(canUseCmds)   
    @commands.command(name='players+',
        brief="Lists current players on the server",
        pass_context=True)
    @CommandChecker.check
    async def playersPlus(self, ctx):
        players = await self.arma_rcon.getPlayersArray()

        limit = 100
        i = 1
        new = False
        msg  = "Players: \n"
        for player in players:
            if(i <= limit):
                id,ip,ping,guid,name = player
                #fetch country
                response = self.ipReader.country(ip.split(":")[0])
                region = str(response.country.iso_code).lower()
                if(region == "none"):
                    flag = ":question:" #symbol if no country was found
                else:
                    flag = ":flag_{}:".format(region)
                msg+= "#{} | {} {}".format(id, flag, name)+"\n"

        await self.sendLong(ctx, msg)
###################################################################################################
#####                                   BEC Rcon commands                                      ####
###################################################################################################   
        
    @commands.check(canUseCmds)   
    @commands.command(name='command',
        brief="Sends a custom command to the server",
        pass_context=True)
    @CommandChecker.check
    async def command(self, ctx, *message): 
        message = " ".join(message)
        message = self.setEncoding(message)
        data = await self.arma_rcon.command(message)
        if(len(data) == 0):
            msg = "Executed command: ``"+str(message)+"`` and returned nothing (confirmed its execution)"
        else:
            msg = "Executed command: ``"+str(message)+"`` wich returned: "+str(data)
        await self.sendLong(ctx,msg)
        
    @commands.check(canUseCmds)   
    @commands.command(name='kickPlayer',
        brief="Kicks a player who is currently on the server",
        pass_context=True)
    @CommandChecker.check
    async def kickPlayer(self, ctx, player_id: int, *message): 
        message = " ".join(message)
        message = self.setEncoding(message)
        await self.arma_rcon.kickPlayer(player_id, message)
            
        msg = "kicked player: "+str(player_id)
        await ctx.send(msg)
            
    @commands.check(canUseCmds)   
    @commands.command(name='say',
        brief="Sends a global message",
        pass_context=True)
    @CommandChecker.check
    async def sayGlobal(self, ctx, *message): 
        name = ctx.message.author.name
        message = " ".join(message)
        message = self.setEncoding(message)
        await self.arma_rcon.sayGlobal(name+": "+message)
        msg = "Send: ``"+message+"``"
        await ctx.send(msg)    
        
    @commands.check(canUseCmds)   
    @commands.command(name='sayPlayer',
        brief="Sends a message to a specific player",
        pass_context=True)
    @CommandChecker.check
    async def sayPlayer(self, ctx, player_id: int, *message): 
        message = " ".join(message)
        message = self.setEncoding(message)
        name = ctx.message.author.name
        if(len(message)<2):
            message = "Ping"
        await self.arma_rcon.sayPlayer(player_id, name+": "+message)
        msg = "Send msg: ``"+str(player_id)+"``"+message
        await ctx.send(msg)
    
    @commands.check(canUseCmds)   
    @commands.command(name='loadScripts',
        brief="Loads the 'scripts.txt' file without the need to restart the server",
        pass_context=True)
    @CommandChecker.check
    async def loadScripts(self, ctx): 
        await self.arma_rcon.loadScripts()
        msg = "Loaded Scripts!"
        await ctx.send(msg)        
     
    @commands.check(canUseCmds)   
    @commands.command(name='loadEvents',
        brief="Loads Events",
        pass_context=True)
    @CommandChecker.check
    async def loadEvents(self, ctx): 
        await self.arma_rcon.loadEvents()
        msg = "Loaded Events!"
        await ctx.send(msg)    
            
    @commands.check(canUseCmds)   
    @commands.command(name='maxPing',
        brief="Changes the MaxPing value. If a player has a higher ping, he will be kicked from the server",
        pass_context=True)
    @CommandChecker.check
    async def maxPing(self, ctx, ping: int): 
        await self.arma_rcon.maxPing(ping)
        msg = "Set maxPing to: "+ping
        await ctx.send(msg)       

    @commands.check(canUseCmds)   
    @commands.command(name='changePassword',
        brief="Changes the RCon password",
        pass_context=True)
    @CommandChecker.check
    async def changePassword(self, ctx, *password): 
        password = " ".join(password)
        await self.arma_rcon.changePassword(password)
        msg = "Set Password to: ``"+password+"``"
        await ctx.send(msg)        
        
    @commands.check(canUseCmds)   
    @commands.command(name='loadBans',
        brief="(Re)load the BE ban list from bans.txt",
        pass_context=True)
    @CommandChecker.check
    async def loadBans(self, ctx): 
        await self.arma_rcon.loadBans()
        msg = "Loaded Bans!"
        await ctx.send(msg)    
        
    @commands.check(canUseCmds)   
    @commands.command(name='players',
        brief="Lists current players on the server",
        pass_context=True)
    @CommandChecker.check
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
                msgtable.add_row([player[0], player[4], player[1],player[3]])
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
    
    @commands.check(canUseCmds)   
    @commands.command(name='admins',
        brief="Lists current admins on the server",
        pass_context=True)
    @CommandChecker.check
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
            
    @commands.check(canUseCmds)   
    @commands.command(name='getMissions',
        brief="Gets a list of all Missions",
        pass_context=True)
    @CommandChecker.check
    async def getMissions(self, ctx):
        missions = await self.arma_rcon.getMissions()
        await self.sendLong(ctx, missions)
        
    @commands.check(canUseCmds)   
    @commands.command(name='loadMission',
        brief="Loads a mission",
        pass_context=True)
    @CommandChecker.check
    async def loadMission(self, ctx, mission: str):
        if(mission.endswith(".pbo",-4)): #Strips PBO
            mission = mission[:-4]
        await self.arma_rcon.loadMission(mission)
        msg = "Loaded mission: ``"+str(missions)+"``"
        await ctx.send(msg)  
    
    @commands.check(canUseCmds)   
    @commands.command(name='banPlayer',
        brief="Ban a player's BE GUID from the server. If time is not specified or 0, the ban will be permanent.",
        pass_context=True)
    @CommandChecker.check
    async def banPlayer(self, ctx, player_id, time=0, *message): 
        message = " ".join(message)
        message = self.setEncoding(message)
        if(len(message)<2):
            await self.arma_rcon.banPlayer(player=player, time=time)
        else:
            await self.arma_rcon.banPlayer(player, message, time)
            
        msg = "Banned player: ``"+str(player)+" - "+matches[0]+"`` with reason: "+message
        await ctx.send(msg)    
        
    @commands.check(canUseCmds)   
    @commands.command(name='addBan',
        brief="Ban a player with GUID (even if they are offline)",
        pass_context=True)
    @CommandChecker.check
    async def addBan(self, ctx, GUID: str, time=0, *message): 
        message = " ".join(message)
        message = self.setEncoding(message)
        player = player_id
        matches = ["?"]
        if(len(GUID) != 32):
            raise Exception("Invalid GUID")
        if(len(message)<2):
            await self.arma_rcon.addBan(player=player, time=time)
        else:
            await self.arma_rcon.addBan(player, message, time)
            
        msg = "Banned player: ``"+str(player)+" - "+matches[0]+"`` with reason: "+message
        await ctx.send(msg)   

    @commands.check(canUseCmds)   
    @commands.command(name='removeBan',
        brief="Removes a ban",
        pass_context=True)
    @CommandChecker.check
    async def removeBan(self, ctx, banID: int): 
        await self.arma_rcon.removeBan(banID)
            
        msg = "Removed ban: ``"+str(banID)+"``"
        await ctx.send(msg)    
        
    @commands.check(canUseCmds)   
    @commands.command(name='getBans',
        brief="Removes a ban",
        pass_context=True)
    @CommandChecker.check
    async def getBans(self, ctx): 
        bans = await self.arma_rcon.getBansArray()
        bans.reverse() #news bans first
        msgtable = prettytable.PrettyTable()
        msgtable.field_names = ["ID", "GUID", "Time", "Reason"]
        msgtable.align["ID"] = "r"
        msgtable.align["Name"] = "l"
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
            
    @commands.check(canUseCmds)   
    @commands.command(name='getBEServerVersion',
        brief="Gets the current version of the BE server",
        pass_context=True)
    @CommandChecker.check
    async def getBEServerVersion(self, ctx): 
        version = await self.arma_rcon.getBEServerVersion()
        msg = "BE version: ``"+str(version)+"``"
        await ctx.send(msg)         
        
    @commands.check(canUseCmds)   
    @commands.command(name='lock',
        brief="Locks the server. No one will be able to join",
        pass_context=True)
    @CommandChecker.check
    async def lock(self, ctx): 
        data = await self.arma_rcon.lock()
        msg = "Locked the Server"
        await ctx.send(msg)    

    @commands.check(canUseCmds)   
    @commands.command(name='unlock',
        brief="Unlocks the Server",
        pass_context=True)
    @CommandChecker.check
    async def unlock(self, ctx): 
        data = await self.arma_rcon.unlock()
        msg = "Unlocked the Server"
        await ctx.send(msg)       
    
    @commands.check(canUseCmds)   
    @commands.command(name='shutdown',
        brief="Shutdowns the Server",
        pass_context=True)
    @CommandChecker.check
    async def shutdown(self, ctx): 
        data = await self.arma_rcon.shutdown()
        msg = "Shutdown the Server"
        await ctx.send(msg)           
        
    @commands.check(canUseCmds)   
    @commands.command(name='restart',
        brief="Restart mission with current player slot selection",
        pass_context=True)
    @CommandChecker.check
    async def restart(self, ctx): 
        data = await self.arma_rcon.restart()
        msg = "Restarting the Mission"
        await ctx.send(msg)          
    
    @commands.check(canUseCmds)   
    @commands.command(name='restartServer',
        brief="Shuts down and restarts the server immediately",
        pass_context=True)
    @CommandChecker.check
    async def restartServer(self, ctx): 
        data = await self.arma_rcon.restartServer()
        msg = "Restarting the Server"
        await ctx.send(msg)           
        
    @commands.check(canUseCmds)   
    @commands.command(name='restartM',
        brief="Shuts down and restarts the server after mission ends",
        pass_context=True)
    @CommandChecker.check
    async def restartserveraftermission(self, ctx): 
        data = await self.arma_rcon.restartserveraftermission()
        msg = "Restarting the Server after mission ends"
        await ctx.send(msg)       
    
    @commands.check(canUseCmds)   
    @commands.command(name='shutdownM',
        brief="Shuts down the server after mission ends",
        pass_context=True)
    @CommandChecker.check
    async def shutdownserveraftermission(self, ctx): 
        data = await self.arma_rcon.shutdownserveraftermission()
        msg = "Restarting the Server after mission ends"
        await ctx.send(msg)       
    
    @commands.check(canUseCmds)   
    @commands.command(name='reassign',
        brief="Shuts down the server after mission ends",
        pass_context=True)
    @CommandChecker.check
    async def reassign(self, ctx): 
        data = await self.arma_rcon.reassign()
        msg = "Restart the mission with new player slot selection"
        await ctx.send(msg)          
    
    @commands.check(canUseCmds)   
    @commands.command(name='monitords',
        brief="Shows performance information in the dedicated server console. Interval 0 means to stop monitoring.",
        pass_context=True)
    @CommandChecker.check
    async def monitords(self, ctx, interval: int): 
        data = await self.arma_rcon.monitords(interval)
        msg = "Restart the mission with new player slot selection"
        await ctx.send(msg)        
        
    @commands.check(canUseCmds)   
    @commands.command(name='goVote',
        brief="Users can vote for the mission selection.",
        pass_context=True)
    @CommandChecker.check
    async def goVote(self, ctx): 
        data = await self.arma_rcon.goVote()
        msg = "Restart the mission with new player slot selection"
        await ctx.send(msg)       

def setup(bot):
    bot.add_cog(CommandRcon(bot))    
    