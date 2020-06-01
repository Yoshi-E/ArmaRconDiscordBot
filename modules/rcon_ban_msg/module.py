
# Works with Python 3.6
# Discord 1.2.2
import asyncio
import os
import sys
import traceback
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
import numpy as np
from collections import deque

from modules.core.utils import CommandChecker, RateBucket, sendLong, CoreConfig, Tools


class CommandRcon_Custom(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.recentBans = deque(maxlen=100) #tracks the message "has been kicked by BattlEye: Admin Ban"
        asyncio.ensure_future(self.on_ready())
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        try:
            await asyncio.sleep(60) #wait addional time for everything to be ready
            self.CommandRcon = self.bot.cogs["CommandRcon"]
        
            self.post_channel = self.bot.get_channel(CoreConfig.cfg["PUSH_CHANNEL"]) #channel id
            self.CommandRcon.arma_rcon.add_Event("received_ServerMessage", self.rcon_on_msg_received)
            await self.init_bans_watchdog()
        except Exception as e:
            traceback.print_exc()
            print(e)
    
    def rcon_on_msg_received(self, args):
        message=args[0]

        if(":" in message):
            header, body = message.split(":", 1)
            if(self.CommandRcon.isChannel(header)): #was written in a channel
                player_name = header.split(") ")[1]
            else:
                #is join or disconnect, or similaar
                #print(message)
                asyncio.ensure_future(self.banned_user_kick(message))
    
    #fetches the user name from the recent chat entries
    #user names are not saved in the banlist, so we do a temp list here base on the chat entries
    def name_from_guid(self, guid):
        try:
            a = np.array(self.recentBans)
            index = np.where((a[:,1] == guid))[0][0]
            return self.recentBans[index]
        except:
            return ["Unkown", "-1"]
        
    async def banned_user_kick(self, msg):
        if("BattlEye: Admin Ban" in msg):
            user = msg[msg.find(" | ")+1:msg.find("(")]
            guid = msg[msg.find("(")+1:msg.find(")")]
            self.recentBans.append([user, guid])
            
            await self.check_newBan()
        
    async def init_bans_watchdog(self):
        self.bans = await self.CommandRcon.arma_rcon.getBansArray()
        asyncio.ensure_future(self.bans_watchdog())
    
    async def check_newBan(self):
        new_bans = await self.CommandRcon.arma_rcon.getBansArray()
        #print(len(self.bans), len(new_bans))
        
        #Compare old & new list for changes:
        a = np.array(new_bans)
        b = np.array(self.bans)
        change_added = list(set(a[:,0]) - set(b[:,0]))
        change_removed = list(set(b[:,0]) - set(a[:,0]))
        self.bans = new_bans #update old list
        #print(change_added, change_removed)
            
        if(len(a) > 0 and len(change_added) > 0 and len(change_added) < 10):
            for i in change_added:
                index = np.where((a[:,0] == i))[0][0]
                await self.announce_ban_added(a[index])
            
        if(len(a) > 0 and len(change_removed) > 0 and len(change_removed) < 10):
            for i in change_removed:
                index = np.where((b[:,0] == i))
                index = index[0][0]
                await self.announce_ban_removed(b[index])
            
    async def bans_watchdog(self):
        #watches for changes that are not noted in the log (e.g. removal of bans)
        #on every check the full ban list will be copied, 
        #for large ban lists its recommended to keep the update rate >60s
        
        #bans format: ["ID", "GUID", "Time", "Reason"]
        print("Starting ban watchdog")
        while True:
            await asyncio.sleep(60)
            await self.check_newBan()
            
    async def announce_ban_added(self, data):
        name, guid = self.name_from_guid(data[1])
        await self.post_channel.send("``{}`` has been **banned**!: \nGUID: {}\nTime: {}\nReason: {}".format(name, data[1], data[2], data[3]))   
        
    async def announce_ban_removed(self, data):
        name, guid = self.name_from_guid(data[1])
        await self.post_channel.send("``{}`` has been **unbanned**!: \nGUID: {}\nTime: {}\nReason: {}".format(name, data[1], data[2], data[3])) 

def setup(bot):
    bot.add_cog(CommandRcon_Custom(bot))