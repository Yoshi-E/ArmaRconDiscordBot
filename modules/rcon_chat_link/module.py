
# Work with Python 3.6
import asyncio
from collections import Counter
import json
import os
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
import ast
import sys
import traceback
import urllib.parse
import threading

from modules.core.utils import CommandChecker, sendLong, CoreConfig
from modules.core.Log import log

class CommandChatLink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.path = os.path.dirname(os.path.realpath(__file__))
        
        self.cfg = CoreConfig.modules["modules/rcon_chat_link"]["general"]
        asyncio.ensure_future(self.on_ready())
        
    async def on_ready(self):
        await self.bot.wait_until_ready()
        try:
            self.CommandRcon = self.bot.cogs["CommandRcon"]
            self.CommandArma = self.bot.cogs["CommandArma"]
            
            self.CommandArma.readLog.EH.add_Event("Server online", self.server_online)
            self.CommandArma.readLog.EH.add_Event("Mission readname", self.missionRead)
            self.CommandArma.readLog.EH.add_Event("Mission started", self.missionStarted)
            self.CommandArma.readLog.EH.add_Event("Mission finished", self.missionFinished)
            
            self.linkedChannel = self.bot.get_channel(self.cfg["linked_channel"])
            
            if(self.linkedChannel):
                #Add Event Handlers
                self.CommandRcon.arma_rcon.add_Event("received_ServerMessage", self.rcon_on_msg_received)
                self.CommandRcon.arma_rcon.add_Event("on_disconnect", self.rcon_on_disconnect)
                self.CommandRcon.arma_rcon.add_Event("login_Sucess", self.rcon_on_connect)
            
        except Exception as e:
            log.print_exc()
            log.error(e)
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if(message.channel.id!=self.cfg["linked_channel"]):
            return
        if(self.linkedChannel):
            #check if message is command
            if(message.content.startswith(self.bot.command_prefix)):
                return
            #check if bot is author
            if(message.author.id == self.bot.user.id):
                return
            if(self.CommandRcon.arma_rcon.disconnected == False):
                await self.CommandRcon.arma_rcon.sayGlobal("{}: {}".format(message.author.name, message.content[:300]))
                
###################################################################################################
#####                                  common functions                                        ####
###################################################################################################
    async def server_online(self, event, timestamp, msg, event_match, currentLinePos):
        await self.linkedChannel.send(":desktop: Server is back online!")    
    
    async def missionRead(self, event, timestamp, msg, event_match, currentLinePos):
        await self.linkedChannel.send(":map: Loading mission '{}'".format(event_match.group(2)))   

    async def missionStarted(self, event, timestamp, msg, event_match, currentLinePos):
        await self.linkedChannel.send(":map: Mission Started")    
        
    async def missionFinished(self, event, timestamp, msg, event_match, currentLinePos):
        await self.linkedChannel.send(":map: Mission Finished!")
        
    async def verifyMessage(self, author, message):
        if(not self.cfg["verifyMessage"]):
            return
        messages = await self.linkedChannel.history(limit=10).flatten()
        
        for msg in messages:
            if msg.author.name==author and msg.content==message:
                await msg.add_reaction('\U00002714')
                return
               
        await msg.add_reaction('\U0000274C')
        
    #function called when a new message is received by rcon
    async def rcon_on_msg_received(self, args):
        message = discord.utils.escape_markdown(args[0], as_needed=True)
        try:
            #example: getting player name
            if(": " in message):
                header, body = message.split(": ", 1)
                if(self.CommandRcon.isChannel(header)): #was written in a channel
                    channel, player_name = header.split(") ", 1)
                    if(self.cfg["arma_channel_all"] or "Global" in channel):
                        if(self.cfg["display_channel_name"]):
                            await self.linkedChannel.send("({}) {}: {}".format(channel[1:], player_name, body))    
                        else:
                            await self.linkedChannel.send("{}: {}".format(player_name, body))    
                else: #(e.g Admin messages)
                    if("RCon admin #" in message and "(Global)" in message):
                        msg = body.split(") ", 1)[1]
                        author, msg = msg.split(": ", 1)
                        await self.verifyMessage(author, msg)
                        log.info("[OTHER] {} {}".format(author, msg))
            else: #is join or disconnect, or similar 
                pass 
        except Exception as e:
            log.info(message)
            log.print_exc()
            log.error(e)
    #event supports async functions
    #function is called when rcon disconnects
    async def rcon_on_disconnect(self):
        await self.linkedChannel.send(":x: ``Connection lost``")    
        
    async def rcon_on_connect(self):
        await self.linkedChannel.send(":white_check_mark: ``Connected ChatLink``")

     
    ###################################################################################################
    #####                                   Bot commands                                           ####
    ###################################################################################################

    # @CommandChecker.command(  name='ping',
                        # pass_context=True)
    # async def command_ping(self, ctx, *args):
        # msg = 'Pong!'
        # await ctx.send(msg)
    
                  
    
def setup(bot):
    module = CommandChatLink(bot)
    #bot.loop.create_task(module.task_setStatus())
    bot.add_cog(module)
    